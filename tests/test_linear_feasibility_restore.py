from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from linear_feasibility_restore import linear_step, restore


def test_repairs_known_linear_violation_with_minimum_bounded_step():
    x = np.array([0., 0.]); c = np.array([-2e-5, .1]); j = np.array([[10., 0.], [0., -1.]])
    delta, proof = linear_step(x, c, j, np.ones(2), trust=1e-5, margin=1e-5)
    assert proof['success']
    np.testing.assert_allclose(delta[0], 3e-6, atol=1e-12)
    assert np.max(np.abs(delta)) <= 1e-5
    assert (c+j@delta).min() >= 1e-5-1e-10


def test_conflicting_inequalities_return_infeasible_without_a_fake_step():
    delta, proof = linear_step(np.zeros(1), np.array([-1., -1.]), np.array([[1.], [-1.]]), np.ones(1), trust=.1, margin=0.)
    assert delta is None and not proof['success']


def test_constant_rows_and_absolute_bound_are_preserved():
    x = np.array([.999999]); c = np.array([-1e-6, 0.]); j = np.array([[1.], [0.]])
    delta, proof = linear_step(x, c, j, np.ones(1), trust=1e-5, margin=0.)
    assert proof['success'] and x[0]+delta[0] <= 1.+1e-12
    assert proof['constant_constraints'] == 1
    delta, proof = linear_step(x, np.array([-1e-6, -.001]), j, np.ones(1), trust=1e-5, margin=0.)
    assert delta is None and not proof['success']


def test_nonfinite_input_rejected():
    with pytest.raises(ValueError): linear_step(np.zeros(1), np.array([np.nan]), np.ones((1, 1)), np.ones(1))


def test_restoration_rejects_target_tradeoff_and_retains_failed_search():
    from types import SimpleNamespace
    class Problem:
        fitter = SimpleNamespace(bounds=np.ones(1))
        free = np.array([0]); frames = np.array([0])
        def evaluate(self, x):
            target = max(0., float(x[0])-1e-6)**2
            return target, np.zeros(1), np.array([10*x[0]-2e-5]), np.array([[10.]]), None, self.values(x)
        def values(self, x): return np.asarray(x).reshape(1, 1)
        def geometric_guard(self, values): return True
    values, proof = restore(Problem(), np.zeros(1), attempts=1, trust=1e-5, margin=1e-5)
    assert not proof['feasible'] and proof['final_target_objective'] == 0.
    assert 0 < values[0, 0] <= 1e-6
    assert not proof['history'][0]['safeguard_trials'][0]['acceptable']
    assert proof['history'][0]['selected_fraction'] < 1.
