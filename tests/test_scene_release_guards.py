import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_release_guards import compile_release_guards,extend_solver_spec


def fixture():
    transform=dict(translation_m=[2,0,-1],rotation_xyzw=Rotation.from_euler('y',90,degrees=True).as_quat().tolist())
    obj=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2),keyframes=[dict(frame=f,translation_m=[.1*f,.5,0],rotation_xyzw=Rotation.from_euler('y',f*10,degrees=True).as_quat().tolist()) for f in [0,9]])
    contact=dict(id='grip',actor='A',effector=dict(joint='LeftHand',surface_vertex=123),start_frame=2,end_frame=5,target=dict(space='object',object='ball',point_m=[.2,0,0]))
    return dict(frame_count=10,actors=dict(A=dict(transform=transform)),objects=dict(ball=obj),contacts=[contact])


def test_guard_tracks_moving_rotating_object_at_release_not_previous_key():
    scene=fixture();original=copy.deepcopy(scene);guards=compile_release_guards(scene,'A',['grip']);g=guards[0]
    expected_world=np.array([.6,.5,0])+Rotation.from_euler('y',60,degrees=True).apply([.2,0,0])
    placement=scene['actors']['A']['transform'];r=Rotation.from_quat(placement['rotation_xyzw']).as_matrix()
    np.testing.assert_allclose(r@np.array(g['position_m'])+placement['translation_m'],expected_world,atol=1e-12)
    assert g['frame']==6 and scene==original
    scene['contacts'][0]['end_frame']=9
    assert compile_release_guards(scene,'A',['grip'])==[]


def test_guard_changes_only_solver_track_and_rejects_adjacent_handoff():
    g=compile_release_guards(fixture(),'A',['grip'])
    segment=dict(start_frame=2,end_frame=5,space='track',positions_m=[[0,.5,0]]*4,vertex_id=123,tolerance_m=.001)
    spec=dict(schema_version=2,fps=30,frame_count=10,regions=dict(LeftHand=dict(mode='explicit',segments=[segment])))
    before=copy.deepcopy(spec);extended=extend_solver_spec(spec,g)
    assert spec==before and extended['regions']['LeftHand']['segments'][0]['end_frame']==6
    assert extended['regions']['LeftHand']['segments'][0]['tolerance_m']==.001
    assert extended['regions']['LeftHand']['segments'][0]['positions_m'][-1]==g[0]['position_m']
    spec['regions']['LeftHand']['segments'].append(dict(segment,start_frame=6,end_frame=7,positions_m=[[0,.5,0]]*2))
    with pytest.raises(ValueError,match='adjacent contact'):extend_solver_spec(spec,g)
