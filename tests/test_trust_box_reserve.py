"""A smaller box can avoid large-step conservatism, without approving motion."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_scene_norms import NormRows
from measured_proposal_reserve import tighten
from trust_box_reserve import tighten_in_box, propose
import trust_box_reserve


def fixture():
    source = NormRows([[1., 0., 0.], [-.3, 0., 0.]], [1.12, 0.], [1., 1.])
    jac = sparse.csc_matrix(np.array([1., 0., 0., 1., 0., 0.])[:, None])
    deltas = np.array([[.3], [.1]])
    predicted = np.array([source.residual(jac, d)[:1] for d in deltas])
    actual = predicted + deltas**2
    return source, jac, deltas, predicted, actual


def test_real_solver_uses_small_box_error_without_large_trial_false_exclusion():
    source, jac, deltas, predicted, actual = fixture()
    all_trials, _, _ = tighten(source, predicted, actual, 1)
    assert all_trials.residual(jac, deltas[1])[0] > 0  # actual .1 step is safe
    assert actual[1, 0] < 0
    result, receipt = propose(source, jac, [0.], [-1.], [1.], .1, actual, deltas,
                              hard_rows=1, phase_seconds=1., maximum_iterations=100)
    assert result is not None and 0 < result[0] <= .1
    assert 1 + result[0] + result[0]**2 <= source.caps[0]
    assert receipt['calibration']['selected_trial_indices'] == [1]
    assert receipt['calibration']['outside_box_trial_indices'] == [0]
    assert receipt['solver']['trust_control_fraction'] == .1
    assert receipt['predictions_recomputed_from_original_model']
    assert not receipt['release_approved'] and receipt['independently_decoded_candidate_required']
    np.testing.assert_array_equal(source.caps, [1.12, 0.])


def test_box_uses_every_component_every_inside_trial_and_every_protected_row():
    source = NormRows(np.zeros((3, 3)), [2., 3., 0.], [1., 2., 1.])
    deltas = [[.01, .5], [.1, .01], [-.1, -.1], [0., 0.]]
    prediction = np.zeros((4, 2))
    actual = [[1., 1.], [.2, -.3], [.1, .4], [-.1, -.2]]
    result, reserve, receipt = tighten_in_box(source, prediction, actual, deltas, .1, 2)
    assert receipt['selected_trial_indices'] == [1, 2, 3]
    assert receipt['outside_box_trial_indices'] == [0]
    assert reserve[0] >= .2 and reserve[1] >= .8
    assert result.caps[2] == source.caps[2]
    np.testing.assert_array_equal(result.vectors, source.vectors)
    np.testing.assert_array_equal(result.scales, source.scales)


def test_outside_trial_exactly_adjacent_to_boundary_is_not_selected():
    source, _, _, _, _ = fixture()
    _, _, receipt = tighten_in_box(source, [[0.], [0.]], [[0.], [0.]],
                                  [[.1], [np.nextafter(.1, np.inf)]], .1, 1)
    assert receipt['selected_trial_indices'] == [0]


def test_another_direction_inside_same_box_can_still_fail_physical_cap():
    source = NormRows([[1., 0., 0.]], [1.1], [1.])
    jac = np.array([[[.1, 0.], [0., 0.], [0., 0.]]])
    model, _, receipt = tighten_in_box(source, [[-.09]], [[-.09]], [[.1, 0.]], .1, 1)
    other = np.array([0., .1])
    assert model.residual(jac, other)[0] < 0
    assert 1 + 100*other[1]**2 > source.caps[0]
    assert not receipt['future_directions_covered'] and not receipt['formal_error_bound_proven']


@pytest.mark.parametrize('trust', [0, -1, True, '1', float('nan'), float('inf')])
def test_invalid_trust_rejected(trust):
    with pytest.raises(ValueError, match='trust'):
        tighten_in_box(fixture()[0], [[0.]], [[0.]], [[0.]], trust, 1)


@pytest.mark.parametrize('deltas', [[], [[.2]], [[0., float('nan')]], [[True]], [[1j]], [[0.], [0.]], [[]]])
def test_missing_or_invalid_observation_association_rejected(deltas):
    with pytest.raises(ValueError):
        tighten_in_box(fixture()[0], [[0.]], [[0.]], deltas, .1, 1)


def test_invalid_outside_trial_is_not_hidden_by_box_selection():
    with pytest.raises(ValueError):
        tighten_in_box(fixture()[0], [[0.], [0.]], [[0.], [float('inf')]], [[0.], [.3]], .1, 1)


@pytest.mark.parametrize('value,lower,upper,deltas', [
    ([0.], [-1.], [1.], [[1.1]]), ([.5], [-1.], [1.], [[.6]]),
    ([0.], [-1.], [1.], [[0., 0.]]), ([2.], [-1.], [1.], [[0.]]),
    ([0.], [1.], [-1.], [[0.]]), ([True], [-1.], [1.], [[0.]]),
])
def test_proposal_refuses_mismatched_origin_controls_or_authored_boxes(value, lower, upper, deltas):
    with pytest.raises(ValueError):
        propose(fixture()[0], fixture()[1], value, lower, upper, .1, [[0.]], deltas, hard_rows=1)


def test_proposal_refuses_incomplete_model_derivative():
    source, _, deltas, _, actual = fixture()
    with pytest.raises(ValueError, match='Jacobian'):
        propose(source, np.zeros((1, 3, 1)), [0.], [-1.], [1.], .1, actual, deltas, hard_rows=1)


def test_proposal_preserves_solver_failure_instead_of_widening_box():
    source = NormRows([[2., 0., 0.], [0., 0., 0.]], [1., 0.], [1., 1.])
    delta, receipt = propose(source, sparse.csc_matrix((6, 1)), [0.], [-1.], [1.], .1,
                              [[1.]], [[0.]], hard_rows=1, phase_seconds=1.)
    assert delta is None and receipt['solver']['status'] == 'FixedProtectedConflict'
    assert receipt['calibration']['trust_control_fraction'] == .1
    assert not receipt['original_source_limits_changed'] and not receipt['quality_approved']


def test_solver_numerical_tolerance_cannot_extrapolate_calibration_box(monkeypatch):
    def outside(*args, **kwargs):
        return np.array([np.nextafter(.1, np.inf)]), dict(status='Solved')
    monkeypatch.setattr(trust_box_reserve, 'direction', outside)
    source, jac, deltas, _, actual = fixture()
    delta, receipt = propose(source, jac, [0.], [-1.], [1.], .1, actual, deltas, hard_rows=1)
    assert delta is None and receipt['solver']['calibration_box_rejected']
    assert receipt['solver']['rejected_delta'][0] > .1
    assert receipt['calibration_and_solver_trust_identical']
