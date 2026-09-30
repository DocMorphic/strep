import sys
from pathlib import Path
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scalar_angular_replay import angular_replay, compare_saved
from joint_angular_rates import compare_angular_rates


def test_analytical_stationary_joint_pulse_counts_two_speed_three_acceleration_failures():
    times = np.arange(25)/120; source = np.tile(np.eye(3), (25, 2, 1, 1)); candidate = source.copy()
    candidate[12, 1] = Rotation.from_rotvec([0., 0., .001]).as_matrix()
    result = angular_replay(source, candidate, times, [0., .1, .2])
    assert result['angular_speed_rad_s']['exceeding_observations'] == 2
    assert result['angular_acceleration_rad_s2']['exceeding_observations'] == 3
    assert result['angular_speed_rad_s']['maximum_increase'] == pytest.approx(.12)
    assert result['angular_acceleration_rad_s2']['maximum_increase'] == pytest.approx(28.8)
    assert sum(v['observations'] for v in result.values()) == 94


def test_changing_axes_replay_matches_matrix_policy_and_rejects_tampered_counts():
    times = np.arange(61)/120; knots = [0., .2, .35, .5]
    angles = np.column_stack([np.sin(times*4), times**2, .3*times])
    source = Rotation.from_euler('xyz', angles).as_matrix()[:,None]
    edited = angles.copy(); edited[30:34, 1] += .0001
    candidate = Rotation.from_euler('xyz', edited).as_matrix()[:,None]
    replay = angular_replay(source, candidate, times, knots)
    saved = compare_angular_rates(source, candidate, times, knots, ['joint'], speed_tolerance=1e-5, acceleration_tolerance=1e-5)
    compare_saved(replay, saved)
    changed = copy.deepcopy(saved); changed['angular_speed_rad_s']['exceeding_observations'] += 1
    with pytest.raises(ValueError, match='disagrees'): compare_saved(replay, changed)


@pytest.mark.parametrize('fault', ['reflection', 'irregular_clock', 'nan', 'pi_step'])
def test_ambiguous_or_invalid_replay_rejected(fault):
    times = np.arange(7)/120; source = np.tile(np.eye(3), (7,1,1,1)); candidate = source.copy()
    if fault == 'reflection': candidate[3,0,0,0] = -1
    if fault == 'irregular_clock': times[3] += .001
    if fault == 'nan': candidate[3,0,0,0] = np.nan
    if fault == 'pi_step': candidate[3,0] = Rotation.from_rotvec([np.pi,0,0]).as_matrix()
    with pytest.raises(ValueError): angular_replay(source, candidate, times, [0., .025, .05])
