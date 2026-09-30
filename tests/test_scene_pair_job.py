import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import paired_edit_request
import scene_pair_job as jobs
from action_studio_server import Handler, allowed_file
from test_paired_edit_request import payload, URL
from strep import ROOT, read, save, sha256

pytestmark = pytest.mark.skipif(not (ROOT/'reports/scene-trim-jobs/paired-studio-workflow-v2-trim/trimmed.json').exists(), reason='Local saved paired scene required')


@pytest.fixture
def directory(tmp_path, monkeypatch):
    import action_studio_server
    monkeypatch.setattr(action_studio_server, 'external_pair_fit_busy', lambda:False)
    monkeypatch.setattr(jobs, 'JOBS', tmp_path)
    monkeypatch.setattr(paired_edit_request, 'JOBS', tmp_path)
    return tmp_path


def test_prepare_snapshots_native_review_and_exact_events(directory):
    folder = directory/'one'; jobs.prepare(dict(label='Review pair', request=payload()), folder)
    job = read(folder/'job.json')
    assert read(folder/'state.json')['status'] == 'prepared'
    assert read(folder/'pipeline.json')['status'] == 'starting'
    assert set(job['native']) == {'A', 'B'}
    assert 'review-input/retime-contact-windows.json' in job['files']
    for name, digest in job['files'].items(): assert sha256(folder/name) == digest
    for name, digest in job['implementation'].items(): assert sha256(folder/'worker-implementation'/name) == digest
    assert jobs.listing()['jobs'][0]['label'] == 'Review pair'


def test_worker_failure_preserves_prepared_reference_and_terminal_state(directory, monkeypatch):
    folder = directory/'failure'; jobs.prepare(dict(label='Failure test', request=payload()), folder)
    original = sha256(folder/'request.json')
    import study_scene_pair_fit
    def fail(*args, **kwargs): raise ValueError('Deliberate fixture failure')
    monkeypatch.setattr(study_scene_pair_fit, 'run', fail)
    with pytest.raises(ValueError, match='fixture failure'): jobs.run(folder)
    assert sha256(folder/'request.json') == original
    assert read(folder/'state.json')['status'] == 'prepared'
    assert jobs.listing()['jobs'][0]['status'] == 'failed'


def handler(path, value=None):
    output = []; raw = b'' if value is None else json.dumps(value).encode()
    obj = SimpleNamespace(path=path, headers={'Host':'127.0.0.1:8768', 'Origin':'http://127.0.0.1:8768',
        'Content-Type':'application/json', 'Content-Length':str(len(raw))}, rfile=io.BytesIO(raw),
        server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'}, worker=None), respond=lambda code, data:output.append((code,data)))
    return obj, output


def test_direct_metadata_and_listing_routes(directory):
    from urllib.parse import quote
    h, out = handler('/api/scene-pair-source?path='+quote(URL)); Handler.do_GET(h)
    assert out[0][0] == 200 and set(out[0][1]['actors']) == {'A','B'}
    assert out[0][1]['contacts'][0]['seconds'][0] == pytest.approx(2.0917225950783)
    h, out = handler('/api/scene-pair-jobs'); Handler.do_GET(h); assert out == [(200, {'jobs':[]})]
    assert allowed_file('/scene-pair-editor.js') == ROOT/'scripts/scene-pair-editor.js'
    h, out = handler('/api/scene-pair-source?extra=no'); Handler.do_GET(h); assert out[0][0] == 400


def test_post_enforces_origin_validation_and_existing_worker(directory, monkeypatch):
    import threading
    import action_studio_server as server
    data = dict(label='Pair', request=payload())
    h, out = handler('/api/scene-pair-fits',data); h.headers['Origin']='http://elsewhere'; Handler.do_POST(h); assert out[0][0] == 403
    h, out = handler('/api/scene-pair-fits',{}); Handler.do_POST(h); assert out[0][0] == 400
    monkeypatch.setattr(server, 'worker_busy', lambda:True)
    h, out = handler('/api/scene-pair-fits',data); h.server.job_lock=threading.Lock(); Handler.do_POST(h); assert out[0][0] == 409
    assert not list(directory.iterdir())


def test_post_launches_only_the_prepared_worker(directory, monkeypatch):
    import threading
    import action_studio_server as server
    monkeypatch.setattr(server,'worker_busy',lambda:False); launched=[]
    def launch(args, **kwargs): launched.append((args,kwargs)); return SimpleNamespace(pid=os.getpid(),poll=lambda:None)
    monkeypatch.setattr(server.subprocess,'Popen',launch)
    h, out = handler('/api/scene-pair-fits',dict(label='Pair',request=payload())); h.server.job_lock=threading.Lock(); Handler.do_POST(h)
    assert out[0][0] == 202 and len(launched) == 1
    args, options = launched[0]; assert Path(args[1]).name == 'scene_pair_job.py'
    folder=Path(args[2]); assert folder.parent == directory and read(folder/'job.json')['label'] == 'Pair'
    assert read(folder/'request.json')['authored']['protected_contact_ids'] == ['palm-to-palm']
    assert options['env']['HF_HUB_OFFLINE'] == '1'


def test_completed_study_reuse_requires_exact_prepared_identity(directory):
    folder=directory/'prepared'; folder.mkdir(); save(folder/'request.json',{'test_fixture':True})
    study=directory/'study'; study.mkdir()
    save(study/'request.json',dict(prepared_request=str(folder/'request.json'),inputs={str(folder/'request.json'):sha256(folder/'request.json')}))
    save(study/'result.json',dict(status='processing',request_sha256=sha256(study/'request.json')))
    with pytest.raises(ValueError,match='Completed bound'):jobs.copy_completed_fit(folder,study)
    save(study/'result.json',dict(status='complete',request_sha256=sha256(study/'request.json')))
    jobs.copy_completed_fit(folder,study)
    assert sha256(folder/'fit/result.json')==sha256(study/'result.json')
    with pytest.raises(ValueError,match='fresh fit'):jobs.copy_completed_fit(folder,study)
    other=directory/'other'; other.mkdir(); save(other/'request.json',{'test_fixture':True})
    with pytest.raises(ValueError,match='another prepared'):jobs.copy_completed_fit(other,study)
