import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,sha256
from rig_clip_edit import timeline,remap_intervals,envelope,validate,prepare
from rig_contact_authoring import metadata


def request(job='20260926-202244-c3c3bb14'):
    m=metadata(job,'corrected')
    return dict(source_job=job,variant='corrected',edit=dict(schema='strep-rig-clip-edit-v1',glb_sha256=m['glb_sha256'],label='Trim and pose',
        start_frame=10,last_frame=40,speed=1.5,poses=[dict(node=17,start_frame=10,peak_frame=25,end_frame=40,rotation_degrees=[0,0,10])]))


def test_clock_preserves_both_trim_endpoints_and_reports_effective_speed():
    e=request()['edit'];frames,clock=timeline(e,61)
    assert len(frames)==21 and frames[0]==10 and frames[-1]==40
    assert clock['effective_speed']==1.5 and clock['duration_s']==pytest.approx(2/3)
    e['speed']=1.7;frames,clock=timeline(e,61)
    assert len(frames)==19 and clock['effective_speed']==pytest.approx(30/18)


def test_contact_membership_uses_half_open_original_frame_intervals():
    frames,_=timeline(request()['edit'],61)
    contacts,dropped=remap_intervals([dict(joint='LeftFoot',start_frame=21,end_frame_exclusive=26,start_seconds=.7,end_seconds_exclusive=26/30),dict(joint='RightFoot',start_frame=0,end_frame_exclusive=4)],frames)
    assert dropped==[1] and contacts[0]['start_frame']==8 and contacts[0]['end_frame_exclusive']==11
    assert contacts[0]['start_seconds']==pytest.approx(8/30)
    assert np.array_equal((frames>=21)&(frames<26),np.isin(np.arange(21),[8,9,10]))


@pytest.mark.parametrize('fault',['hash','trim','speed','long','node','curve','overlap','angle'])
def test_invalid_edits_are_rejected_before_job_creation(fault):
    p=request();e=p['edit']
    if fault=='hash':e['glb_sha256']='0'*64
    if fault=='trim':e['last_frame']=100
    if fault=='speed':e['speed']=float('nan')
    if fault=='long':e['label']=''
    if fault=='node':e['poses'][0]['node']=999
    if fault=='curve':e['poses'][0]['peak_frame']=10
    if fault=='overlap':e['poses'].append(copy.deepcopy(e['poses'][0]))
    if fault=='angle':e['poses'][0]['rotation_degrees']=[90,90,0]
    with pytest.raises(ValueError):validate(p)


def test_worker_preserves_source_pose_and_retimes_contacts_and_chained_versions(tmp_path,monkeypatch):
    import action_worker_lock
    import rig_contact_authoring as author
    from rig_studio_job import run
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from target_rig_contact import baseline
    from rig_contact_tracks import signals
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    p=request();folder=tmp_path/'edited';prepare(p,folder);run(folder)
    result=read(folder/'result.json');assert result['frames']==21 and result['variants']['input']['frames']==61
    before=RigAsset.load(folder/'input/character.glb');after=RigAsset.load(folder/'transfer/character.glb');sampler=AnimationSampler(before.document,before.binary,0)
    poses,local_after=baseline(after,21);frames,clock=timeline(p['edit'],61)
    for f,source_frame in enumerate(frames):
        source_world=sampler.sample(float(np.float32(source_frame/30)));source_local=source_world.copy()
        for node,parent in enumerate(before.parents):
            if parent>=0:source_local[node]=np.linalg.inv(source_world[parent])@source_world[node]
        np.testing.assert_allclose(local_after[f,:,:3,3],source_local[:,:3,3],atol=1e-5)
        for node in range(len(before.parents)):
            if node!=17:np.testing.assert_allclose(local_after[f,node,:3,:3],source_local[node,:3,:3],atol=1e-5)
        delta=np.linalg.inv(source_local[17,:3,:3])@local_after[f,17,:3,:3]
        expected=envelope(p['edit']['poses'][0],source_frame)*10
        assert np.degrees(Rotation.from_matrix(delta).magnitude())==pytest.approx(expected,abs=1e-4)
        np.testing.assert_allclose(poses[f,3,:3,3],source_world[3,:3,3],atol=1e-5)
    spec=read(folder/'contact-spec.json');assert spec['frames']==21 and spec['glb_sha256']==sha256(folder/'transfer/character.glb')
    assert [(c['start_frame'],c['end_frame_exclusive']) for c in spec['contacts']]==[(8,11)]
    masks,origin=signals(read(folder/'transfer/report.json'));assert origin=='none_supplied' and all(not m.any() for m in masks.values())
    monkeypatch.setattr(author,'JOBS',tmp_path)
    assert author.metadata('edited','input')['frames']==61
    assert author.metadata('edited','transfer')['frames']==21
    q=dict(source_job='edited',variant='input',spec=author.metadata('edited','input')['spec'])
    author.prepare(q,tmp_path/'input-contact-edit')
    assert read(tmp_path/'input-contact-edit/transfer/report.json')['frames']==61


def test_native_prediction_clock_survives_edit_and_contact_chain(tmp_path,monkeypatch):
    import action_worker_lock
    import rig_contact_authoring as author
    from rig_studio_job import run
    from rig_contact_tracks import signals
    from strep import save
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    p=request('20260926-195412-bf0e8a1d')
    p['edit'].update(start_frame=30,last_frame=90,speed=2,poses=[])
    folder=tmp_path/'native-edited';prepare(p,folder);run(folder)
    before=read(folder/'input/contacts.json');after=read(folder/'transfer/contacts.json')
    sf=np.arange(30,91,2)
    assert after['origin']=='source_model_predictions'
    masks,origin=signals(read(folder/'transfer/report.json'))
    for role,mask in masks.items():
        expected=np.zeros(31,dtype=bool)
        for c in before['intervals']:
            if c['joint']==role:expected|=(sf>=c['start_frame'])&(sf<c['end_frame_exclusive'])
        np.testing.assert_array_equal(mask,expected)
    monkeypatch.setattr(author,'JOBS',tmp_path)
    metadata=author.metadata('native-edited','transfer')
    assert metadata['frames']==31 and metadata['spec']['frames']==31
    target=tmp_path/'contact-child'
    author.prepare(dict(source_job='native-edited',variant='transfer',spec=metadata['spec']),target)
    child_report=read(target/'transfer/report.json')
    assert Path(child_report['contact_annotations_file']).parent==target/'transfer'
    child_masks,_=signals(child_report)
    for role in masks:np.testing.assert_array_equal(masks[role],child_masks[role])
    after['intervals'][0]['end_frame_exclusive']=999;save(target/'transfer/contacts.json',after)
    with pytest.raises(ValueError,match='changed'):signals(child_report)
