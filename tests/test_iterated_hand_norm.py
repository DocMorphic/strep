import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import iterated_hand_norm as implementation


def nonlinear(x):
    return dict(vectors=np.array([[.8, x[0]**2, 0.]]), caps=np.ones(1), scales=np.ones(1),
                margins=np.ones(1), depths=np.array([.02-.01*x[0]]))


def test_relinearization_tracks_new_pose_and_preserves_original_caps(monkeypatch):
    snapshots = []; jacobians = []
    def proposal(model, trust, solver):
        jacobians.append(model['jacobian']['vectors'][0, 1, 0])
        return np.array([trust]), dict(status='Solved')
    monkeypatch.setattr(implementation, 'direction', proposal)
    start = np.zeros(1)
    point, report = implementation.solve(nonlinear, nonlinear, start, None, iterations=3,
        trusts=(.3,), checkpoint=lambda model, row: snapshots.append(copy.deepcopy((model, row))))
    np.testing.assert_array_equal(start, [0.])
    np.testing.assert_allclose(jacobians, [0., .6, 1.2], atol=1e-12)
    np.testing.assert_allclose(point, [.75])
    assert report['stop_reason'] == 'iteration_budget'
    assert all(row['accepted'] and row['after']['minimum_margin'] >= 0 for row in report['history'])
    assert report['history'][-1]['attempts'][0]['trials'][0]['accepted'] is False
    assert report['history'][-1]['attempts'][0]['trials'][1]['accepted'] is True
    assert all(np.array_equal(model['base']['caps'], [1.]) for model, _ in snapshots)
    assert not report['quality_approved'] and report['fresh_geometry_required']


def test_best_actual_candidate_selected_across_trusts(monkeypatch):
    monkeypatch.setattr(implementation, 'direction', lambda m, t, s: (np.array([t]), dict(status='AlmostSolved')))
    point, report = implementation.solve(nonlinear, nonlinear, [0.], None, iterations=1, trusts=(.1, .3))
    np.testing.assert_allclose(point, [.3])
    assert len(report['history'][0]['attempts']) == 2


def test_no_improvement_stops_without_spending_remaining_iterations(monkeypatch):
    calls = []
    def no_progress(m, t, s):
        calls.append(t); return np.zeros(1), dict(status='Solved')
    monkeypatch.setattr(implementation, 'direction', no_progress)
    point, report = implementation.solve(nonlinear, nonlinear, [0.], None, iterations=6, trusts=(.1,))
    assert len(calls) == 1 and len(report['history']) == 1
    np.testing.assert_array_equal(point, [0.])
    assert report['stop_reason'] == 'no_exact_feasible_improvement'


def test_later_caps_cannot_be_rebased_to_the_accepted_pose(monkeypatch):
    # The first iteration succeeds; mutating the cap from a checkpoint must be
    # detected before the next local model can legitimize a changed constraint.
    cap = np.ones(1)
    def sample(x):
        data = nonlinear(x); data['caps'] = cap; return data
    monkeypatch.setattr(implementation, 'direction', lambda m, t, s: (np.array([.1]), dict(status='Solved')))
    with pytest.raises(ValueError, match='rebasing'):
        implementation.solve(sample, sample, [0.], None, checkpoint=lambda m, r: cap.fill(2.))


def test_changed_witness_population_fails_closed():
    def changed(x):
        result = nonlinear(x); result['depths'] = np.array([.02, .01]); return result
    with pytest.raises(ValueError, match='population'):
        implementation.solve(nonlinear, changed, [0.], None)


def test_infeasible_start_is_rejected():
    with pytest.raises(ValueError, match='Motion-feasible'):
        implementation.solve(nonlinear, nonlinear, [.9], None)


def test_central_boundary_is_explicit_and_never_silently_clipped():
    def feasible(x):
        result = nonlinear(x); result['vectors'] *= 0; return result
    point, report = implementation.solve(feasible, feasible, [1.], None)
    assert report['stop_reason'] == 'central_probe_boundary' and report['history'] == []
    np.testing.assert_array_equal(point, [1.])


@pytest.mark.parametrize('options', [dict(iterations=0), dict(iterations=13), dict(iterations=True),
    dict(trusts=[]), dict(trusts=[0]), dict(trusts=[float('nan')]), dict(step=0)])
def test_invalid_budget_and_probes(options):
    with pytest.raises(ValueError): implementation.solve(nonlinear, nonlinear, [0.], None, **options)
