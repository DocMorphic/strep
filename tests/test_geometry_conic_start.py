import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import geometry_conic_start as subject


def problem():
    return dict(values=np.array([-.5, 1.]), jac=np.array([[1.], [-1.]]), caps=np.array([-.5, 0.]),
        lower=np.array([0.]), upper=np.array([.4]), seconds=5.,
        vectors=dict(offsets=np.zeros((2, 3)), jacobian=np.array([[[1.], [0.], [0.]], [[1.], [0.], [0.]]]),
            limits=np.array([1., 1.]), scales=np.array([1., 1.]), rows=np.array([1, 1]), distance=np.array([True, False])))


@pytest.mark.parametrize('priority', ['merit', 'worst-first'])
def test_actual_complete_cone_start_preserves_every_scalar_duplicate_and_bound(priority):
    data=problem(); delta, report=subject.direction(**data, priority=priority)
    assert delta is not None and delta[0] == pytest.approx(.4, abs=1e-6)
    assert report['norm_cones'] == 2 and report['scalar_rows'] == 2
    assert report['success'] and report['minimum_linear_slack'] >= -1e-8
    assert report['minimum_vector_slack'] >= -1e-8
    assert np.all(data['values']+data['jac']@delta >= data['caps']-1e-8)
    assert report['directional_merit'] < -1e-8
    assert not report['retained'] and not report['quality_approved'] and not report['release_approved']


def test_conflicting_complete_scalar_row_returns_no_start():
    data=problem(); data['caps'][0]=.1
    delta, report=subject.direction(**data)
    assert delta is None and not report['success'] and report['primary_status']=='PrimalInfeasible'
    assert not report['release_approved']


def test_zero_gradient_and_empty_vector_radius_do_not_invoke_solver(monkeypatch):
    monkeypatch.setattr(subject, 'solver_module', lambda:pytest.fail('No solver needed'))
    data=problem(); data['values'][0]=0.
    delta, report=subject.direction(**data)
    assert delta is None and report['status']=='no_checked_geometry_descent'
    data=problem(); data['caps'][1]=1.
    delta, report=subject.direction(**data)
    assert delta is None and report['status']=='empty_vector_radius'


@pytest.mark.parametrize('field,value', [('values', [np.nan, 1.]), ('jac', [[1.]]), ('caps', [-.5]),
    ('lower', [.5]), ('upper', [np.inf]), ('seconds', 0.), ('seconds', 21.), ('seconds', True)])
def test_invalid_complete_system_is_rejected_before_solver(monkeypatch, field, value):
    monkeypatch.setattr(subject, 'solver_module', lambda:pytest.fail('Invalid system must not solve'))
    data=problem(); data[field]=value
    with pytest.raises(ValueError):subject.direction(**data)


@pytest.mark.parametrize('field,value', [('offsets', [[0., 0., 0.]]), ('jacobian', [[[np.inf], [0.], [0.]]]*2),
    ('limits', [0., 1.]), ('scales', [1., 0.]), ('rows', [1., 1.]), ('rows', [1, 2]),
    ('distance', [1, 0]), ('offsets', [[.1, 0., 0.], [0., 0., 0.]])])
def test_invalid_or_mismatched_complete_vectors_are_rejected(monkeypatch, field, value):
    monkeypatch.setattr(subject, 'solver_module', lambda:pytest.fail('Invalid vectors must not solve'))
    data=problem(); data['vectors'][field]=value
    with pytest.raises(ValueError):subject.direction(**data)


def fake_backend(monkeypatch, points):
    actual=subject.solver_module(); phases=[]
    def solver(p,q,a,b,cones,settings):
        phases.append((a,b,cones,settings))
        result=SimpleNamespace(x=points[len(phases)-1], status='Solved', iterations=1)
        return SimpleNamespace(solve=lambda:result)
    monkeypatch.setattr(subject, 'solver_module', lambda:SimpleNamespace(__version__=actual.__version__,
        DefaultSettings=actual.DefaultSettings, NonnegativeConeT=actual.NonnegativeConeT,
        SecondOrderConeT=actual.SecondOrderConeT, DefaultSolver=solver))
    return phases


@pytest.mark.parametrize('point', [[np.nan, .1], [.5, 0.], [.2, 0.], [0., .5], [.4]])
def test_success_status_cannot_hide_invalid_or_unchecked_primary(monkeypatch, point):
    phases=fake_backend(monkeypatch, [point]); delta, report=subject.direction(**problem())
    assert delta is None and report['status']=='primary_replay_failed' and len(phases)==1


def test_secondary_failure_preserves_checked_primary_without_retention(monkeypatch):
    phases=fake_backend(monkeypatch, [[.4,.1], [.2, 0.]])
    delta, report=subject.direction(**problem())
    np.testing.assert_array_equal(delta, [.4])
    assert report['selected_phase']=='primary' and report['secondary_replay']['check_status']=='priority_epigraph_failed'
    assert len(phases)==2 and report['retained'] is False


def test_secondary_cannot_exceed_original_epigraph_tie(monkeypatch):
    fake_backend(monkeypatch, [[.4,.1], [.3,.2]])
    delta, report=subject.direction(**problem())
    np.testing.assert_array_equal(delta, [.4])
    assert report['selected_phase']=='primary'


def test_complete_norm_replay_rejects_solver_status_even_when_scalar_rows_pass(monkeypatch):
    data=problem(); data['vectors']['jacobian']*=10
    fake_backend(monkeypatch, [[.4,.1]])
    delta, report=subject.direction(**data)
    assert delta is None and report['minimum_vector_slack'] < -1e-8
    assert report['status']=='primary_replay_failed'


def test_budget_between_phases_keeps_only_checked_unretained_primary(monkeypatch):
    phases=fake_backend(monkeypatch, [[.4,.1]])
    clock=iter([0., 0., 6., 6.]); monkeypatch.setattr(subject.time, 'monotonic', lambda:next(clock))
    delta, report=subject.direction(**problem())
    np.testing.assert_array_equal(delta, [.4])
    assert len(phases)==1 and report['secondary_status']=='budget_exhausted' and report['retained'] is False


def test_clipping_is_replayed_against_all_rows(monkeypatch):
    fake_backend(monkeypatch, [[.4+1e-10,.1], [.4+1e-10,.1]])
    delta, report=subject.direction(**problem())
    np.testing.assert_array_equal(delta, [.4])
    assert report['clipped_to_step_bounds'] and report['minimum_linear_slack'] >= -1e-8


def test_optional_backend_version_is_pinned(monkeypatch):
    monkeypatch.setitem(sys.modules, 'clarabel', SimpleNamespace(__version__='0.0.0'))
    with pytest.raises(ValueError, match='0.11.1'):subject.solver_module()


def test_nonfinite_derived_gradient_is_rejected_before_backend(monkeypatch):
    monkeypatch.setattr(subject, 'solver_module', lambda:pytest.fail('No nonfinite model must solve'))
    data=problem(); data['jac'][0,0]=1e308; data['values'][0]=-10.
    with pytest.warns(RuntimeWarning), pytest.raises(ValueError, match='derived'):
        subject.direction(**data)


def test_expired_budget_before_primary_does_not_launch_solver(monkeypatch):
    phases=fake_backend(monkeypatch, [])
    clock=iter([0., 6., 6.]); monkeypatch.setattr(subject.time, 'monotonic', lambda:next(clock))
    delta, report=subject.direction(**problem())
    assert delta is None and report['status']=='geometry_start_time_guard' and not phases
