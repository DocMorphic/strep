import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v7 import inequality_merit,relative_track_speed


def test_inequality_merit_gradient_respects_feasibility_and_multiplier():
    g=torch.tensor([-.2,-.05,.1],dtype=torch.float64,requires_grad=True)
    multiplier=torch.tensor([1.,1.,1.],dtype=torch.float64)
    loss=inequality_merit(g,multiplier,10.).sum();loss.backward()
    np.testing.assert_allclose(g.grad,[0,.5,2],atol=1e-12)
    # Feasible inactive constraint has no force; a violated one pushes down g.
    assert inequality_merit(torch.tensor(0.),torch.tensor(0.),10.)==0


def test_tracking_a_moving_grip_is_not_world_sliding():
    target=torch.tensor([[[0.,0.,0.]],[[.1,.2,0.]],[[.2,.4,.1]]],dtype=torch.float64)
    points=(target+torch.tensor([.005,0,0])).requires_grad_()
    speed=relative_track_speed(points,target)
    torch.testing.assert_close(speed,torch.zeros_like(speed),atol=1e-12,rtol=0)
    speed.square().sum().backward();assert torch.isfinite(points.grad).all()
    assert relative_track_speed(torch.zeros_like(target),target).min()>6
