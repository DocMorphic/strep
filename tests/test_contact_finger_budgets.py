import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v8 import finger_rotation_budgets
from support_contact_v5 import bounded_rotation,rodrigues
from inspect_motion import skeleton_metadata


def test_finger_budgets_bound_each_rotation_norm_and_keep_finite_gradients():
    names,_,_=skeleton_metadata(77);budgets=finger_rotation_budgets(names)
    assert len(budgets)==38 and budgets[names.index('LeftHandThumb1')]==8 and budgets[names.index('RightHandPinky1')]==5
    limits=torch.tensor(np.deg2rad(list(budgets.values())))[None,:,None]
    parameters=torch.randn((5,38,3),dtype=torch.float64,requires_grad=True)
    changes=bounded_rotation(parameters*100,limits)
    assert torch.all(torch.linalg.vector_norm(changes,dim=-1)<=limits.squeeze(-1))
    rodrigues(changes).sum().backward();assert torch.isfinite(parameters.grad).all()
