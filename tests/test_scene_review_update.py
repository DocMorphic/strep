import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_review_update import displayed_manifest, annotate_failed_angular
from strep import read, save, sha256


def fixture(tmp_path):
    collection=tmp_path/'collection';collection.mkdir(); replay=tmp_path/'replay';replay.mkdir()
    save(collection/'manifest.json',dict(scenes=[dict(id='source',review_note='Original'),dict(id='candidate',review_note='Prior acceptance')]))
    records=[]
    for name in ['A','B']:
        for version in ['source','candidate']:records.append(dict(actor=name,version=version,copied_glb_sha256=version+name))
    save(collection/'provenance.json',dict(fit_result_sha256='fit',files={'manifest.json':sha256(collection/'manifest.json')},records=records))
    save(replay/'request.json',dict(study_result_sha256='fit'))
    save(replay/'verification.json',dict(status='complete',request_sha256=sha256(replay/'request.json'),passed=False,
        actors=[dict(actor=n,source_sha256='source'+n,candidate_sha256='candidate'+n,rates=dict(angular=dict(exceeding_observations=2))) for n in ['A','B']]))
    return collection,replay


def test_appended_review_changes_display_without_rewriting_original(tmp_path):
    collection,replay=fixture(tmp_path); old=sha256(collection/'manifest.json'); provenance=sha256(collection/'provenance.json')
    annotate_failed_angular(collection,replay); display=displayed_manifest(collection/'manifest.json')
    assert display['scenes'][0]['review_note']=='Original'
    assert '4 limit exceedances' in display['scenes'][1]['review_note']
    assert sha256(collection/'manifest.json')==old and sha256(collection/'provenance.json')==provenance
    with pytest.raises(ValueError,match='Preserve'):annotate_failed_angular(collection,replay)


@pytest.mark.parametrize('fault',['fit','actor','missing_actor','published_bytes'])
def test_unrelated_or_incomplete_review_cannot_annotate(tmp_path,fault):
    collection,replay=fixture(tmp_path)
    if fault=='fit':
        request=read(replay/'request.json');request['study_result_sha256']='other';save(replay/'request.json',request)
    if fault=='published_bytes':save(collection/'manifest.json',{})
    proof=read(replay/'verification.json');proof['request_sha256']=sha256(replay/'request.json')
    if fault=='actor':proof['actors'][0]['candidate_sha256']='other'
    if fault=='missing_actor':proof['actors'].pop()
    save(replay/'verification.json',proof)
    with pytest.raises(ValueError):annotate_failed_angular(collection,replay)


def test_handler_serves_bound_review_and_rejects_changed_evidence(tmp_path,monkeypatch):
    monkeypatch.setitem(sys.modules,'action_worker_lock',SimpleNamespace(worker_busy=lambda:False))
    import action_studio_server as server
    collection,replay=fixture(tmp_path);annotate_failed_angular(collection,replay)
    monkeypatch.setattr(server,'allowed_file',lambda path:collection/'manifest.json'); responses=[]
    handler=SimpleNamespace(path='/files/fixture/manifest.json',headers={'Host':'local'},server=SimpleNamespace(allowed_hosts={'local'}),respond=lambda code,data:responses.append((code,data)))
    server.Handler.do_GET(handler);assert responses[-1][0]==200
    assert 'failed independent angular' in responses[-1][1]['scenes'][1]['review_note']
    save(collection/'angular-review/verification.json',{})
    server.Handler.do_GET(handler);assert responses[-1][0]==409
