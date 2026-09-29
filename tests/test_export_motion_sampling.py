import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_motion_sampling import matrix_quaternion,quaternion_matrix,slerp,joint_trajectory,motion_rates
from support_contact_v5 import rodrigues
from rig_clip_import import AnimationSampler


def test_quaternion_conversion_matches_scipy_at_identity_and_half_turns():
    v=np.array([[0.,0.,0.],[np.pi,0.,0.],[0.,np.pi,0.],[0.,0.,np.pi],[.3,-.4,1.2]])
    matrices=Rotation.from_rotvec(v).as_matrix()
    actual=quaternion_matrix(matrix_quaternion(torch.tensor(matrices))).numpy()
    np.testing.assert_allclose(actual,matrices,atol=1e-14)
    angles=torch.tensor(v,requires_grad=True)
    assert torch.autograd.gradcheck(lambda x:quaternion_matrix(matrix_quaternion(rodrigues(x))),(angles,))


@pytest.mark.parametrize('angle',[0.,1e-8,.2,2.8])
def test_slerp_matches_export_sampler_including_antipodal_quaternions(angle):
    q=Rotation.from_rotvec([[0.,0.,0.],[angle,.1*angle,0.]]).as_quat()
    for sign in [1,-1]:
        a=torch.tensor(q[0][[3,0,1,2]],requires_grad=True)
        b=torch.tensor(q[1][[3,0,1,2]]*sign,requires_grad=True)
        for t in [.0,.25,.5,.75,1.]:
            actual=slerp(a,b,t)
            expected=AnimationSampler.value('rotation',np.array([0.,1.]),np.stack([q[0],q[1]*sign]),'LINEAR',t)
            np.testing.assert_allclose(quaternion_matrix(actual).detach(),Rotation.from_quat(expected).as_matrix(),atol=1e-12)
        assert torch.autograd.gradcheck(lambda x,y:quaternion_matrix(slerp(x,y,.37)),(a,b),atol=1e-5)


def test_chained_joint_trajectory_differentiates_between_key_acceleration():
    angles=torch.tensor([[[0.,0.,0.],[0.,0.,0.]],[[0.,.2,0.],[0.,0.,.1]],[[0.,.3,0.],[0.,0.,.2]]],dtype=torch.float64,requires_grad=True)
    positions=torch.tensor([[[0.,0.,0.],[1.,0.,0.]],[[.1,0.,0.],[1.,0.,.1]],[[.2,0.,0.],[1.,0.,.2]]],dtype=torch.float64,requires_grad=True)
    assert torch.autograd.gradcheck(lambda a,p:joint_trajectory(rodrigues(a),p,[-1,0]),(angles,positions),atol=1e-4)
    velocity,acceleration=motion_rates(joint_trajectory(rodrigues(angles),positions,[-1,0]))
    assert velocity.shape==(8,2) and acceleration.shape==(7,2)
    gradients=torch.autograd.grad(acceleration.square().sum(),[angles,positions])
    assert all(torch.isfinite(g).all() for g in gradients)
    assert gradients[0].abs().max()>0


def test_invalid_sampling_layouts_rejected():
    r=torch.eye(3,dtype=torch.float64).expand(3,2,3,3);p=torch.zeros(3,2,3,dtype=torch.float64)
    for parents in [[1,-1],[-1],[-2,0]]:
        with pytest.raises(ValueError):joint_trajectory(r,p,parents)
    with pytest.raises(ValueError):joint_trajectory(r.float(),p.float(),[-1,0])
    with pytest.raises(ValueError):joint_trajectory(r,p,[-1,0],subdivisions=True)
