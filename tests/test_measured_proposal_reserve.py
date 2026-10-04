"""Measured proposal error cannot relax source limits or establish clip quality."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_scene_norms import NormRows
from measured_proposal_reserve import tighten
from budgeted_native_conic import direction


def model():
    return NormRows([[1., 0., 0.], [-.3, 0., 0.]], [1.22, 0.], [1., 1.])


def test_real_bounded_solver_rejects_a_false_linear_success_after_measured_reserve():
    source = model()
    jac = sparse.csc_matrix(np.array([1., 0., 0., 1., 0., 0.])[:, None])
    kwargs = dict(hard_rows=1, phase_seconds=1., maximum_iterations=100)
    raw, record = direction(source, jac, np.zeros(1), -np.ones(1), np.ones(1), .3, **kwargs)
    assert raw is not None
    predicted = source.residual(jac, raw)[:1]
    # Complete nonlinear fixture observation; all original physical caps are
    # retained. The hard quantity has curvature absent from its affine model.
    actual = np.array([1. + raw[0] + raw[0]**2 - source.caps[0]])
    assert predicted[0] < 1e-7 and actual[0] > .04
    reserved, margins, receipt = tighten(source, predicted[None], actual[None], 1)
    repaired, _ = direction(reserved, jac, np.zeros(1), -np.ones(1), np.ones(1), .3, **kwargs)
    assert repaired is not None and repaired[0] < raw[0]
    assert 1. + repaired[0] + repaired[0]**2 <= source.caps[0]
    np.testing.assert_array_equal(source.caps, [1.22, 0.])
    np.testing.assert_array_equal(reserved.caps[1:], source.caps[1:])
    assert margins[0] >= raw[0]**2 and receipt['tightened_rows'] == 1
    assert not receipt['formal_error_bound_proven'] and not receipt['quality_approved']


def test_all_trials_all_hard_rows_and_original_soft_targets_are_preserved():
    source = NormRows(np.zeros((4, 3)), [2., 3., 4., 0.], [.5, 2., 4., 1.])
    original = [a.copy() for a in (source.vectors, source.caps, source.scales)]
    predicted = np.zeros((3, 3))
    actual = [[.2, -.5, 0.], [.1, .3, -.1], [-.5, .1, .4]]
    result, reserves, receipt = tighten(source, predicted, actual, 3, factor=2.)
    assert np.all(reserves >= [.2, 1.2, 3.2])
    assert result.caps[3] == 0. and receipt['complete_observed_trials'] == 3
    for before, after in zip(original, (source.vectors, source.caps, source.scales)):
        np.testing.assert_array_equal(before, after)
    np.testing.assert_array_equal(result.vectors, source.vectors)
    np.testing.assert_array_equal(result.scales, source.scales)
    result.vectors[:] = 9
    result.scales[:] = 9
    np.testing.assert_array_equal(source.vectors, original[0])
    np.testing.assert_array_equal(source.scales, original[2])


def test_no_observed_underprediction_retains_exact_original_model():
    source = model()
    result, reserves, receipt = tighten(source, [[1.], [2.]], [[.5], [2.]], 1)
    for old, new in zip((source.vectors, source.caps, source.scales), (result.vectors, result.caps, result.scales)):
        np.testing.assert_array_equal(old, new)
    np.testing.assert_array_equal(reserves, [0.])
    assert receipt['tightened_rows'] == 0


def test_small_positive_reserve_is_not_lost_to_floating_point_subtraction():
    source = NormRows([[1., 0., 0.]], [1.], [1.])
    result, reserves, _ = tighten(source, [[0.]], [[np.nextafter(0., 1.)]], 1)
    assert result.caps[0] == np.nextafter(1., -np.inf) and reserves[0] > 0


def test_positive_error_with_zero_cap_rejects_without_clamping_or_relaxing():
    source = NormRows([[0., 0., 0.]], [0.], [1.])
    with pytest.raises(ValueError, match='exceeds'):
        tighten(source, [[0.]], [[.1]], 1)
    assert source.caps[0] == 0.


def test_empirical_reserve_is_not_a_bound_for_a_different_nonlinear_direction():
    source = NormRows([[1., 0., 0.]], [1.1], [1.])
    # The first observed direction has zero error; another direction can have
    # arbitrarily greater curvature. No passing helper receipt approves it.
    result, _, receipt = tighten(source, [[-.1]], [[-.1]], 1)
    jac = np.array([[[.1], [0.], [0.]]])
    other = np.array([.8])
    other_predicted = result.residual(jac, other)[0]
    other_actual = 1. + .1 * other[0] + other[0]**2 - source.caps[0]
    assert other_predicted <= 0 < other_actual and result.caps[0] == source.caps[0]
    assert not receipt['future_directions_covered']
    assert receipt['exported_constraints_and_geometry_required']


@pytest.mark.parametrize('rows', [0, -1, 3, True, 1., '1'])
def test_incomplete_or_invalid_hard_prefix_rejected(rows):
    with pytest.raises(ValueError, match='prefix'):
        tighten(model(), [[0.]], [[0.]], rows)


@pytest.mark.parametrize('factor', [0., .99, True, '1', float('nan'), float('inf')])
def test_invalid_margin_factor_rejected(factor):
    with pytest.raises(ValueError, match='factor'):
        tighten(model(), [[0.]], [[0.]], 1, factor=factor)


@pytest.mark.parametrize('predicted,actual', [
    ([], []), ([[0., 0.]], [[0., 0.]]), ([[0.]], [[0.], [1.]]),
    ([0.], [0.]), ([[float('nan')]], [[0.]]), ([[0.]], [[float('inf')]]),
    ([[True]], [[False]]), ([[1j]], [[0.]]), ([['0']], [[0.]]),
])
def test_missing_rows_trials_and_nonreal_observations_rejected(predicted, actual):
    with pytest.raises(ValueError):
        tighten(model(), predicted, actual, 1)


def test_overflow_and_impossible_reserves_rejected():
    with pytest.raises(ValueError, match='overflowed'):
        tighten(model(), [[-1e308]], [[1e308]], 1)
    with pytest.raises(ValueError, match='exceeds'):
        tighten(model(), [[0.]], [[2.]], 1)
    source = NormRows([[0., 0., 0.]], [-.1], [1.])
    with pytest.raises(ValueError, match='Negative'):
        tighten(source, [[0.]], [[0.]], 1)
