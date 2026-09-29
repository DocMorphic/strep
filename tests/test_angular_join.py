import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from angular_join import rotation_log,angular_steps


@pytest.mark.parametrize('vectors',[[[0.,0.,0.],[1e-8,-2e-8,1e-8]],[[.2,-.3,.1],[2.,.4,-.1]]])
def test_log_matches_independent_rotation_library(vectors):
    matrices=Rotation.from_rotvec(vectors).as_matrix()
    np.testing.assert_allclose(rotation_log(torch.tensor(matrices)).numpy(),vectors,atol=1e-12)


def test_noncommuting_rate_step_jacobian_matches_difference():
    local=Rotation.from_rotvec([[.1,.2,.3],[.12,.17,.28],[.13,.21,.26],[.12,.24,.27]]).as_matrix()[:,None]
    variable=torch.tensor(local,requires_grad=True);value=angular_steps(variable)
    direction=np.random.default_rng(83).normal(size=local.shape);direction/=np.linalg.norm(direction)
    jac=torch.autograd.functional.jacobian(angular_steps,variable).detach().numpy()
    h=1e-6;fd=(angular_steps(torch.tensor(local+h*direction))-angular_steps(torch.tensor(local-h*direction))).numpy()/(2*h)
    np.testing.assert_allclose(np.tensordot(jac,direction,axes=4),fd,atol=1e-6,rtol=1e-6)
    rates=np.array([(Rotation.from_matrix(local[i]).inv()*Rotation.from_matrix(local[i+1])).as_rotvec()*30 for i in range(3)])
    np.testing.assert_allclose(value.detach().numpy(),np.linalg.norm(np.diff(rates,axis=0),axis=-1),atol=1e-12)


def test_identity_has_finite_derivative_and_pi_is_rejected():
    variable=torch.eye(3,dtype=torch.float64).requires_grad_()
    assert torch.isfinite(torch.autograd.functional.jacobian(rotation_log,variable)).all()
    with pytest.raises(ValueError):rotation_log(torch.tensor(Rotation.from_rotvec([np.pi,0,0]).as_matrix()))
