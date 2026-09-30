import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rigid_contact_placement import place,replay,placement_frame,align_near
from grasp_orientation import angular_error
from object_geometry import Geometry


@pytest.mark.parametrize('target',[[1.,0.,0.],[-1.,0.,0.]])
def test_placement_replays_with_bounds_and_shape_change(target):
    frame=placement_frame([1.,0.,0.],target)
    normal=Rotation.from_rotvec([0.,.12,-.07]).apply(frame[0])
    offsets=np.array([[0.,0.,0.],[.01,.04,.02],[.02,-.03,.05]])
    raw=np.array([3.,-4.,7.,8.,-2.,8.1]);target_point=np.array([.2,.1,0.])
    t=lambda x:torch.tensor(x,dtype=torch.float64)
    values=place(t(raw),t(offsets),t(normal),*[t(v) for v in frame],t(target_point),.005,np.deg2rad(10))
    independent=replay(raw,offsets,normal,*frame,target_point,.005,np.deg2rad(10))
    for a,b in zip(values,independent):np.testing.assert_allclose(a.numpy(),b,atol=1e-14)
    points,q,matrix=independent
    assert np.linalg.norm(q-target_point)<.005
    assert angular_error(matrix@normal,frame[1])<10
    np.testing.assert_allclose(matrix.T@matrix,np.eye(3),atol=1e-14)
    np.testing.assert_allclose(np.linalg.norm(points[1:]-points[0],axis=1),np.linalg.norm(offsets[1:],axis=1))


def test_placement_shape_and_rigid_derivatives():
    t=lambda x:torch.tensor(x,dtype=torch.float64)
    frame=placement_frame([1.,0.,0.],[-1.,0.,0.])
    def function(z):
        normal=torch.stack([z.new_tensor(1.),z[6],z[7]]);normal=normal/torch.linalg.vector_norm(normal)
        return place(z[:6],t([[.01,.04,.02]]),normal,*[t(v) for v in frame],t([.2,.1,0.]),.005,.17)[0]
    raw=t([.1,.2,.3,.4,.5,.6,.07,.08]).requires_grad_()
    assert torch.autograd.gradcheck(function,(raw,),eps=1e-6,atol=1e-6,rtol=1e-4)


def test_cylinder_twist_is_not_a_radial_sphere_symmetry():
    frame=placement_frame([-1.,0.,0.],[-1.,0.,0.])
    offsets=np.array([[0.,.12,0.]])
    cylinder=Geometry.parse(dict(schema='strep-object-geometry-v1',shape='cylinder',radius_m=.2,height_m=.4))
    gaps=[]
    for twist in [0.,np.pi/2]:
        points,_,_=replay([0,0,0,0,0,twist],offsets,frame[0],*frame,np.array([.2,.1,0.]),.005,.17)
        gaps.append(cylinder.distance_gradient(points,np.zeros(3),np.eye(3))[0][0])
    assert abs(gaps[0]-gaps[1])>.01


def test_shape_normal_chart_rejects_antiparallel_motion():
    t=lambda x:torch.tensor(x,dtype=torch.float64)
    with pytest.raises(ValueError,match='alignment chart'):align_near(t([1.,0.,0.]),t([-1.,0.,0.]))


def test_hand_patch_excludes_every_positive_external_influence():
    from study_regional_hand_placement import pure_hand_vertices
    skin=dict(lbs_indices=np.array([[1,2],[2,0],[1,0],[2,3]]),
              lbs_weights=np.array([[.5,.5],[1.,0.],[1.-1e-14,1e-14],[.8,.2]]))
    np.testing.assert_array_equal(pure_hand_vertices(skin,[-1,0,1,0],1),[0,1])
