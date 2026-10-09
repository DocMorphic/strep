import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v8 import finger_rotation_budgets
from support_contact_v5 import bounded_rotation,rodrigues


def test_finger_budgets_bound_each_rotation_norm_and_keep_finite_gradients():
    names=['Hips']+[side+'Hand'+finger+str(joint) for side in ['Left','Right']
        for finger in ['Thumb','Index','Middle','Ring','Pinky'] for joint in range(1,4 if finger=='Thumb' else 5)]
    names += ['FixtureBody'+str(i) for i in range(77-len(names))]
    budgets=finger_rotation_budgets(names)
    assert len(budgets)==38 and budgets[names.index('LeftHandThumb1')]==8 and budgets[names.index('RightHandPinky1')]==5
    limits=torch.tensor(np.deg2rad(list(budgets.values())))[None,:,None]
    parameters=torch.randn((5,38,3),dtype=torch.float64,requires_grad=True,generator=torch.Generator().manual_seed(77))
    changes=bounded_rotation(parameters*100,limits)
    ratio=torch.linalg.vector_norm(changes,dim=-1)/limits.squeeze(-1)
    assert torch.all(ratio<=1+8*torch.finfo(torch.float64).eps) # Arithmetic roundoff, not an angular budget allowance.
    rodrigues(changes).sum().backward();assert torch.isfinite(parameters.grad).all()
