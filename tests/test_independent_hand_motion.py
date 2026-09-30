import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from independent_hand_motion import IndependentHandMotion,from_symmetric,actor_controls,scales,margins
from oriented_terminal_hand import OrientedTerminalMotion
from test_decoded_motion_edges import rig_fixture
from scipy.spatial.transform import Rotation
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from gltf_tools import read_glb


@pytest.mark.parametrize('actor',[0,1])
def test_independent_wrist_direction_and_actual_export_with_other_actor_untouched(actor,tmp_path):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    native=clock[3:8].astype(float);times=np.arange(241)/120
    placement=Rotation.from_euler('xyz',[19,-41,7],degrees=True).as_matrix()
    model=IndependentHandMotion(rig,[1,2,3],native,times,[],placement,actor)
    rows=np.zeros((3,14));rows[:,3*actor:3*actor+3]=[[.001,-.002,.003],[-.002,.001,.004],[.003,.002,-.001]]
    rows[:,6+actor]=[1.,-2.,.5];rows[:,8+3*actor:11+3*actor]=[[.5,-.6,.3],[-.9,.4,.7],[.2,.6,-.8]]
    path=tmp_path/'independent.glb';model.export_vector(rows.ravel(),path)
    doc,binary=read_glb(path);reader=AnimationSampler(doc,binary,0);source=AnimationSampler(rig.document,rig.binary,0)
    np.testing.assert_allclose(model.evaluate_vector(rows.ravel())[0],[reader.sample(t) for t in times],atol=2e-12,rtol=0)
    for t,row in zip(native[1:-1],rows):
        old,new=source.sample(t),reader.sample(t)
        np.testing.assert_allclose(new[3,:3,3]@placement.T,old[3,:3,3]@placement.T+row[actor*3:actor*3+3],atol=2e-7,rtol=0)
        delta=Rotation.from_rotvec(np.deg2rad(row[8+actor*3:11+actor*3])).as_matrix()
        np.testing.assert_allclose(placement@new[3,:3,:3],delta@placement@old[3,:3,:3],atol=2e-7,rtol=0)
    other=IndependentHandMotion(rig,[1,2,3],native,times,[],placement,1-actor)
    np.testing.assert_array_equal(other.evaluate_vector(rows.ravel())[0],other.model.model.source_world)
    before,after=rotation_channels(rig.document,rig.binary),rotation_channels(doc,binary)
    for node,(_,track,q) in before.items():
        np.testing.assert_array_equal(track,after[node][1])
        frozen=~np.isin(track,native[1:-1]) if node in [1,2,3] else np.ones(len(track),bool)
        np.testing.assert_array_equal(q[frozen],after[node][2][frozen])


@pytest.mark.parametrize('actor',[0,1])
def test_symmetric_candidate_maps_to_identical_exported_motion(actor,tmp_path):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    native=clock[3:8].astype(float);times=np.arange(241)/120;placement=Rotation.from_euler('y',29,degrees=True).as_matrix()
    old=OrientedTerminalMotion(rig,[1,2,3],native,times,[],placement,actor)
    new=IndependentHandMotion(rig,[1,2,3],native,times,[],placement,actor)
    controls=(np.array([.4,1.,.7])[:,None]*np.array([.001,-.002,.003,1.,-2.,.3,-.7,.2,-.4,.8,-.6])).ravel()
    expanded=from_symmetric(controls)
    np.testing.assert_array_equal(old.evaluate_vector(controls)[0],new.evaluate_vector(expanded)[0])
    a,b=tmp_path/'old.glb',tmp_path/'new.glb';old.export_vector(controls,a);new.export_vector(expanded,b)
    assert a.read_bytes()==b.read_bytes()


def test_common_direction_wrist_motion_is_representable_and_each_actor_keeps_own_guide_caps():
    native=[0.,.1,.2];limits=[.8,300,300];controls=np.zeros(14)
    controls[:3]=[.01,0.,0.];controls[3:6]=[.01,0.,0.]
    assert actor_controls(controls,1,0)[0]==.01 and actor_controls(controls,1,1)[0]==-.01
    assert np.min(margins(controls,native,limits))>0
    assert scales(native,limits).shape==(14,)
    controls[3:6]=[.05,.05,0.]
    assert np.all(np.abs(controls)<=scales(native,limits))
    assert np.min(margins(controls,native,limits))<0
    with pytest.raises(ValueError):actor_controls(np.zeros(11),1,0)
    with pytest.raises(ValueError):from_symmetric([float('nan')]*11)
