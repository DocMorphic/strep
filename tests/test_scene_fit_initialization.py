import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from scene_fit_initialization import recover_controls
from support_contact_v8 import bounded_edit_rotations
from support_contact_v5 import rodrigues


@pytest.mark.parametrize('physical', [False, True])
def test_recovery_keeps_original_body_and_finger_parameter_bounds(physical):
    basis = np.array([[1., 0.], [.75, .25], [.5, .5], [.25, .75], [0., 1.]])
    limits = np.deg2rad([40., 8., 12.])
    controls = np.random.default_rng(42).normal(size=(2, 3, 3)) * .03
    params = torch.tensor(np.einsum('fk,kjd->fjd', basis, controls))
    bounded = bounded_edit_rotations(params, torch.tensor(limits)[None, :, None], 1, physical)
    source = np.broadcast_to(np.eye(3), (5, 4, 3, 3)).copy()
    seed = source.copy(); seed[:, [0, 2, 3]] = rodrigues(bounded).numpy()
    recovered, proof = recover_controls(source, seed, [0, 2, 3], limits, 1, physical, basis)
    np.testing.assert_allclose(recovered, controls, atol=1e-12)
    assert proof['original_edit_budgets_preserved']
    # Subsequent controls are still bounded against source, not multiplied onto seed.
    excessive = torch.tensor(recovered * 1e6)
    rotations = bounded_edit_rotations(excessive, torch.tensor(limits)[None, :, None], 1, physical)
    assert np.all(np.linalg.norm(rotations.numpy(), axis=-1) <= limits)


def test_seed_beyond_original_budget_rejected():
    source = np.broadcast_to(np.eye(3), (3, 1, 3, 3)).copy()
    vec = torch.tensor([[[.5, 0., 0.]]] * 3, dtype=torch.float64)
    with pytest.raises(ValueError, match='original rotation budgets'):
        recover_controls(source, rodrigues(vec).numpy(), [0], [.2], 1, False, np.ones((3, 1)))


def test_unrepresentable_seed_not_silently_projected():
    source = np.broadcast_to(np.eye(3), (3, 1, 3, 3)).copy()
    vec = torch.tensor([[[0., 0., 0.]], [[.1, 0., 0.]], [[0., 0., 0.]]], dtype=torch.float64)
    with pytest.raises(ValueError, match='original correction spline'):
        recover_controls(source, rodrigues(vec).numpy(), [0], [.7], 1, False, np.ones((3, 1)))
