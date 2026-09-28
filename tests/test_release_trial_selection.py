from pathlib import Path
import sys
import copy
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from release_trial_selection import peak_joint, derivative_frames


def test_peak_selection_uses_actual_node_and_preserves_only_editable_peaks():
    local = np.tile(np.eye(4), (4, 5, 1, 1))
    local[2:, 3, :3, :3] = Rotation.from_euler('x', 60, degrees=True).as_matrix()
    local[1:, 1, :3, :3] = Rotation.from_euler('z', 10, degrees=True).as_matrix()
    selected = peak_joint(local, [1, 3])
    assert selected['node'] == 3 and selected['step_end_frame'] == 2
    assert selected['protected_nodes'] == [3]
    np.testing.assert_allclose(selected['degrees'], 60.)
    assert peak_joint(local, [1])['protected_nodes'] == []


def test_derivative_samples_follow_long_clip_clock_and_late_release():
    count = 210; acceleration = np.zeros((count-2, 3)); acceleration[-1, 0] = 3.
    event = dict(release_frame=209, acceleration_frames=[207, 208], acceleration_max_m_s2=3.)
    track = dict(acceleration_m_s2=acceleration.tolist(), releases=[event])
    dynamics = {v: dict(feet=dict(Right=copy.deepcopy(track))) for v in ['input', 'prior', 'candidate']}
    dynamics['input']['feet']['Right']['releases'][0]['acceleration_max_m_s2'] = 1.
    dynamics['prior']['feet']['Right']['releases'][0]['acceleration_max_m_s2'] = 2.
    selection = derivative_frames(dynamics, count)
    assert selection['frames'] == [0, 105, 208, 209]
    assert selection['selected_peak_center'] == 208
    assert selection['selected_release_frame'] == 209


def test_no_releases_still_tests_endpoints_and_midpoint():
    data = {v: dict(feet=dict(Left=dict(releases=[]))) for v in ['input', 'prior', 'candidate']}
    result = derivative_frames(data, 7)
    assert result['frames'] == [0, 3, 4, 6]
    assert result['selected_release_side'] is None
