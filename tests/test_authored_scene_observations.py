from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from authored_scene_observations import observe_scene_motion


def fixture():
    names=['joint'+str(i) for i in range(77)];bind=np.array([[0.,0,0],[0,0,.1],[.1,0,0]])
    skin=dict(rig_joint_names=np.array(names),bind_vertices=bind,faces=np.array([[0,1,2]]),lbs_indices=np.zeros((3,8),dtype=int),lbs_weights=np.tile([1.,0,0,0,0,0,0,0],(3,1)),bind_rig_transform=np.tile(np.eye(4),(77,1,1)))
    p=np.zeros((5,77,3));p[:,:,0]=np.arange(5)[:,None]*.1;p[:,:,1]=-.2;p[:,2:6,0]+=.1;r=np.tile(np.eye(3),(5,77,1,1))
    plan=dict(schema='strep-authored-scene-guidance-v1',frames=5,joint_names=names,vertices=3,floor_normal=[0,1,0],floor_offset_m=0,primitives=[],contacts=[dict(vertex=0,start_frame=1,end_frame=3,targets_m=[[0.,0.,0.]]*3,normal_directions=[[0,1,0]]*3,normal_faces=[[0,1,2]],tangent_directions=[[1,0,0]]*3,hand_joint=1,knuckle_joints=[2,3,4,5])])
    return plan,skin,r,p


def test_full_pose_metrics_orientation_and_complete_intervals():
    plan,skin,r,p=fixture();result=observe_scene_motion(plan,skin,r,p)
    np.testing.assert_allclose(result['floor'][0],.2);np.testing.assert_array_equal(result['floor'][1],3)
    np.testing.assert_allclose(result['skin_speed_m_s'],3);np.testing.assert_allclose(result['skin_acceleration_m_s2'],0,atol=1e-12)
    np.testing.assert_allclose(result['contact_position'],np.sqrt(np.array([.1,.2,.3])**2+.2**2));np.testing.assert_allclose(result['contact_normal'],0);np.testing.assert_allclose(result['contact_tangent'],0)
    assert len(result['contact_position'])==3 and len(result['joint_speed_m_s'])==4 and len(result['joint_acceleration_m_s2'])==3


@pytest.mark.parametrize('shape,geometry',[('box',dict(size_m=[1.,1.,1.])),('sphere',dict(radius_m=.5)),('cylinder',dict(radius_m=.5,height_m=1.))])
def test_every_primitive_frame_is_measured(shape,geometry):
    plan,skin,r,p=fixture();plan['primitives']=[dict(geometry=dict(schema='strep-object-geometry-v1',shape=shape,**geometry),positions_m=[[0,0,0]]*5,rotations=np.tile(np.eye(3),(5,1,1)).tolist())]
    result=observe_scene_motion(plan,skin,r,p);assert result['objects'].shape==(1,3,5) and np.all(result['objects']>=0) and result['objects'][0,0,0]>0


def test_clock_or_original_joint_order_cannot_change():
    plan,skin,r,p=fixture()
    with pytest.raises(ValueError):observe_scene_motion(plan,skin,r[:-1],p[:-1])
    plan['joint_names']=plan['joint_names'][::-1]
    with pytest.raises(ValueError):observe_scene_motion(plan,skin,r,p)
