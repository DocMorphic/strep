"""Saved arbitrary intent, terminal state, liveness and a real blocked supervisor."""
import json
import shutil
import sys
import threading
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
import psutil
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_generation_resources as m
from resource_admission import ResourcePolicy
from motion_profile import default_profile
from strep import read,save


def request():
    profile=default_profile();profile['style']='Expressive stage mime';profile['stats'][0]['value']=85
    return dict(schema_version=1,requests=[dict(id='clock-and-shrug',label='Imaginary clock',
        segments=[dict(prompt='Mime winding an enormous imaginary clock.',duration_s=3.2),
                  dict(prompt='Spread both hands and shrug to the audience.',duration_s=2)],
        seeds=[0,4294967295],scene_requirements=['Clock is imaginary.'],motion_profile=profile)])


@pytest.fixture
def folder(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'ROOT',tmp_path)
    result=tmp_path/'reports/action-jobs/original';m.prepare(request(),result)
    return result


def deferred(folder,**change):
    save(folder/'guard/pipeline.json',dict(status='deferred',worker_started=False,reason='admission_timeout',**change))


def identity(folder,offset=0):
    p=psutil.Process();save(folder/'worker.json',dict(pid=p.pid,created_at=p.create_time()+offset))


def test_exact_intent_and_original_immutable_on_retry(folder):
    deferred(folder);before={p.relative_to(folder):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    batch=m.retry_request(dict(job='action-jobs/original'));assert batch==request()
    new=folder.parent/'retry';m.prepare(batch,new,retry_of='action-jobs/original')
    assert read(new/'resource-request.json')==request()
    assert read(new/'studio-launch.json')['retry_of']=='action-jobs/original'
    assert before=={p.relative_to(folder):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    assert not read(new/'studio-launch.json')['release_approved']


def test_changed_request_or_archive_rejected_before_retry(folder):
    deferred(folder);altered=request();altered['requests'][0]['seeds']=[11]
    save(folder/'resource-request.json',altered)
    with pytest.raises(ValueError):m.retry_request(dict(job='action-jobs/original'))
    save(folder/'resource-request.json',request())
    (folder/'request-implementation/motion_profile.py').write_text('altered',encoding='utf-8')
    with pytest.raises(ValueError):m.validate_snapshot(folder)


def test_resolved_controls_changed_after_prepare_rejected(folder,monkeypatch):
    deferred(folder);monkeypatch.setattr(m,'request_digest',lambda _: 'changed')
    assert m.observed_state(folder)['status']=='deferred'
    with pytest.raises(ValueError):m.retry_request(dict(job='action-jobs/original'))
    with pytest.raises(ValueError):m.validate_snapshot(folder,execution=True)


def test_wrapper_rejects_tamper_before_importing_model(folder,monkeypatch):
    import studio_generation_worker as worker
    monkeypatch.delitem(sys.modules,'run_actions',raising=False)
    save(folder/'resource-request.json',dict(schema_version=1,requests=[]))
    with pytest.raises(ValueError):worker.run(folder)
    assert 'run_actions' not in sys.modules and read(folder/'pipeline.json')['status']=='failed'


def test_valid_wrapper_passes_only_bound_request_to_pipeline(folder,monkeypatch):
    from types import SimpleNamespace
    import studio_generation_worker as worker
    calls=[]
    monkeypatch.setitem(sys.modules,'run_actions',SimpleNamespace(main=lambda request,out:calls.append((request,out))))
    worker.run(folder)
    assert calls==[(folder/'resource-request.json',folder)]
    assert read(calls[0][0])==request()


@pytest.mark.parametrize('status,started',[('failed',True),('complete',True),('processing',True),('deferred',True)])
def test_retry_requires_deferred_and_unstarted(folder,status,started):
    identity(folder);save(folder/'guard/pipeline.json',dict(status=status,worker_started=started))
    with pytest.raises(ValueError):m.retry_request(dict(job='action-jobs/original'))


def test_live_waiting_supervisor_survives_server_restart(folder):
    identity(folder)
    assert m.observed_state(folder)['status']=='waiting_resources' and m.generation_worker_busy()


def test_pid_reuse_does_not_keep_stale_supervisor_busy(folder):
    identity(folder,offset=-10)
    assert m.observed_state(folder)['status']=='failed' and not m.generation_worker_busy()


def test_access_denied_is_unknown_and_conservatively_busy(folder,monkeypatch):
    identity(folder)
    def denied(_):raise psutil.AccessDenied()
    monkeypatch.setattr(m.psutil,'Process',denied)
    assert m.observed_state(folder)['status']=='unknown' and m.generation_worker_busy()


def test_live_model_child_is_not_marked_finished_if_supervisor_lost(folder):
    identity(folder,-10);p=psutil.Process()
    save(folder/'guard/pipeline.json',dict(status='processing',worker_started=True,worker_pid=p.pid,worker_created_at=p.create_time()))
    assert m.observed_state(folder)['status']=='processing'


@pytest.mark.parametrize('status',['deferred','failed'])
def test_guard_terminal_overrides_stale_complete_output(folder,status):
    save(folder/'pipeline.json',dict(status='complete'));save(folder/'summary.json',{})
    save(folder/'guard/pipeline.json',dict(status=status,worker_started=False))
    assert m.observed_state(folder)['status']==status


def test_complete_requires_both_supervisor_and_motion_output(folder):
    save(folder/'guard/pipeline.json',dict(status='complete',worker_started=True))
    assert m.observed_state(folder)['status']=='failed'
    save(folder/'pipeline.json',dict(status='complete',takes=2))
    assert m.observed_state(folder)['takes']==2


def test_malformed_job_state_does_not_break_listing_or_allow_retry(folder):
    identity(folder);(folder/'guard').mkdir();(folder/'guard/pipeline.json').write_text('{')
    assert m.observed_state(folder)['status']=='unknown'
    with pytest.raises(ValueError):m.retry_request(dict(job='action-jobs/original'))


@pytest.mark.parametrize('job',['../escape','action-jobs/../escape','action-jobs/a/b','contact-jobs/a'])
def test_retry_cannot_read_outside_generation_jobs(folder,job):
    with pytest.raises(ValueError):m.retry_request(dict(job=job))


def test_real_http_saved_request_defer_retry_and_stale_files(tmp_path,monkeypatch):
    """Child-only fake zero RAM; real HTTP, subprocess, storage and admission."""
    import action_studio_server as server
    source=Path(m.__file__).parent;scripts=tmp_path/'scripts';scripts.mkdir()
    names=set(m.METHODS)|{'run_guarded_job.py','resource_admission.py','process_monitor.py','action_worker_lock.py','strep.py'}
    for name in names:shutil.copyfile(source/name,scripts/name)
    (scripts/'psutil.py').write_text('from types import SimpleNamespace\ndef virtual_memory():return SimpleNamespace(available=0)\n',encoding='utf-8')
    monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(server,'ROOT',tmp_path)
    monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(server,'worker_busy',m.generation_worker_busy)
    http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);port=http.server_address[1]
    http.allowed_hosts={f'127.0.0.1:{port}'};http.worker=None;http.job_lock=threading.Lock()
    http.generation_resource_policy=ResourcePolicy(4*1024**3,stable_seconds=.01,admission_seconds=.15,poll_seconds=.01)
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    def call(route,data=None):
        url=f'http://127.0.0.1:{port}';r=urllib.request.Request(url+route,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Content-Type':'application/json','Origin':url})
        with urllib.request.urlopen(r,timeout=10) as response:return response.status,json.load(response)
    try:
        code,first=call('/api/jobs',request());assert code==202 and first['status']=='waiting_resources'
        http.worker.wait(timeout=10);original=m.job_folder(first['id'])
        assert read(original/'guard/pipeline.json')['status']=='deferred'
        assert not read(original/'guard/pipeline.json')['worker_started'] and not (original/'guard/worker.log').exists()
        save(original/'summary.json',{});save(original/'manifest.json',{});save(original/'pipeline.json',dict(status='complete'))
        _,listing=call('/api/studies');row=next(s for s in listing['studies'] if s['id']==first['id'])
        assert row['can_retry'] and row['status']=='deferred' and not row['ready'] and not row['scene_ready']
        before=(original/'resource-request.json').read_bytes()
        code,second=call('/api/jobs/retry',dict(job=first['id']));assert code==202 and second['id']!=first['id']
        http.worker.wait(timeout=10);retry=m.job_folder(second['id'])
        assert read(retry/'resource-request.json')==request() and (original/'resource-request.json').read_bytes()==before
        assert read(retry/'studio-launch.json')['retry_of']==first['id']
        assert not read(retry/'guard/pipeline.json')['worker_started']
        with pytest.raises(urllib.error.HTTPError) as exc:call('/api/jobs/retry',dict(job='../escape'))
        assert exc.value.code==400
        assert 'torch' not in sys.modules
    finally:
        if http.worker is not None and http.worker.poll() is None:http.worker.kill();http.worker.wait(timeout=5)
        http.shutdown();http.server_close();thread.join(timeout=5)
