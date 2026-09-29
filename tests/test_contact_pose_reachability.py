from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_pose_reachability import point_bound


def test_zero_lever_requires_joint_displacement():
    result = point_bound([[0, 0, 0]], [1], [[0, 0, 0]], [.5, 0, 0])
    assert result['any_verified_conflict']
    assert .494 < result['joint_displacement_lower_bound_m'] < .496
    assert not result['quality_approved']


def test_arbitrary_rotation_allowance_prevents_false_conflict():
    result = point_bound([[0, 0, 0]], [1], [[.5, 0, 0]], [.5, 0, 0])
    assert not result['any_verified_conflict']


def test_all_eight_influences_and_actual_weight_mass_are_used():
    weights = np.array([.4, .1, .1, .1, .1, .1, .05, .05])*1.000001
    positions = np.zeros((8, 3));positions[-1, 0] = 10
    target = weights@positions
    result = point_bound(positions, weights, np.zeros((8, 3)), target)
    assert not result['any_verified_conflict']
    assert result['weight_sum'] == pytest.approx(weights.sum())


def test_constructed_rigid_candidate_inside_joint_budget_never_conflicts():
    rng = np.random.default_rng(22)
    from scipy.spatial.transform import Rotation
    for _ in range(50):
        weights = rng.random(8);weights /= weights.sum()
        positions = rng.normal(size=(8, 3));bind = rng.normal(size=(8, 3))*.05
        delta = rng.normal(size=(8, 3));delta *= (.22/np.linalg.norm(delta, axis=1))[:, None]
        rotation = Rotation.random(8, random_state=rng).as_matrix()
        target = (weights[:, None]*(positions+delta+np.einsum('vij,vj->vi', rotation, bind))).sum(0)
        assert not point_bound(positions, weights, bind, target)['any_verified_conflict']


def test_reserve_cannot_be_ignored_at_the_boundary():
    result = point_bound([[0, 0, 0]], [1], [[0, 0, 0]], [.2250005, 0, 0])
    assert not result['any_verified_conflict']


@pytest.mark.parametrize('weights', [[-1.], [0.], [float('nan')]])
def test_invalid_weights_rejected(weights):
    with pytest.raises(ValueError):point_bound([[0, 0, 0]], weights, [[0, 0, 0]], [0, 0, 0])


def test_invalid_rotation_assumption_rejected():
    with pytest.raises(ValueError):point_bound([[0, 0, 0]], [1], [[0, 0, 0]], [0, 0, 0], rotation_norm_bound=.99)
