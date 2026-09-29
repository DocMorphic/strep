"""Original-source budgets cannot drift through successive feedback repairs."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_export_repair import verify_original_bounds


def poses():
    source = dict(root_positions=np.zeros((3, 3), np.float32),
                  posed_joints=np.zeros((3, 2, 3), np.float32),
                  local_rot_mats=np.tile(np.eye(3, dtype=np.float32), (3, 2, 1, 1)),
                  global_rot_mats=np.tile(np.eye(3, dtype=np.float32), (3, 2, 1, 1)))
    return source, {k: v.copy() for k, v in source.items()}, np.array([True, False, True])


def test_valid_free_root_and_rotation_change():
    source, trial, held = poses()
    trial['root_positions'][1, 1] = .1
    trial['local_rot_mats'][1, 0] = Rotation.from_euler('x', 20, degrees=True).as_matrix()
    result = verify_original_bounds(source, trial, .22, 40, held)
    assert .099 < result['maximum_root_lift_m'] < .101
    assert 19.99 < result['maximum_rotation_delta_degrees'] < 20.01


@pytest.mark.parametrize('height', [-1e-10, .220001, float('nan')])
def test_original_root_limit_has_no_new_acceptance_slack(height):
    source, trial, held = poses()
    trial['root_positions'][1, 1] = height
    with pytest.raises(ValueError, match='Original root'):
        verify_original_bounds(source, trial, .22, 40, held)


def test_rotation_limit_is_relative_to_original():
    source, trial, held = poses()
    trial['local_rot_mats'][1, 0] = Rotation.from_euler('x', 41, degrees=True).as_matrix()
    with pytest.raises(ValueError, match='Original rotation'):
        verify_original_bounds(source, trial, .22, 40, held)


def test_horizontal_root_change_rejected():
    source, trial, held = poses()
    trial['root_positions'][1, 0] = 1e-9
    with pytest.raises(ValueError, match='Root XZ'):
        verify_original_bounds(source, trial, .22, 40, held)


@pytest.mark.parametrize('key', ['root_positions', 'posed_joints', 'local_rot_mats', 'global_rot_mats'])
def test_held_native_pose_is_byte_exact(key):
    source, trial, held = poses()
    # Flip a zero's sign: numerically equal must still preserve native bytes.
    trial[key][0].reshape(-1)[1] = -0.
    with pytest.raises(ValueError, match='Held source pose'):
        verify_original_bounds(source, trial, .22, 40, held)


@pytest.mark.parametrize('budget', [0, -1, True, float('inf'), float('nan')])
def test_invalid_original_budget_rejected(budget):
    source, trial, held = poses()
    with pytest.raises(ValueError):
        verify_original_bounds(source, trial, budget, 40, held)
