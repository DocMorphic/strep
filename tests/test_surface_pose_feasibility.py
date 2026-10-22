from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import surface_pose_feasibility as fit
from test_surface_pose_window import window


def fixture():
    p = window(2)
    x = np.zeros((2, 6)); x[:, 1] = .02
    p.problems[0].bounds = [(float(v), float(v)) for v in x[0]]
    p.bounds = [b for problem in p.problems for b in problem.bounds]
    return p, x.reshape(-1)


def test_feasible_initial_is_preserved_without_invoking_optimizer(monkeypatch):
    p, x = fixture()
    monkeypatch.setattr(fit, 'minimize', lambda *a, **k: pytest.fail('Already feasible'))
    result, report = fit.propose(p, x, max_iterations=40)
    np.testing.assert_array_equal(result, x)
    assert result is not x and report['fitting_constraints_pass']
    assert report['iterations'] == 0 and report['solver_success'] is None
    assert report['requires_decoded_validation'] and not report['quality_approved']


def test_real_solve_repairs_step_violation_with_incoming_pose_fixed():
    p, x = fixture(); x[7] += .04; before = x.copy()
    assert not p.assess(x)['numerical_window_pass']
    original_acceptance = window(2)
    p.limits[0] -= 1e-5  # Explicit fitting reserve; original 25-mm check stays strict.
    result, report = fit.propose(p, x, max_iterations=40)
    np.testing.assert_array_equal(x, before)
    np.testing.assert_array_equal(result[:6], x[:6])
    assert original_acceptance.assess(result)['numerical_window_pass']
    assert report['minimum_fitting_gap'] > report['initial_minimum_fitting_gap']
    assert not report['release_approved']


def test_success_flag_cannot_hide_unselected_floor_failure(monkeypatch):
    p, x = fixture(); x[0] = x[6] = .1
    p.bounds[:6] = [(float(v), float(v)) for v in x[:6]]
    assert p.values(x).min() >= 0 and p.values(x, full=True).min() < 0
    monkeypatch.setattr(fit, 'minimize', lambda *a, **k: SimpleNamespace(x=x.copy(), success=True, message='success', nit=1))
    result, report = fit.propose(p, x, max_iterations=1)
    assert report['solver_success'] and not report['fitting_constraints_pass']
    assert not p.assess(result)['numerical_window_pass']


def test_final_regression_keeps_better_intermediate_and_failure_status(monkeypatch):
    p, x = fixture(); good = x.copy(); x[7] += .04
    def solver(*a, **kwargs):
        kwargs['callback'](good)
        return SimpleNamespace(x=x.copy(), success=False, message='Iteration limit reached', nit=1)
    monkeypatch.setattr(fit, 'minimize', solver)
    result, report = fit.propose(p, x, max_iterations=1)
    np.testing.assert_array_equal(result, good)
    assert report['fitting_constraints_pass'] and report['solver_success'] is False


@pytest.mark.parametrize('fault', ['fixed', 'bound', 'nan', 'shape', 'rows', 'bounds'])
def test_invalid_solver_output_or_mutation_rejected(monkeypatch, fault):
    p, x = fixture(); x[7] += .04
    def solver(*a, **kwargs):
        bad = x.copy()
        if fault == 'fixed': bad[0] += 1e-5
        if fault == 'bound': bad[7] = p.bounds[7][1]+1
        if fault == 'nan': bad[7] = np.nan
        if fault == 'shape': bad = bad[:-1]
        if fault == 'rows': p.problems[0].floor_vertices = np.array([1])
        if fault == 'bounds': p.bounds[7] = (0., 100.)
        return SimpleNamespace(x=bad, success=True, message='success', nit=1)
    monkeypatch.setattr(fit, 'minimize', solver)
    with pytest.raises(ValueError): fit.propose(p, x, max_iterations=1)


@pytest.mark.parametrize('count', [0, 1001, True, 1.5])
def test_explicit_iteration_budget_required(count):
    p, x = fixture()
    with pytest.raises(ValueError): fit.propose(p, x, max_iterations=count)


def test_fixed_infeasible_parameters_are_reported_without_solver(monkeypatch):
    p, x = fixture(); x[7] += .04
    p.bounds = [(float(v), float(v)) for v in x]
    monkeypatch.setattr(fit, 'minimize', lambda *a, **k: pytest.fail('No free parameters'))
    result, report = fit.propose(p, x, max_iterations=40)
    np.testing.assert_array_equal(result, x)
    assert not report['fitting_constraints_pass'] and report['solver_success'] is None


def test_sampled_native_rotation_window_proposes_without_worsening_complete_rows():
    from test_surface_pose_interpolation import models, problem
    from surface_pose_interpolation import InterpolatedPoseMap, SampledPoseWindow
    from surface_pose_window import CoupledPoseWindow
    a, b, sampled = models()
    keys = CoupledPoseWindow([problem(a), problem(b)], root_step_m=.025, rotation_step_degrees=5.)
    p = SampledPoseWindow(keys, [(0, InterpolatedPoseMap(a, b, sampled, .37), problem(sampled))])
    x = np.zeros(p.size); p.grow(x, batch_size=1)
    before = [q.floor_vertices.copy() for q in [*keys.problems, p.samples[0][2]]]
    result, report = fit.propose(p, x, max_iterations=2)
    assert max(0., -report['minimum_fitting_gap']) <= max(0., -report['initial_minimum_fitting_gap'])
    for q, rows in zip([*keys.problems, p.samples[0][2]], before):
        np.testing.assert_array_equal(q.floor_vertices, rows)
    assert report['requires_decoded_validation'] and not report['quality_approved']


@pytest.mark.parametrize('fault', ['jac_shape', 'jac_nan', 'different_values', 'row_count'])
def test_derivative_or_population_mismatch_is_rejected(monkeypatch, fault):
    p, x = fixture(); x[7] += .04
    pair = p.pair
    def bad_pair(values):
        g, j = pair(values)
        if fault == 'jac_shape': j = j[:, :-1]
        if fault == 'jac_nan': j[0, 0] = np.nan
        if fault == 'different_values': g[0] += .1
        if fault == 'row_count': g = np.r_[g, 1.]
        return g, j
    p.pair = bad_pair
    def solver(*a, **kwargs):
        kwargs['constraints']['jac'](x)
        pytest.fail('Invalid derivative accepted')
    monkeypatch.setattr(fit, 'minimize', solver)
    with pytest.raises(ValueError): fit.propose(p, x, max_iterations=1)
