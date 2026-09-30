import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scipy.spatial.transform import Rotation
from test_decoded_motion_edges import rig_fixture
from native_waypoint_clock import guide_clock
from oriented_terminal_hand import OrientedTerminalMotion,support_clock
from continuous_terminal_hand import solve
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels


@pytest.mark.parametrize('actor',[0,1])
def test_independent_scene_hand_rotation_export_and_full_support_replay(actor,tmp_path):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    native=guide_clock([clock]*6,[.15,.5,.85],[])[-3:];times=np.arange(241)/120
    placement=Rotation.from_euler('xyz',[11,37,-9],degrees=True).as_matrix()
    model=OrientedTerminalMotion(rig,[1,2,3],native,times,[],placement,actor)
    controls=np.array([.0012,-.0007,.003,1.2,-1.1,.6,-.9,.5,-.7,.8,-.3])
    path=tmp_path/'candidate.glb';model.export_vector(controls,path)
    doc,binary=read_glb(path);reader=AnimationSampler(doc,binary,0);source=AnimationSampler(rig.document,rig.binary,0)
    world,maximum=model.evaluate_vector(controls)
    np.testing.assert_allclose(world,[reader.sample(t) for t in times],atol=2e-12,rtol=0);assert maximum>0
    at_key=reader.sample(native[1]);old=source.sample(native[1]);delta=Rotation.from_rotvec(np.deg2rad(controls[5+actor*3:8+actor*3])).as_matrix()
    np.testing.assert_allclose(placement@at_key[3,:3,:3],delta@placement@old[3,:3,:3],atol=2e-7,rtol=0)
    np.testing.assert_allclose(at_key[3,:3,3]@placement.T,old[3,:3,3]@placement.T+controls[:3]*(1 if actor==0 else -1),atol=2e-7,rtol=0)
    for t in [native[0]-.01,native[0],native[-1],native[-1]+.000001,native[-1]+.1]:
        # SLERP's exact-endpoint arithmetic may differ by one ulp when its
        # neighboring quaternion changes. Stored protected keys stay exact.
        np.testing.assert_allclose(reader.sample(t),source.sample(t),atol=1e-12,rtol=0)
    before=rotation_channels(rig.document,rig.binary);after=rotation_channels(doc,binary)
    for node,(_,clock,q) in before.items():
        np.testing.assert_array_equal(clock,after[node][1])
        frozen=clock!=native[1] if node in [1,2,3] else np.ones(len(clock),bool)
        np.testing.assert_array_equal(q[frozen],after[node][2][frozen])
    # Rotating the other actor must not touch this actor's tracks.
    other=np.zeros(11);other[5+3*(1-actor)]=1.
    np.testing.assert_array_equal(model.evaluate_vector(other)[0],model.model.source_world)
    excessive=np.zeros(11);excessive[5+3*actor]=90
    with pytest.raises(ValueError):model.export_vector(excessive,tmp_path/'invalid.glb')


def test_support_clock_contains_incoming_and_return_stencils():
    times=np.arange(21)/10;inside,ids=support_clock(times,[.7,1.,1.3])
    np.testing.assert_array_equal(inside,np.arange(7,13));np.testing.assert_array_equal(ids,np.arange(5,15))
    with pytest.raises(ValueError):support_clock(times,[0,.1,.2])
    with pytest.raises(ValueError):support_clock(times,[1.7,1.9,2.])
    with pytest.raises(ValueError):support_clock(times[::-1],[.7,1.,1.3])


def test_hand_only_control_preserves_every_unedited_arm_quaternion():
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    native=guide_clock([clock]*6,[.15,.5,.85],[])[-3:]
    model=OrientedTerminalMotion(rig,[1,2,3],native,np.arange(241)/120,[],np.eye(3),0)
    control=np.zeros(11);control[5]=.5;values,_=model.quaternions_vector(control)
    for entry in model.model.entries[:2]:np.testing.assert_array_equal(values[entry['node']],entry['source'])
    assert np.any(values[3]!=model.model.entries[-1]['source'])


def test_eleven_dimensional_optimizer_uses_last_hand_component():
    best,_,_=solve(lambda c:(max(0.,.01-c[-1]),np.array([.004-c[-1],c[-1]+.04])),
                   np.full(11,.04),[np.zeros(11)],iterations=25)
    assert len(best['controls'])==11 and 0<best['controls'][-1]<=.004
    assert .006<=best['witness_peak_m']<.0061


