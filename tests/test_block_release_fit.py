from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from block_release_fit import temporal_pair, norm_envelope_pair, adjacent_pair, BlockProblem, solve
from test_guarded_release_fit import ToyFitter
from serialized_pose import SerializedPose


def test_temporal_block_derivative_includes_coupled_neighbors():
    rng = np.random.default_rng(507)
    points = rng.normal(size=(8, 2, 3))*.01
    derivative = np.zeros((8, 2, 3, 6))
    derivative[2, :, :, :3] = rng.normal(size=(2, 3, 3))*.01
    derivative[3, :, :, 3:] = rng.normal(size=(2, 3, 3))*.01
    direction = rng.normal(size=6); displacement = np.einsum('fsip,p->fsi', derivative, direction)*1e-6
    for order in [1, 2]:
        vectors, jac = temporal_pair(points, derivative, order, 30.)
        caps = np.full(vectors.shape[:2], 30.)
        values, rows = norm_envelope_pair(vectors, jac, caps, 1.)
        minus = np.diff(points-displacement, n=order, axis=0)*30**order
        plus = np.diff(points+displacement, n=order, axis=0)*30**order
        expected = ((caps**2-np.sum(plus**2, axis=2))-(caps**2-np.sum(minus**2, axis=2)))/(caps**2*2e-6)
        np.testing.assert_allclose(rows@direction, expected.ravel(), atol=1e-8)
        assert np.any(rows[:, :3]) and np.any(rows[:, 3:])


def test_adjacent_block_derivative_has_both_sides_and_fixed_boundary():
    rng = np.random.default_rng(822)
    values = rng.normal(size=(6, 9))*.01; frames = [2, 3]; free = np.array([6, 7, 8])
    v, j = adjacent_pair(values, frames, free, .1, .2)
    direction = rng.normal(size=6); minus, plus = values.copy(), values.copy()
    minus[np.ix_(frames, free)] -= direction.reshape(2, 3)*1e-6
    plus[np.ix_(frames, free)] += direction.reshape(2, 3)*1e-6
    expected = (adjacent_pair(plus, frames, free, .1, .2)[0]-adjacent_pair(minus, frames, free, .1, .2)[0])/2e-6
    np.testing.assert_allclose(j@direction, expected, atol=1e-9)
    assert len(v) == 9  # Three edges times root/two joints, not four duplicate edges.


def test_coupled_solver_reduces_known_spike_and_preserves_fixed_parameters():
    fitter = ToyFitter(); initial = np.zeros((7, 9)); initial[3, 6] = .1
    evaluator = SerializedPose(fitter.rig, {0, 1}, 0, len(initial))
    centers = np.array([fitter.rig.vertices(evaluator.pose(fitter.pose(f, x)[0])) for f, x in enumerate(initial)])
    caps = np.maximum(.001, np.linalg.norm(np.diff(centers, n=2, axis=0), axis=2))
    envelope = dict(active_frames=np.zeros((7, 2), bool), support_steps=np.zeros((6, 2), bool),
        support_speed_caps_m_s=np.zeros((6, 2)), hover_caps_m=np.full((7, 2), .01), rotation_cap_radians=0.)
    target = dict(centers=[2, 3, 4], side_index=0, limit_m_s2=0.)
    problem = BlockProblem(fitter, initial, evaluator, [2, 3, 4], [6, 7, 8], envelope, caps, target)
    result, proof = solve(problem, maxiter=80)
    assert proof['accepted_fraction'] is not None
    assert proof['objective_after'] < proof['objective_before']
    np.testing.assert_array_equal(result[:, :6], initial[:, :6])
    np.testing.assert_array_equal(result[[0, 1, 5, 6]], initial[[0, 1, 5, 6]])
    checked = problem.evaluate(result[np.ix_([2, 3, 4], [6, 7, 8])].ravel())
    assert checked[2].min() >= -1e-8
    assert problem.geometric_guard(result)
