import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v5 import correction_basis,bounded_rotation


@pytest.mark.parametrize('frames,spacing',[(3,6),(30,6),(120,6),(31,1)])
def test_edit_basis_reproduces_constant_and_linear_controls(frames,spacing):
    basis,knots=correction_basis(frames,spacing)
    np.testing.assert_allclose(basis.sum(1),1,atol=1e-12)
    np.testing.assert_allclose(basis@knots,np.arange(frames),atol=1e-12)
    np.testing.assert_allclose(basis[knots],np.eye(len(knots)),atol=1e-12)


def test_rotation_budget_holds_even_when_cubic_controls_overshoot():
    basis,knots=correction_basis(30,6)
    controls=torch.zeros((len(knots),1,3),dtype=torch.float64,requires_grad=True)
    with torch.no_grad():controls[:,0,0]=torch.tensor([100*(-1)**i for i in range(len(knots))])
    interpolated=torch.einsum('fk,kjd->fjd',torch.tensor(basis),controls)
    rotations=bounded_rotation(interpolated,.7)
    assert torch.linalg.vector_norm(rotations,dim=-1).max()<=.7
    rotations.sum().backward();assert torch.isfinite(controls.grad).all()
