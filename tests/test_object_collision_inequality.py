import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from support_contact_v8 import torch_primitive_depth,torch_primitive_clearance_violation,inequality_merit


@pytest.mark.parametrize('geometry',[Geometry('sphere',(.25,)),Geometry('box',(.5,.7,.9))])
def test_signed_collision_merit_preserves_initial_loss_and_gradient(geometry):
    p=torch.tensor([[[.1,.04,.08],[.3,.1,.05]],[[.7,.8,.9],[.6,.7,.8]]],dtype=torch.float64,requires_grad=True)
    origin=torch.zeros((2,3),dtype=p.dtype)
    r=torch.tensor(np.tile(Rotation.from_euler('y',31,degrees=True).as_matrix(),(2,1,1)),dtype=p.dtype)
    old=torch_primitive_depth(p,origin,r,geometry,.002).square().amax(1).mean()*10000
    g=torch_primitive_clearance_violation(p,origin,r,geometry,.002).amax(1)
    merit=inequality_merit(g,torch.zeros_like(g),20000).mean()
    torch.testing.assert_close(merit,old)
    old_gradient=torch.autograd.grad(old,p,retain_graph=True)[0]
    new_gradient=torch.autograd.grad(merit,p)[0]
    torch.testing.assert_close(new_gradient,old_gradient)
    assert g[0]>0 and g[1]<0
    multiplier=torch.tensor([10.,10.],dtype=p.dtype)
    updated=torch.relu(multiplier+20000*g.detach())
    assert updated[0]>multiplier[0] and updated[1]==0
