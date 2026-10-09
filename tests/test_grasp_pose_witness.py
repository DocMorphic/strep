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


def test_joint_only_native_fk_preserves_rotations_positions_and_all_derivatives():
    import torch
    from grasp_pose_witness import PoseProblem
    from support_contact_v8 import rodrigues
    problem=PoseProblem.__new__(PoseProblem)
    problem.parents=[-1,0,1];problem.lookup={0:0,2:1}
    problem.initial=rodrigues(torch.tensor([[.1,.2,-.1],[-.2,.1,.05],[.03,-.1,.2]],dtype=torch.float64))
    problem.root=torch.tensor([.3,.8,-.4],dtype=torch.float64)
    problem.offsets=torch.tensor([[0,0,0],[.1,.4,-.1],[.3,.1,.2]],dtype=torch.float64)
    problem.indices=np.tile([0,1,2,0,1,2,0,2],(5,1))
    problem.bind=torch.arange(120,dtype=torch.float64).reshape(5,8,3)/100
    problem.weights=torch.full((5,8),1/8,dtype=torch.float64)
    controls=torch.tensor([.02,-.03,.04,-.05,.06,.07,.008],dtype=torch.float64,requires_grad=True)
    full=problem.fk(controls);joints=problem.fk(controls,vertices=False)
    assert full[3].shape==(5,3) and joints[3] is None
    for before,after in zip(full[:3],joints[:3]):
        torch.testing.assert_close(before,after,rtol=0,atol=0)
    dense=torch.autograd.functional.jacobian(lambda x:torch.cat([a.flatten() for a in problem.fk(x)[:3]]),controls)
    joint=torch.autograd.functional.jacobian(lambda x:torch.cat([a.flatten() for a in problem.fk(x,vertices=False)[:3]]),controls)
    torch.testing.assert_close(dense,joint,rtol=0,atol=0)
    # A joint-only call must never access mesh inputs, even if they are absent.
    del problem.indices,problem.bind,problem.weights
    for before,after in zip(full[:3],problem.fk(controls,vertices=False)[:3]):
        torch.testing.assert_close(before,after,rtol=0,atol=0)
