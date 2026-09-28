import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v8 import bounded_edit_rotations
from support_contact_v5 import bounded_rotation


def test_physical_finger_coordinates_have_same_reachable_rotations_and_body_map():
    limits=torch.tensor(np.deg2rad([40,40,5,8,12]),dtype=torch.float64)[None,:,None]
    params=torch.tensor(np.random.default_rng(24).normal(size=(7,5,3)),dtype=torch.float64)
    physical=params.clone();physical[:,2:]*=limits[:,2:]
    old=bounded_edit_rotations(params,limits,2)
    new=bounded_edit_rotations(physical,limits,2,True)
    torch.testing.assert_close(old,new,atol=1e-15,rtol=1e-15)
    torch.testing.assert_close(old,bounded_rotation(params,limits),atol=0,rtol=0)
    assert torch.all(torch.linalg.vector_norm(new,dim=-1)<limits.squeeze(-1))


def test_physical_finger_origin_jacobian_is_identity_without_changing_body():
    limits=torch.tensor(np.deg2rad([40,5,12]),dtype=torch.float64)[None,:,None]
    zero=torch.zeros((1,3,3),dtype=torch.float64,requires_grad=True)
    jac=torch.autograd.functional.jacobian(lambda x:bounded_edit_rotations(x,limits,1,True),zero).reshape(9,9)
    expected=torch.diag(torch.tensor([np.deg2rad(40)]*3+[1.]*6,dtype=torch.float64))
    torch.testing.assert_close(jac,expected,atol=1e-14,rtol=1e-14)
