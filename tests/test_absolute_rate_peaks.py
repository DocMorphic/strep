import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from absolute_rate_peaks import compare
from rate_peak_guard import RatePeakGuard


def arrays(x): return [np.asarray(x, float) for _ in range(4)]


def test_changing_caps_can_hide_absolute_peak_growth():
    source, candidate, caps = arrays([[10], [6]]), arrays([[11], [5]]), arrays([[8], [1]])
    assert RatePeakGuard(source, caps, cap_tolerance=0).report(candidate)['per_joint_peak_guard_pass']
    result = compare(source, candidate)
    assert not result['absolute_peak_guard_pass']
    assert all(r['maximum_increase'] == 1 for r in result['rates'])


def test_each_joint_is_checked_even_when_the_global_maximum_falls():
    result = compare(arrays([[10, 2], [9, 3]]), arrays([[9, 3], [8, 4]]))
    assert all(r['regressing_joints'] == 1 and r['worst_column'] == 1 for r in result['rates'])
    assert compare(arrays([[10, 2]]), arrays([[9, 2]]))['absolute_peak_guard_pass']


def test_invalid_or_changed_population_is_rejected():
    with pytest.raises(ValueError): compare(arrays([[1]]), arrays([[1, 2]]))
    with pytest.raises(ValueError): compare(arrays([[1]]), arrays([[float('nan')]]))
