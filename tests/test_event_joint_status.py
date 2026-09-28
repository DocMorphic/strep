import sys
from pathlib import Path
import zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from rig_event_edit import inherited_joint_status,prepare,run as edit_events


def fixture(tmp_path,passed=False):
    glb=tmp_path/'character.glb';glb.write_bytes(b'unchanged motion')
    audit=dict(glb_sha256=sha256(glb),numerical_screen_passed=passed,targets_reached=True)
    save(tmp_path/'joint-edit-audit.json',audit)
    result=dict(joint_edit_status='numerical_screens_met' if passed else 'rejected')
    return glb,audit,result


@pytest.mark.parametrize('passed',[False,True])
def test_exact_motion_keeps_decision_and_audit(tmp_path,passed):
    glb,audit,result=fixture(tmp_path,passed)
    inherited=inherited_joint_status(result,'transfer',glb,'original')
    assert inherited['status']==result['joint_edit_status']
    assert inherited['audit_sha256']==sha256(tmp_path/'joint-edit-audit.json')
    result['inherited_joint_edit']=inherited
    child=inherited_joint_status(result,'transfer',glb,'child')
    assert child['source_job']=='child' and child['origin_job']=='original'
    assert inherited_joint_status(result,'input',glb,'original') is None
    assert inherited_joint_status({},'transfer',glb,'unrelated') is None


@pytest.mark.parametrize('fault',['motion','status','inherited_audit'])
def test_mismatched_evidence_is_rejected(tmp_path,fault):
    glb,audit,result=fixture(tmp_path)
    result['inherited_joint_edit']=inherited_joint_status(result,'transfer',glb,'original')
    if fault=='motion':glb.write_bytes(b'changed motion')
    if fault=='status':result['joint_edit_status']='numerical_screens_met'
    if fault=='inherited_audit':
        audit['extra']='changed';save(tmp_path/'joint-edit-audit.json',audit)
    with pytest.raises(ValueError):inherited_joint_status(result,'transfer',glb,'child')


def test_real_joint_candidate_marker_chain_keeps_rejection_and_export(tmp_path,monkeypatch):
    import action_worker_lock,rig_contact_authoring
    from rig_studio_job import run
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    original=ROOT/'reports/rig-jobs/20260927-044311-aab345bc'
    glb=original/'transfer/character.glb';audit_hash=sha256(original/'transfer/joint-edit-audit.json')
    payload=dict(schema='strep-rig-events-v1',job=original.name,variant='transfer',glb_sha256=sha256(glb),label='Joint rejection retained through marker edits',markers=[dict(id='cue',name='cue',frame=30,confirmed=True)])
    for name in ['first','second']:
        folder=tmp_path/name;prepare(payload,folder);run(folder)
        result=read(folder/'result.json')
        assert read(folder/'pipeline.json')['status']=='complete'
        assert result['joint_edit_status']=='rejected'
        assert result['joint_targets_reached'] is True
        assert result['inherited_joint_edit']['origin_job']==original.name
        assert sha256(folder/'transfer/character.glb')==sha256(glb)
        assert sha256(folder/'transfer/joint-edit-audit.json')==audit_hash
        assert read(folder/'transfer/events.json')['events'][-1]['name']=='cue'
        with zipfile.ZipFile(folder/'character-animation.zip') as archive:
            import hashlib,json
            assert hashlib.sha256(archive.read('transfer/joint-edit-audit.json')).hexdigest()==audit_hash
            assert json.loads(archive.read('request.json'))['inherited_joint_edit']['status']=='rejected'
        monkeypatch.setattr(rig_contact_authoring,'JOBS',tmp_path)
        payload['job']=name;payload['markers'][0]['frame']=31


def test_frozen_joint_audit_cannot_change_before_event_worker(tmp_path):
    source=ROOT/'reports/rig-jobs/20260927-044311-aab345bc'
    payload=dict(schema='strep-rig-events-v1',job=source.name,variant='transfer',glb_sha256=sha256(source/'transfer/character.glb'),label='Snapshot check',markers=[])
    folder=tmp_path/'edit';prepare(payload,folder)
    audit=read(folder/'input/joint-edit-audit.json');audit['numerical_screen_passed']=True;save(folder/'input/joint-edit-audit.json',audit)
    with pytest.raises(ValueError,match='snapshot changed'):edit_events(folder)