@pytest.mark.parametrize('actor',[0,1])
def test_three_editable_keys_preserve_other_keys_and_shared_sampler(actor,tmp_path):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    native=clock[3:8].astype(float);times=np.arange(241)/120
    placement=Rotation.from_euler('xyz',[-17,43,8],degrees=True).as_matrix()
    model=OrientedTerminalMotion(rig,[1,2,3],native,times,[],placement,actor)
    rows=np.array([[.001,-.002,.003,1.,-2.,.3,-.7,.2,-.4,.8,-.6],
                   [0.,0.,0.,0.,0.,-.7,.2,.1,.5,-.6,.3],
                   [-.002,.001,-.001,-1.,1.,.9,.4,-.3,-.2,.6,.8]])
    path=tmp_path/'three-key.glb';model.export_vector(rows.ravel(),path)
    doc,binary=read_glb(path);reader=AnimationSampler(doc,binary,0)
    source=AnimationSampler(rig.document,rig.binary,0)
    np.testing.assert_allclose(model.evaluate_vector(rows.ravel())[0],[reader.sample(t) for t in times],atol=2e-12,rtol=0)
    for t,row in zip(native[1:-1],rows):
        old=source.sample(t);new=reader.sample(t)
        delta=Rotation.from_rotvec(np.deg2rad(row[5+actor*3:8+actor*3])).as_matrix()
        np.testing.assert_allclose(placement@new[3,:3,:3],delta@placement@old[3,:3,:3],atol=2e-7,rtol=0)
        np.testing.assert_allclose(new[3,:3,3]@placement.T,old[3,:3,3]@placement.T+row[:3]*(1 if actor==0 else -1),atol=2e-7,rtol=0)
    before=rotation_channels(rig.document,rig.binary);after=rotation_channels(doc,binary)
    for node,(_,track,q) in before.items():
        np.testing.assert_array_equal(track,after[node][1])
        frozen=~np.isin(track,native[1:-1]) if node in [1,2,3] else np.ones(len(track),bool)
        np.testing.assert_array_equal(q[frozen],after[node][2][frozen])
        if node in [1,2]:np.testing.assert_array_equal(q[track==native[2]],after[node][2][track==native[2]])
    # Fixture node 6 shares the original arm sampler and must stay untouched.
    np.testing.assert_array_equal(before[6][2],after[6][2])
    with pytest.raises(ValueError):model.evaluate_vector(np.zeros(11))


def test_multikey_guide_bounds_reject_adjacent_direction_changes_and_diagonals():
    from oriented_guide_domain import control_scales,margins
    native=[0.,.1,.2,.3,.4];limits=[.8,300.,300.]
    scale=control_scales(native,limits).reshape(3,11)
    np.testing.assert_allclose(scale[:,0],.06)
    for columns,amount in [([0],.06),([3],30.),([5],30.),([8],30.)]:
        controls=np.zeros((3,11));controls[0,columns]=amount;controls[1,columns]=-amount
        values=margins(controls.ravel(),native,limits)
        assert np.min(values[:15])>=-1e-14 # Each key individually inside its envelope.
        assert np.min(values[15:])<0 # Adjacent transition too fast.
    for columns,amount in [([0,1],.05),([5,6],25.),([8,9],25.)]:
        controls=np.zeros((3,11));controls[1,columns]=amount
        assert np.all(np.abs(controls)<=scale)
        assert np.min(margins(controls.ravel(),native,limits))<0
    controls=np.zeros((3,11));controls[:,0]=[.01,.02,.01];controls[:,5]=[5.,10.,5.]
    assert np.min(margins(controls.ravel(),native,limits))>0
    with pytest.raises(ValueError):margins(np.zeros(11),native,limits)


def test_multikey_support_includes_entire_edit_and_halos():
    inside,ids=support_clock(np.arange(31)/10,[.7,.9,1.1,1.3,1.5])
    np.testing.assert_array_equal(inside,np.arange(7,15));np.testing.assert_array_equal(ids,np.arange(5,17))


def test_thirty_three_dimensional_optimizer_can_edit_last_key():
    best,_,_=solve(lambda c:(max(0.,.01-c[-1]),np.array([.004-c[-1],c[-1]+.04])),
                   np.full(33,.04),[np.zeros(33)],iterations=25)
    assert len(best['controls'])==33 and 0<best['controls'][-1]<=.004
    assert .006<=best['witness_peak_m']<.0061


@pytest.mark.parametrize('damage',[None,'artifact','incomplete','snapshot','current_method'])
def test_return_diagnosis_requires_complete_unchanged_evidence(tmp_path,monkeypatch,damage):
    import json
    import diagnose_oriented_hand_returns as diagnosis
    from strep import sha256
    root=tmp_path/'root';(root/'scripts').mkdir(parents=True)
    folder=tmp_path/'study';(folder/'implementation').mkdir(parents=True)
    method=root/'scripts'/'method.py';method.write_text('original')
    snapshot=folder/'implementation'/'method.py';snapshot.write_text('original')
    request=dict(hand_orientation=True,implementation={'method.py':sha256(method)})
    result=dict(status='complete')
    for name in ['request','witnesses','source-queries','selected','solvers','evaluations','decoded','geometry']:
        path=folder/(name+'.json');path.write_text(json.dumps(request if name=='request' else []))
        result[name.replace('-','_')+'_sha256']=sha256(path)
    if damage=='incomplete':result['status']='running'
    (folder/'result.json').write_text(json.dumps(result));monkeypatch.setattr(diagnosis,'ROOT',root)
    if damage=='artifact':(folder/'solvers.json').write_text('[1]')
    if damage=='snapshot':snapshot.write_text('changed')
    if damage=='current_method':method.write_text('changed')
    if damage:
        with pytest.raises(ValueError):diagnosis.load_evidence(folder)
    else:
        loaded,files=diagnosis.load_evidence(folder)
        assert loaded==request and files[str(snapshot)]==sha256(snapshot)
