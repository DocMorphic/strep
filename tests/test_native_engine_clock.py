import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_engine_clock import audit_clock, compare_poses, clock_echo_matches


def test_clock_echo_allows_only_two_double_steps_not_event_quantization():
    event = 2.0917225950783
    second = np.nextafter(np.nextafter(event, np.inf), np.inf)
    assert clock_echo_matches(event, event) and clock_echo_matches(event, second)
    assert not clock_echo_matches(event, np.nextafter(second, np.inf))
    assert not clock_echo_matches(event, float(np.float32(event)))
    assert not clock_echo_matches(event, np.nan)


def test_native_keys_and_fractional_event_stay_distinct_over_full_clip():
    key = float(np.float32(2.0917225950783)); event = 2.0917225950783
    times = audit_clock(3.6666667461395264, [[0, key, 3.6666667461395264]], [1.4083333333333334], event)
    assert key in times and event in times and key != event
    assert 3.0 in times and times[0] == 0 and times[-1] == 3.6666667461395264
    assert (key+3.6666667461395264)/2 in times
    assert np.all(np.diff(times) > 0)


@pytest.mark.parametrize('keys,declared,event', [([0, 0], [], .5), ([0, np.nan], [], .5), ([0, 2], [], .5), ([0, 1], [-.01], .5), ([0, 1], [], 1.01)])
def test_invalid_clock_rejected(keys, declared, event):
    with pytest.raises(ValueError): audit_clock(1, [keys], declared, event)


def test_matrix_column_layout_detects_position_and_basis_errors():
    expected = np.tile(np.eye(4), (2, 1, 1))
    found = np.zeros((2, 4, 3)); found[:, :3] = np.eye(3)
    assert compare_poses(expected, found) == dict(position_error_m=0., basis_element_error=0.)
    found[1, 3, 2] = .03; found[0, 1, 0] = .02
    assert compare_poses(expected, found) == dict(position_error_m=.03, basis_element_error=.02)
    found[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match='Non-finite'): compare_poses(expected, found)
