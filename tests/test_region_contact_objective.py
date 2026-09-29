import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from region_contact_objective import signed_distance,violations,choose_triangle

LIMITS=dict(clearance_m=.002,contact_gap_m=.003,spacing_m=.006,area_m2=.000025,
            centroid_error_m=.005,local_radius_m=.03,normal_degrees=10.)


@pytest.mark.parametrize('shape',[Geometry('sphere',(.5,)),Geometry('box',(1,1,1))])
def test_signed_distance_and_derivatives_match_independent_geometry(shape):
    rotation=Rotation.from_euler('xyz',[.2,.3,.5]).as_matrix();origin=np.array([1,2,3])
    local=np.array([[.503,.02,.03],[.02,.504,.01]])
    points=local@rotation.T+origin
    x=torch.tensor(points,dtype=torch.float64,requires_grad=True)
    p=torch.tensor(origin);r=torch.tensor(rotation)
    np.testing.assert_allclose(signed_distance(x,p,r,shape).detach(),shape.distance_gradient(points,origin,rotation)[0],atol=1e-12)
    assert torch.autograd.gradcheck(lambda v:signed_distance(v,p,r,shape),(x,))


def test_all_region_terms_have_checked_derivatives_and_detect_lost_contact():
    points=np.array([[-.01,.5021,-.01],[.012,.5023,-.01],[.001,.5022,.02]])
    x=torch.tensor(points,dtype=torch.float64,requires_grad=True)
    geometry=Geometry('box',(1,1,1));faces=np.array([[0,1,2]])
    def f(v):return violations(v,faces,np.arange(3),0,v.new_tensor([0,.5,0]),v.new_tensor([0,-1,0]),geometry,v.new_zeros(3),torch.eye(3,dtype=v.dtype),LIMITS,.02)
    assert torch.autograd.gradcheck(f,(x,),atol=1e-4,rtol=1e-3)
    assert bool((f(x)<=0).all())
    moved=x.detach().clone();moved[1:,1]+=.03
    assert float(torch.relu(f(moved)).max())>20
    assert torch.isfinite(torch.autograd.grad(torch.relu(f(x)).square().sum(),x)[0]).all()


def test_triangle_selection_keeps_existing_witness_and_handles_no_witness():
    points=np.array([[-.01,.502,-.01],[.01,.502,-.01],[0,.502,.02]])
    chosen,method=choose_triangle(points,np.array([10,20,30]),np.array([0,.5,0]),np.full(3,.002),LIMITS)
    assert chosen==[10,20,30] and method.startswith('existing')
    chosen,method=choose_triangle(points+.1,np.array([10,20,30]),np.array([0,.5,0]),np.full(3,.1),LIMITS)
    assert set(chosen)=={10,20,30} and '24 nearest' in method
