import numpy as np
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scipy.spatial.transform import Rotation
from rigid_contact_normal_bound import pairwise_bound
from rigid_normal_spread import bound as object_bound


def test_exact_rotated_field_has_zero_bound_even_when_current_facing_fails():
    source = np.eye(3)[None]
    target = -Rotation.from_euler('xyz', [70, 20, 95], degrees=True).apply(source[0])[None]
    result = pairwise_bound(source, target)
    np.testing.assert_allclose(result['lower_bound_degrees'], 0, atol=1e-12)
    assert result['necessary_only'] and not result['rotation_found']
    assert not result['skin_deformation_ruled_out'] and not result['quality_approved']


def test_complete_frames_and_pairs_include_antipodal_witness():
    source = np.array([[[1, 0, 0], [1, 0, 0], [-1, 0, 0]],
                       [[1, 0, 0], [0, 1, 0], [-1, 0, 0]]])
    target = np.broadcast_to([1, 0, 0], source.shape)
    result = pairwise_bound(source, target, maximum_pairs=3)
    np.testing.assert_array_equal(result['lower_bound_degrees'], [90, 90])
    np.testing.assert_array_equal(result['pair_indices'], [[0, 1], [0, 2], [1, 2]])
    np.testing.assert_array_equal(result['maximizing_pair'], [[0, 2], [0, 2]])


def test_passing_necessary_bound_does_not_prove_a_rotation():
    # Three equatorial vectors sum to zero. They cannot all have dot product
    # >= cos(60 degrees) with one target, even though each pair bound is 60.
    angle = np.deg2rad([0, 120, 240])
    source = np.c_[np.cos(angle), np.sin(angle), np.zeros(3)][None]
    target = np.broadcast_to([0, 0, 1], source.shape)
    result = pairwise_bound(source, target)
    np.testing.assert_allclose(result['lower_bound_degrees'], 60, atol=1e-12)
    np.testing.assert_allclose(source.sum(axis=1), 0, atol=1e-12)
    assert not result['rotation_found']


def test_absolute_gap_is_symmetric_and_target_negation_invariant():
    a = np.array([[[1, 0, 0], [1, 0, 0]]])
    b = np.array([[[1, 0, 0], [0, 1, 0]]])
    for left, right in [(a, b), (b, a), (a, -b)]:
        np.testing.assert_allclose(pairwise_bound(left, right)['lower_bound_degrees'], [45])


@pytest.mark.parametrize('bad', [np.zeros((1, 2, 3)), np.full((1, 2, 3), np.nan),
    np.ones((1, 2, 3)), np.empty((0, 2, 3)), np.ones((1, 1, 3)), np.ones((2, 3))])
def test_incomplete_or_unreliable_normals_reject(bad):
    with pytest.raises(ValueError):
        pairwise_bound(bad, bad)


def test_matching_populations_and_complete_budget_required():
    good = np.eye(3)[None]
    with pytest.raises(ValueError, match='matching'):
        pairwise_bound(good, good[:, :2])
    with pytest.raises(ValueError, match='no subset'):
        pairwise_bound(good, good, maximum_pairs=2)
    for bad in [True, 0, 65537, 3.0]:
        with pytest.raises(ValueError, match='budget'):
            pairwise_bound(good, good, maximum_pairs=bad)


def test_existing_object_bound_agrees_for_rotating_common_target_frames():
    rng = np.random.default_rng(763)
    source = rng.normal(size=(7, 5, 3)); source /= np.linalg.norm(source, axis=2, keepdims=True)
    local = rng.normal(size=(5, 3)); local /= np.linalg.norm(local, axis=1, keepdims=True)
    rotations = Rotation.from_euler('xyz', rng.uniform(-180, 180, size=(7, 3)), degrees=True)
    world = np.einsum('fij,pj->fpi', rotations.as_matrix(), local)
    current = pairwise_bound(source, world)
    legacy_report, legacy = object_bound(source, local, 15.)
    np.testing.assert_allclose(current['lower_bound_degrees'], legacy['lower_bound_degrees'], atol=1e-12, rtol=0)
    assert legacy_report['necessary_condition_only'] and not legacy_report['rigid_rotation_feasibility_proven']
    assert not current['rotation_found'] and not current['skin_deformation_ruled_out']
