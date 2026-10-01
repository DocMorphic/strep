import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from joint_ball_least_squares import margins, margin_jacobian, feasible_projection, solve


def test_axis_rotation_uses_existing_radius_excluded_by_box():
    target = np.array([.9, 0., 0.])
    full, report = solve(lambda x: x-target, np.zeros(3))
    box, other = solve(lambda x: x-target, np.zeros(3), ball=False)
    np.testing.assert_allclose(full, target, atol=1e-6)
    assert box[0] == pytest.approx(1./np.sqrt(3), abs=1e-6)
    assert report['final_cost'] < other['final_cost'] and not report['quality_approved']


def test_multiple_joint_balls_match_closed_form_projection():
    target = np.array([2., 2., 0., .1, .2, .3])
    answer, report = solve(lambda x: x-target, np.zeros(6))
    expected = target.copy(); expected[:3] /= np.linalg.norm(expected[:3])
    np.testing.assert_allclose(answer, expected, atol=2e-5)
    assert np.all(margins(answer) >= 0) and report['final_cost'] <= report['initial_cost']


def test_constraint_jacobian_matches_central_difference():
    x = np.array([.2, .3, -.1, .7, -.2, .1]); eps = 1e-6
    numeric = np.stack([(margins(x+e*eps)-margins(x-e*eps))/(2*eps) for e in np.eye(6)], axis=1)
    np.testing.assert_allclose(margin_jacobian(x), numeric, atol=1e-9)


def test_roundoff_projection_is_replayed_inside_same_budget():
    x = np.array([1.+1e-10, 0, 0, .1, .2, .3])
    projected = feasible_projection(x, ball=True)
    assert np.all(margins(projected) >= 0)
    np.testing.assert_array_equal(projected[3:], x[3:])
    box = feasible_projection(np.ones(3), ball=False)
    np.testing.assert_allclose(box, np.ones(3)/np.sqrt(3))


def test_invalid_start_and_nonfinite_residual_fail_closed():
    with pytest.raises(ValueError, match='Feasible'):
        solve(lambda x: x, [1.1, 0, 0])
    with pytest.raises(ValueError, match='triples'):
        solve(lambda x: x, [0, 0])
    with pytest.raises(ValueError, match='residual'):
        solve(lambda x: [np.nan], [0, 0, 0])


def test_residual_population_cannot_change_during_fit():
    count = [0]
    def residual(x):
        count[0] += 1
        return np.zeros(1 if count[0] == 1 else 2)
    with pytest.raises(ValueError, match='population'): solve(residual, np.zeros(3))


def test_iteration_limit_keeps_best_feasible_replayed_candidate():
    x, report = solve(lambda x: np.r_[10.*(x[1]-x[0]**2), 1.-x[0], x[2]],
                      np.zeros(3), iterations=1)
    assert np.all(margins(x) >= 0)
    assert report['final_cost'] <= report['initial_cost']
    assert all(h['minimum_joint_margin'] >= 0 for h in report['history'])
