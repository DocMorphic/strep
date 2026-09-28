import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from grasp_pose_witness import norm_slack_and_jacobian


def test_joint_norm_bound_rejects_component_box_corner_and_jacobian_matches():
    limits=np.array([.2,.7]);x=np.r_[[.18,.18,0],[.1,-.2,.3],.01]
    slack,jac=norm_slack_and_jacobian(x,limits)
    assert slack[0]<0 and slack[1]>0
    direction=np.array([.1,-.2,.3,-.4,.5,.6,.7]);h=1e-7
    fd=(norm_slack_and_jacobian(x+h*direction,limits)[0]-norm_slack_and_jacobian(x-h*direction,limits)[0])/(2*h)
    np.testing.assert_allclose(jac@direction,fd,rtol=1e-8,atol=1e-8)
    np.testing.assert_array_equal(jac[:,-1],0)


def test_smooth_max_conservatively_bounds_exact_max_and_has_finite_gradient():
    import torch
    from grasp_pose_witness import conservative_max
    values=torch.tensor([.002,.002,-.03],dtype=torch.float64,requires_grad=True)
    temperature=.0001
    value=conservative_max(values,temperature)
    assert values.max()<=value<=values.max()+temperature*np.log(len(values))
    value.backward()
    assert torch.isfinite(values.grad).all()
    np.testing.assert_allclose(values.grad.sum(),1.,atol=1e-12)
    assert conservative_max(values,0)==values.max()
