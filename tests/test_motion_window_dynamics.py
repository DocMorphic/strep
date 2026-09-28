import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from motion_window_dynamics import measure


def motion():
    root = np.zeros((60, 3))
    root[:, 0] = np.arange(60) / 30
    return dict(root_positions=root, posed_joints=root[:, None, :].copy(),
                local_rot_mats=np.tile(np.eye(3), (60, 1, 1, 1)))


def test_constant_translation_has_speed_without_acceleration():
    result = measure(motion())['measures']
    assert result['root_speed_m_s']['ending_peak'] == pytest.approx(1.)
    assert result['joint_rms_speed_m_s']['ending_peak'] == pytest.approx(1.)
    assert result['root_acceleration_m_s2']['ending_peak'] < 1e-10
    assert result['local_rotation_step_degrees']['ending_peak'] == 0


def test_final_pose_snap_reports_correct_time_and_angle():
    data = motion()
    data['local_rot_mats'][-1, 0] = Rotation.from_euler('x', 90, degrees=True).as_matrix()
    result = measure(data)['measures']['local_rotation_step_degrees']
    assert result['ending_peak'] == pytest.approx(90.)
    assert result['ending_peak_arrival_frame'] == 59


def test_nonfinite_motion_is_not_reported_as_small_error():
    data = motion()
    data['root_positions'][-1, 1] = np.nan
    with pytest.raises(ValueError):
        measure(data)
