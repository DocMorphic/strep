import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from root_height_feasibility import RootHeightProblem, interpolation_matrix, solve
from export_motion_sampling import joint_trajectory


def fixture():
    frames = 7
    r = np.tile(np.eye(3), (frames, 1, 1, 1))
    p = np.zeros((frames, 1, 3)); p[:, 0, 0] = np.arange(frames)**2*.001
    p[:, 0, 1] = -.012+np.arange(frames)*.001
    source = dict(root_positions=p[:, 0].copy(), posed_joints=p, global_rot_mats=r, local_rot_mats=r.copy())
    seed = {k: v.copy() for k, v in source.items()}
    change = .002+np.arange(frames)**2*.00001
    seed['root_positions'][:, 1] += change; seed['posed_joints'][:, 0, 1] += change
    skin = dict(rig_joint_names=['LeftFoot'], lbs_indices=np.zeros((2, 8), dtype=int),
        lbs_weights=np.tile(np.arange(1, 9)/36, (2, 1)), bind_vertices=np.array([[1., .01, 0.], [0., .03, 0.]]),
        bind_rig_transform=np.eye(4)[None])
    spec = dict(schema_version=1, fps=30, frame_count=frames, regions={'LeftFoot': dict(mode='explicit', segments=[
        dict(start_frame=2, end_frame=4, vertex_id=0, space='world', position_m=[1.012, .001, 0.])])})
    with patch('export_point_position_objective.regions', return_value={'LeftFoot': np.array([0])}), \
         patch('export_point_rate_objective.regions', return_value={'LeftFoot': np.array([0])}):
        problem = RootHeightProblem(source, seed, [-1], skin, spec, [1, 5], .12)
    return problem


def test_cache_matches_full_export_objectives_at_seed_and_perturbed_roots():
    problem = fixture()
    for delta in [np.zeros(3), np.array([1e-5, -2e-5, 3e-5])]:
        x = problem.start+delta
        c, _, groups = problem.evaluate(x)
        motion = problem.motion(x)
        np.testing.assert_allclose(c, problem.reference_residuals(motion), atol=1e-8, rtol=1e-9)
        r = torch.tensor(motion['global_rot_mats'], dtype=torch.float64)
        p = torch.tensor(motion['posed_joints'], dtype=torch.float64)
        for obj in [problem.position, problem.point_rate, problem.floor, problem.global_rate]: obj.loss(r, p)
        assert groups['pin:0']['minimum_slack'] == pytest.approx(float(-problem.position.last[0].max()), abs=1e-9)
        for i, rows in enumerate(problem.point_rate.last):
            for order, values in enumerate(rows, 1):
                assert groups[f'point_rate:{i}:{order}']['minimum_slack'] == pytest.approx(float(-values.max()), abs=1e-8)
        assert groups['floor']['minimum_slack'] == pytest.approx(float(-problem.floor.last.max()), abs=1e-9)
        for order, values in enumerate(problem.global_rate.last, 1):
            assert groups[f'global_rate:{order}']['minimum_slack'] == pytest.approx(float(-values.max()), abs=1e-8)
        assert np.isfinite(c).all()


def test_every_residual_derivative_matches_central_difference():
    problem = fixture(); x = problem.start+np.array([2e-5, -1e-5, 1e-5])
    _, j, _ = problem.evaluate(x)
    for index in range(len(x)):
        direction = np.eye(len(x))[index]*1e-8
        finite = (problem.evaluate(x+direction, False)[0]-problem.evaluate(x-direction, False)[0])/(2e-8)
        np.testing.assert_allclose(j[:, index], finite, atol=2e-5, rtol=2e-5)


def test_held_boundaries_rotation_and_original_budget_reference_are_preserved():
    problem = fixture(); assert problem.free.tolist()==[2, 3, 4]
    motion = problem.motion(problem.start+1e-5)
    locked = [0, 1, 5, 6]
    assert np.array_equal(motion['root_positions'][locked], problem.seed['root_positions'][locked])
    assert np.array_equal(motion['local_rot_mats'], problem.seed['local_rot_mats'])
    assert np.array_equal(motion['root_positions'][:, [0, 2]], problem.seed['root_positions'][:, [0, 2]])
    expected = problem.seed['root_positions'][problem.free, 1]-problem.source['root_positions'][problem.free, 1]-.06
    np.testing.assert_array_equal(problem.start, expected)


def test_float32_export_clock_is_matched_including_fractional_key_drift():
    frames = 180; free = np.arange(frames)
    r = torch.eye(3, dtype=torch.float64).repeat(frames, 1, 1, 1)
    p = torch.zeros(frames, 1, 3, dtype=torch.float64)
    p[:, 0, 1] = torch.sin(torch.arange(frames, dtype=torch.float64)*.3)
    actual = joint_trajectory(r, p, [-1]).numpy()[:, 0, 1]
    np.testing.assert_allclose(interpolation_matrix(frames, free)@p.numpy()[:, 0, 1], actual, atol=2e-15)


def test_linear_repair_obeys_box_and_does_not_move_a_passed_constraint():
    class Problem:
        start=np.array([0.]); bounds=np.array([.01]); free=np.array([1])
        def evaluate(self, x, jacobian=True):
            c=np.array([x[0]-.001, .002-x[0]])
            return c, np.array([[1.], [-1.]]) if jacobian else None, {}
        def motion(self, x): return x
    motion, result=solve(Problem(), trust=.002, margin=.0001)
    assert result['sampled_feasible'] and .001<=motion[0]<=.002
    assert result['maximum_root_change_m']<=.002


def test_infeasible_box_keeps_seed_and_records_failed_proposal():
    class Problem:
        start=np.array([0.]); bounds=np.array([.0001]); free=np.array([1])
        def evaluate(self, x, jacobian=True):
            return np.array([x[0]-.001]), np.array([[1.]]) if jacobian else None, {}
        def motion(self, x): return x
    motion, result=solve(Problem(), trust=.002)
    assert not result['sampled_feasible'] and motion[0]==0
    assert result['history'][0]['success'] is False


def test_nonlinear_new_violation_is_rejected_even_when_linear_model_passes():
    class Problem:
        start=np.array([0.]); bounds=np.array([.01]); free=np.array([1])
        def evaluate(self, x, jacobian=True):
            return np.array([x[0]-.001, 1e-8-x[0]**2]), np.array([[1.], [-2*x[0]]]) if jacobian else None, {}
        def motion(self, x): return x
    motion, result=solve(Problem(), attempts=1, trust=.002, margin=.0001)
    trials=result['history'][0]['trials']
    assert trials[0]['passing_rows_preserved'] is False and trials[0]['accepted'] is False
    assert abs(motion[0])<=.0001 and not result['sampled_feasible']
