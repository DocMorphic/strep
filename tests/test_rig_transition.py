import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read
from rig_contact_authoring import metadata
from rig_transition import validate,prepare,localize,blend


def recipe():
    a=metadata('20260926-204848-eaceb96b','transfer');b=metadata('20260926-195412-bf0e8a1d','corrected')
    return dict(schema='strep-rig-transition-v1',label='Wave transition',clips=[dict(job=a['job_id'],variant=a['variant'],glb_sha256=a['glb_sha256'],first_frame=0,last_frame=30),dict(job=b['job_id'],variant=b['variant'],glb_sha256=b['glb_sha256'],first_frame=30,last_frame=90)],blend_frames=10,yaw_degrees=45)


@pytest.mark.parametrize('fault',['hash','frames','blend','yaw','asset'])
def test_reject_invalid_transition(fault):
    p=recipe()
    if fault=='hash':p['clips'][1]['glb_sha256']='0'*64
    if fault=='frames':p['clips'][1]['last_frame']=200
    if fault=='blend':p['blend_frames']=31
    if fault=='yaw':p['yaw_degrees']=float('nan')
    if fault=='asset':
        m=metadata('20260926-204805-38b5db10','transfer');p['clips'][1].update(job=m['job_id'],glb_sha256=m['glb_sha256'],first_frame=0,last_frame=20)
    with pytest.raises(ValueError):validate(p)


def test_baked_transition_preserves_unblended_poses_and_source_clocks(tmp_path,monkeypatch):
    import action_worker_lock
    import rig_contact_authoring as author
    from rig_studio_job import run
    from rig_asset import RigAsset
    from gltf_tools import sample_animation
    from rig_contact_tracks import signals,ROLES
    from scipy.spatial.transform import Rotation
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    p=recipe();folder=tmp_path/'joined';prepare(p,folder);run(folder)
    result=read(folder/'result.json');assert result['frames']==82
    output=RigAsset.load(folder/'transfer/character.glb');actual=np.array([sample_animation(output.document,output.binary,0,f) for f in range(82)])
    a=RigAsset.load(folder/'input/character.glb');b=RigAsset.load(folder/'following/character.glb')
    aw=np.array([sample_animation(a.document,a.binary,0,f) for f in range(31)])
    bw=np.array([sample_animation(b.document,b.binary,0,f) for f in range(30,91)])
    clock=read(folder/'transfer/timeline.json');t=np.array(clock['second_alignment_matrix']);root=63
    np.testing.assert_allclose(t[:3,:3],Rotation.from_euler('y',45,degrees=True).as_matrix(),atol=1e-10)
    assert t[1,3]==0
    np.testing.assert_allclose((t@bw[0,root])[[0,2],3],aw[21,root][[0,2],3],atol=1e-8)
    np.testing.assert_allclose(actual[:22],aw[:22],atol=1e-5)
    for n in range(len(a.parents)):
        ancestor=n
        while ancestor>=0 and ancestor!=root:ancestor=a.parents[ancestor]
        expected=t@bw[9:,n] if ancestor==root else bw[9:,n]
        np.testing.assert_allclose(actual[30:,n],expected,atol=1e-5)
    assert clock['contributors'][21]==[dict(source=0,frame=21,weight=1.),dict(source=1,frame=30,weight=0.)]
    assert clock['contributors'][30]==[dict(source=0,frame=30,weight=0.),dict(source=1,frame=39,weight=1.)]
    assert clock['contributors'][-1]==[dict(source=1,frame=90,weight=1.)]
    masks,origin=signals(read(folder/'transfer/report.json'));assert origin=='blended_source_predictions'
    old=[signals(read(folder/name/'report.json'))[0] for name in ('input','following')]
    for role in ROLES:
        expected=[all(old[c['source']][role][c['frame']] for c in entries if c['weight']>0) for entries in clock['contributors']]
        np.testing.assert_array_equal(masks[role],expected)
    review=read(folder/'transfer/contact-review.json')
    for target in review['authored_targets']:
        expected=np.array(target['original_interval']['target_position_m'])
        if target['source']==1:expected=t[:3,:3]@expected+t[:3,3]
        np.testing.assert_allclose(target['target_position_m'],expected,atol=1e-10)
    assert (folder/'source/transition-history/joined/following/source/motion.npz').exists()
    monkeypatch.setattr(author,'JOBS',tmp_path)
    m=author.metadata('joined','transfer');assert m['frames']==82 and not m['spec']['contacts']
    spec=read(folder/'input/contact-spec.json');spec.update(frames=82,glb_sha256=m['glb_sha256'])
    author.prepare(dict(source_job='joined',variant='transfer',spec=spec),tmp_path/'contact-child')
    for name in ('events.json','timeline.json','contact-review.json'):
        assert (tmp_path/'contact-child/transfer'/name).read_bytes()==(folder/'transfer'/name).read_bytes()
    from rig_clip_edit import prepare as edit_prepare
    edit_prepare(dict(source_job='joined',variant='transfer',edit=dict(schema='strep-rig-clip-edit-v1',glb_sha256=m['glb_sha256'],label='Child edit',start_frame=0,last_frame=30,speed=1,poses=[])),tmp_path/'edited')
    assert (tmp_path/'edited/source/transition-history/joined/following/source/motion.npz').exists()
    run(tmp_path/'edited')
    events=read(tmp_path/'edited/transfer/events.json')['events']
    assert [(e['frame'],e['source_frame']) for e in events]==[(21,21),(30,30)]
    targets=read(tmp_path/'edited/transfer/contact-review.json')['authored_targets']
    assert all(0<=f['frame']<=30 for t in targets for f in t['output_frames'])


def test_changed_second_original_source_is_rejected(tmp_path):
    from rig_transition import run
    folder=tmp_path/'joined';prepare(recipe(),folder)
    with (folder/'following/source/motion.npz').open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='provenance changed'):run(folder)
