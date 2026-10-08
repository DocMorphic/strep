import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_constraints import pose,sample_object,target_track,box_vertex_depth,transform_motion


def test_shared_world_transform_rotates_positions_and_orientations():
    r=Rotation.from_euler('y',90,degrees=True)
    source=dict(posed_joints=np.array([[[0.,0.,1.]]]),global_rot_mats=np.eye(3)[None,None])
    result=transform_motion(source,dict(translation_m=[2,0,0],rotation_xyzw=r.as_quat().tolist()))
    np.testing.assert_allclose(result['positions'],[[[3,0,0]]],atol=1e-12)
    np.testing.assert_allclose(result['rotations'][0,0],r.as_matrix(),atol=1e-12)


def test_object_local_grip_tracks_translation_and_rotation():
    end=Rotation.from_euler('y',90,degrees=True).as_quat().tolist()
    obj=dict(shape='box',size_m=[1,1,1],keyframes=[dict(frame=0,translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]),dict(frame=2,translation_m=[2,0,0],rotation_xyzw=end)])
    track=sample_object(obj,3);p=target_track(dict(space='object',object='box',point_m=[0,0,1]),{},dict(box=track),3)
    np.testing.assert_allclose(p,[[0,0,1],[1+2**-.5,0,2**-.5],[3,0,0]],atol=1e-12)


def test_oriented_box_depth_respects_rotation_and_outside_points():
    v=np.array([[.7,0,0],[1.5,0,0]])
    r=Rotation.from_euler('y',90,degrees=True).as_matrix()
    np.testing.assert_allclose(box_vertex_depth(v,np.zeros(3),r,[.2,1,2]),[.1,0],atol=1e-12)
    np.testing.assert_array_equal(box_vertex_depth(v,np.zeros(3),np.eye(3),[.2,1,2]),[0,0])


def test_invalid_quaternion_and_missing_object_do_not_silently_fallback():
    with pytest.raises(ValueError):pose(dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,0]))
    with pytest.raises(ValueError):target_track(dict(space='object',object='missing',point_m=[0,0,0]),{},{},3)


def test_short_object_track_is_not_silently_extrapolated():
    key=lambda f:dict(frame=f,translation_m=[0,0,0],rotation_xyzw=[0,0,0,1])
    with pytest.raises(ValueError):sample_object(dict(shape='box',size_m=[1,1,1],keyframes=[key(0),key(1)]),10)


def test_joint_offsets_use_supplied_rig_order_without_downloaded_metadata(monkeypatch):
    import scene_constraints as module
    def forbidden(*args):raise AssertionError('Supplied rig must not read vendor metadata')
    monkeypatch.setattr(module,'skeleton_metadata',forbidden)
    actor=dict(positions=np.array([[[9.,9.,9.],[2.,3.,4.]]]),rotations=np.tile(np.eye(3),(1,2,1,1)))
    actor['rotations'][0,1]=Rotation.from_euler('z',90,degrees=True).as_matrix()
    skin=dict(rig_joint_names=np.array(['Hips','LeftHand']))
    effector=dict(joint='LeftHand',offset_m=[.03,0,0])
    expected=np.array([[2.,3.03,4.]])
    np.testing.assert_allclose(module.effector_track(actor,effector,skin),expected,atol=1e-12)
    np.testing.assert_allclose(module.target_track(dict(space='actor',actor='B',**effector),{'B':actor},{},1,skin),expected,atol=1e-12)


@pytest.mark.parametrize('names',[['LeftHand','LeftHand'],['LeftHand'],[['LeftHand','Hips']],['','LeftHand']])
def test_supplied_joint_mapping_must_be_distinct_and_match_motion(names):
    from scene_constraints import effector_track
    actor=dict(positions=np.zeros((1,2,3)),rotations=np.tile(np.eye(3),(1,2,1,1)))
    with pytest.raises(ValueError):
        effector_track(actor,dict(joint='LeftHand',offset_m=[0,0,0]),dict(rig_joint_names=np.array(names)))
