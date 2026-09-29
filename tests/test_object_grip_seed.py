import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from object_grip_seed import transport_frames, fit_frames
from floor_contact import reconstruct


def test_grip_transport_retains_object_relative_position_and_orientation():
    p = np.array([[1., 2., 3.], [3., 1., 2.], [-2., 0., 4.]])
    r = Rotation.from_euler('y', [30, 80, -100], degrees=True).as_matrix()
    gp = np.array([[1.1, 2.3, 3.4], [.8, 2., 3.]])
    gr = Rotation.from_euler('xyz', [[10, 20, 30], [-5, 80, 20]], degrees=True).as_matrix()
    tp, tr = transport_frames(p, r, 0, gp, gr)
    for f in range(3):
        np.testing.assert_allclose((tp[f]-p[f])@r[f], (gp-p[0])@r[0], atol=1e-14)
        np.testing.assert_allclose(r[f].T@tr[f], r[0].T@gr, atol=1e-14)


def test_bounded_ik_follows_moving_target_with_fixed_root_and_offsets():
    frames = 5
    source = dict(root_positions=np.zeros((frames, 3)),
        local_rot_mats=np.tile(np.eye(3), (frames, 3, 1, 1)),
        global_rot_mats=np.tile(np.eye(3), (frames, 3, 1, 1)),
        posed_joints=np.tile([[0., 0., 0.], [1., 0., 0.], [2., 0., 0.]], (frames, 1, 1)))
    parents = [-1, 0, 1]
    local = source['local_rot_mats'].copy()
    local[:, 1] = Rotation.from_euler('z', np.linspace(.05, .2, frames)).as_matrix()
    target = reconstruct(source, local, parents)
    result, record = fit_frames(source, source, parents, [1], [.4], 1, np.eye(frames),
        [2], target['posed_joints'][:, [2]], target['global_rot_mats'][:, [2]], np.ones(frames), 60)
    assert record['maximum_active_joint_position_error_m'] < 1e-4
    np.testing.assert_array_equal(result['root_positions'], source['root_positions'])
    np.testing.assert_allclose(np.linalg.norm(result['posed_joints'][:, 2]-result['posed_joints'][:, 1], axis=-1), 1., atol=1e-6)
    assert record['reconstruction']['original_edit_budgets_preserved']
    assert not record['quality_approved']


def test_impossible_target_does_not_expand_original_budget_or_claim_success():
    frames = 3
    source = dict(root_positions=np.zeros((frames, 3)),
        local_rot_mats=np.tile(np.eye(3), (frames, 2, 1, 1)),
        global_rot_mats=np.tile(np.eye(3), (frames, 2, 1, 1)),
        posed_joints=np.tile([[0., 0., 0.], [1., 0., 0.]], (frames, 1, 1)))
    target_p = np.tile([[[0., 3., 0.]]], (frames, 1, 1))
    target_r = np.tile(np.eye(3), (frames, 1, 1, 1))
    result, record = fit_frames(source, source, [-1, 0], [0], [.1], 1,
        np.eye(frames), [1], target_p, target_r, np.ones(frames), 10)
    angles = Rotation.from_matrix(result['local_rot_mats'][:, 0]).magnitude()
    assert np.all(angles < .1)
    assert record['maximum_active_joint_position_error_m'] > 2
    assert not record['quality_approved']
    with pytest.raises(ValueError, match='weights'):
        fit_frames(source, source, [-1, 0], [0], [.1], 1,
            np.eye(frames), [1], target_p, target_r, np.zeros(frames))
