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
