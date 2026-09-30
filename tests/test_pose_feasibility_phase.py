import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.optimize import minimize
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_feasibility_phase import PhaseOne


def solve(phase):
    return minimize(phase.objective, phase.initial, jac=True, method='SLSQP',
                    bounds=phase.bounds,
                    constraints=[dict(type='ineq', fun=lambda z:phase.constraints(z)[0],
                                      jac=lambda z:phase.constraints(z)[1])],
                    options=dict(ftol=1e-11, maxiter=100))


def test_feasible_problem_reaches_zero_slack_from_infeasible_geometry():
    def pair(x):
        return np.array([x[0]+.1*x[1]-1., .2-x[0]]), np.array([[1., .1], [-1., 0.]])
    phase = PhaseOne(pair, [0., 0.], [.1, 10.], [-.1, -10.], [.1, 10.], 1)
    assert phase.initial[-1] == 1.
    assert np.min(phase.constraints(phase.initial)[0]) >= 0
    result = solve(phase)
    assert result.success and abs(result.x[-1]) < 1e-9
    assert np.min(pair(phase.physical(result.x))[0]) >= -1e-9


def test_slack_never_relaxes_hard_constraint_even_when_geometry_is_infeasible():
    def pair(x):
        return np.array([x[0]-.5, .2-x[0]]), np.array([[1.], [-1.]])
    phase = PhaseOne(pair, [0.], [.1], [-1.], [1.], 1)
    result = solve(phase)
    assert result.success
    np.testing.assert_allclose(phase.physical(result.x), [.2], atol=1e-9)
    assert result.x[-1] == pytest.approx(.3, abs=1e-9)
    assert pair(phase.physical(result.x))[0][0] < -.29  # Solver success is not pose success.
    z = phase.initial.copy(); z[0] = 3.; z[-1] = 1000.
    assert phase.constraints(z)[0][1] == pytest.approx(-.1)
    assert phase.constraints(z)[1][1, -1] == 0.


def test_positive_slack_cannot_buy_a_variable_bound_violation():
    def pair(x):
        return np.array([x[0]-2., 5.-x[0]]), np.array([[1.], [-1.]])
    phase = PhaseOne(pair, [0.], [.2], [0.], [1.], 1)
    result = solve(phase)
    assert result.success
    assert phase.physical(result.x)[0] == pytest.approx(1.)
    assert result.x[-1] == pytest.approx(1.)


def test_scaled_augmented_jacobian_matches_finite_differences():
    def pair(x):
        return np.array([x[0]**2+x[1]-2., 4.-x@x]), np.array([[2*x[0], 1.], -2*x])
    phase = PhaseOne(pair, [.1, .2], [.2, 2.], [-1., -2.], [1., 2.], 1)
    z = phase.initial.copy(); h=1e-6
    fd = np.column_stack([(phase.constraints(z+h*e)[0]-phase.constraints(z-h*e)[0])/(2*h)
                          for e in np.eye(len(z))])
    np.testing.assert_allclose(phase.constraints(z)[1], fd, atol=1e-8)


@pytest.mark.parametrize('seed,scale,lower,upper,rows', [
    ([2.], [1.], [-1.], [1.], 1), ([0.], [0.], [-1.], [1.], 1),
    ([0.], [float('nan')], [-1.], [1.], 1), ([0.], [1.], [-1.], [1.], True),
    ([0.], [1.], [-1.], [1.], 2), ([0.], [1., 2.], [-1.], [1.], 1),
    ([.75], [1.], [-1.], [1.], 1)])
def test_malformed_or_hard_infeasible_seed_rejected(seed, scale, lower, upper, rows):
    def pair(x):
        return np.array([x[0]-1., .5-x[0]]), np.array([[1.], [-1.]])
    with pytest.raises(ValueError):PhaseOne(pair, seed, scale, lower, upper, rows)
