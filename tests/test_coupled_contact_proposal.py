import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from shared_palm_meeting import target, measure
from coupled_contact_proposal import contact_margins, solve
from joint_ball_least_squares import margins


def specification():
    return target([[0, 0, -.01], [0, 0, .01]], [[0, 0, 1], [0, 0, -1]])


def test_contact_norm_constraints_match_independent_contact_screen():
    spec = specification(); rng = np.random.default_rng(4)
    for _ in range(100):
        centers = np.array(spec['centers_m'])+rng.normal(size=(2, 3))*.0004
        normals = np.array(spec['normals'])+rng.normal(size=(2, 3))*.3
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        assert bool(np.all(contact_margins(centers, normals, spec) >= 0)) == measure(centers, normals, spec)['contact_target_pass']


def test_contacts_remain_hard_while_both_actors_move():
    desired = np.array([.8, 0, 0, -.8, 0, 0])
    hard = lambda x: np.array([.16-x[0]**2, .16-x[3]**2, .0001-(x[0]+x[3])**2])
    point, report = solve(lambda x: x-desired, hard, np.zeros(6))
    assert np.all(hard(point) >= 0) and np.all(margins(point) >= 0)
    assert point[0] > .3 and point[3] < -.3
    assert report['final_cost'] < report['initial_cost'] and not report['quality_approved']


def test_replay_can_reject_smooth_feasible_candidate():
    residual = lambda x: x-np.array([.8, 0, 0])
    point, report = solve(residual, lambda x: np.array([1.-x[0]]), np.zeros(3),
        replay_hard=lambda x: np.array([.25-x[0]]))
    assert 0 < point[0] <= .25
    assert any(not trial['contact_pass'] for row in report['history'] for trial in row['attempts'])


def test_no_serialized_feasible_improvement_retains_source():
    point, report = solve(lambda x: x-np.array([.8, 0, 0]), lambda x: np.ones(1), np.zeros(3),
        replay_hard=lambda x: np.array([-abs(x[0])]))
    np.testing.assert_array_equal(point, np.zeros(3))
    assert report['final_cost'] == report['initial_cost']


def test_invalid_contact_and_changed_population_rejected():
    with pytest.raises(ValueError, match='Initially feasible'):
        solve(lambda x: x, lambda x: [-1], np.zeros(3))
    count = [0]
    def hard(x):
        count[0] += 1
        return np.ones(1 if count[0] == 1 else 2)
    with pytest.raises(ValueError, match='population'):
        solve(lambda x: x, hard, np.zeros(3))


def test_invalid_target_threshold_is_not_silently_relaxed():
    spec = specification(); spec['anchor_tolerance_m'] = 0
    with pytest.raises(ValueError, match='Positive'):
        contact_margins(spec['centers_m'], spec['normals'], spec)
