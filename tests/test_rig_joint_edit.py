import copy
import sys
import zipfile
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256
from test_rig_joint_recipe import request
from rig_joint_recipe import prepare
import rig_joint_edit


def test_supervised_job_retains_input_targets_contacts_and_rejected_candidate(tmp_path,monkeypatch):
    import action_worker_lock
    import rig_contact_authoring
    from rig_studio_job import run
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    original=rig_joint_edit.run
    monkeypatch.setattr(rig_joint_edit,'run',lambda folder:original(folder,feasibility_iterations=1,refinement_iterations=1))
    folder=tmp_path/'joint-job';payload=request();prepare(payload,folder)
    prior={p.name:sha256(p) for p in (folder/'input').iterdir() if p.is_file()}
    run(folder)
    result=read(folder/'result.json');audit=read(folder/'transfer/joint-edit-audit.json')
    assert read(folder/'pipeline.json')['status']=='complete'
    assert result['kind']=='joint_edit' and result['joint_targets_reached']
    assert result['joint_edit_status']=='rejected' # Pre-existing mesh-floor defect survives.
    assert audit['hard_checks_passed'] and audit['refinement'] is not None
    assert not audit['human_approved'] and result['engine_import'] is None
    assert all(sha256(folder/'input'/name)==digest for name,digest in prior.items() if name!='report.json')
    annotations=read(folder/'transfer/contacts.json');source_annotations=read(folder/'input/contacts.json')
    assert all(annotations[k]==v for k,v in source_annotations.items())
    assert annotations['origin']=='none_supplied'
    assert read(folder/'transfer/timeline.json')['source_frames']==list(range(61))
    assert read(folder/'contact-spec.json')['contacts']==read(folder/'input/contact-spec.json')['contacts']
    with zipfile.ZipFile(folder/'character-animation.zip') as z:
        for name in ['joint-edit.json','joint-input.npz','target-fit/character.glb','quality-fit/summary.json','transfer/joint-fit.npz','transfer/joint-edit-audit.json']:
            assert z.read(name)==(folder/name).read_bytes()
    monkeypatch.setattr(rig_contact_authoring,'JOBS',tmp_path)
    for variant in ['input','transfer']:
        meta=rig_contact_authoring.metadata('joint-job',variant)
        assert meta['frames']==61 and meta['glb_sha256']==result['variants'][variant]['sha256']


def test_unmet_goals_retained_and_refinement_not_started(tmp_path):
    p=request();p['edit']['goals'][0]['position_m'][0]+=10
    folder=tmp_path/'unreachable';prepare(p,folder)
    report,audit=rig_joint_edit.run(folder,feasibility_iterations=1,refinement_iterations=1)
    assert not audit['targets_reached'] and audit['refinement_skipped']
    assert 'joint_targets_missed' in audit['flags'] and audit['hard_checks_passed']
    assert (folder/'transfer/character.glb').exists() and not (folder/'quality-fit').exists()
    assert not audit['feasibility']['infeasibility_proven']


@pytest.mark.parametrize('name',['joint-targets.json','input/contacts.json','input/character.glb'])
def test_changed_snapshots_rejected_before_output(tmp_path,name):
    folder=tmp_path/'changed';prepare(request(),folder)
    with (folder/name).open('ab') as stream:stream.write(b' ')
    with pytest.raises(ValueError,match='snapshot changed'):rig_joint_edit.run(folder)
    assert not (folder/'target-fit').exists() and not (folder/'transfer').exists()


def test_independent_audit_detects_changed_context_even_when_goal_is_met(tmp_path):
    from rig_asset import RigAsset
    from rig_loop import encode
    folder=tmp_path/'context';prepare(request(),folder)
    data=dict(np.load(folder/'joint-input.npz'));spec=read(folder/'joint-spec.json');targets=read(folder/'joint-targets.json')
    rig=RigAsset.load(folder/'input/character.glb');changed=data['before'].copy()
    changed[0,:,:3,3]+=[.1,0,0]
    path=folder/'bad.glb';encode(rig,changed,set(range(len(rig.parents))),spec['root_node'],path,'Changed context')
    audit=rig_joint_edit.audit_clip(path,data['before'],spec,targets)
    assert audit['targets_reached'] and not audit['hard_checks_passed']
    assert 'hard_fixed_context_failed' in audit['flags']


def test_api_origin_stale_hash_busy_lock_and_snapshot_dispatch(tmp_path,monkeypatch):
    import json
    import threading
    import urllib.request
    import urllib.error
    from http.server import ThreadingHTTPServer
    import action_studio_server
    import action_worker_lock
    import studio_characters
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    monkeypatch.setattr(studio_characters,'JOBS',tmp_path/'jobs')
    studio_characters.JOBS.mkdir()
    dispatch=[]
    class Worker:
        pid=2147483647
        def poll(self):return None
    def launch(command,**kwargs):
        dispatch.append(command)
        return Worker()
    monkeypatch.setattr(action_studio_server.subprocess,'Popen',launch)
    server=ThreadingHTTPServer(('127.0.0.1',0),action_studio_server.Handler)
    host=f'127.0.0.1:{server.server_port}';server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    payload=request()
    def send(value,origin=None):
        req=urllib.request.Request(f'http://{host}/api/rig-joint-edits',json.dumps(value).encode(),
            headers={'Content-Type':'application/json','Origin':origin or 'http://'+host})
        return urllib.request.urlopen(req)
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:send(payload,'http://untrusted.invalid')
        assert exc.value.code==403
        stale=copy.deepcopy(payload);stale['edit']['glb_sha256']='0'*64
        with pytest.raises(urllib.error.HTTPError) as exc:send(stale)
        assert exc.value.code==400
        with action_worker_lock.worker_lock():
            with pytest.raises(urllib.error.HTTPError) as exc:send(payload)
            assert exc.value.code==409
        assert not list(studio_characters.JOBS.iterdir()) and not dispatch
        with send(payload) as response:
            assert response.status==202
            result=json.load(response)
        assert len(dispatch)==1 and Path(dispatch[0][-1])==studio_characters.JOBS/result['id']
        snapshot=studio_characters.JOBS/result['id']
        assert read(snapshot/'joint-edit.json')==payload['edit']
        assert read(snapshot/'request.json')['kind']=='joint_edit'
        assert sha256(snapshot/'input/character.glb')==payload['edit']['glb_sha256']
    finally:server.shutdown();server.server_close();thread.join()
