import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rate_peak_guard import RatePeakGuard


def arrays(a): return [np.array(a, float) for _ in range(4)]


def test_rejects_a_joint_regression_despite_lower_global_peak_and_score():
    caps = arrays([[1, 1], [1, 1]])
    guard = RatePeakGuard(arrays([[5, 2], [2, 2]]), caps, cap_tolerance=0)
    candidate = arrays([[4, 2.1], [2, 2]])
    assert any(guard.margins(candidate) < 0)
    report = guard.report(candidate)
    assert not report['per_joint_peak_guard_pass'] and not report['quality_approved']
    assert all(r['regressing_joints'] == 1 for r in report['rates'])


def test_passing_joint_keeps_original_caps_without_rebasing_to_lower_source():
    guard = RatePeakGuard(arrays([[.5, 2], [.5, 2]]), arrays([[1, 1], [1, 1]]), cap_tolerance=0)
    assert np.all(guard.margins(arrays([[.9, 1.9], [.8, 1.8]])) >= 0)
    assert np.any(guard.margins(arrays([[1.1, 1.9], [.8, 1.8]])) < 0)


def test_reserve_tightens_proposal_only_and_does_not_overrun_small_deficits():
    source = arrays([[1.000001, 2]])
    guard = RatePeakGuard(source, arrays([[1, 1]]), cap_tolerance=0, guard_tolerance=0)
    assert np.all(guard.margins(source) == 0)
    assert np.all(guard.margins(source, proposal=True) < 0)
    for allowed, reserve in zip(guard.allowed, guard.reserve):
        assert np.all(reserve <= .1*allowed) and np.all(reserve >= 0)


def test_peak_guard_pass_does_not_claim_original_cap_pass():
    guard = RatePeakGuard(arrays([[3, 1]]), arrays([[1, 1]]), cap_tolerance=0)
    report = guard.report(arrays([[2, .9]]))
    assert report['per_joint_peak_guard_pass'] and not report['original_motion_caps_pass']
    assert guard.report(arrays([[.9, .9]]))['original_motion_caps_pass']


def test_rejects_invalid_rate_shapes_and_nonfinite_values():
    with pytest.raises(ValueError): RatePeakGuard(arrays([[1]]), arrays([[-1]]))
    guard = RatePeakGuard(arrays([[2]]), arrays([[1]]))
    with pytest.raises(ValueError): guard.margins(arrays([[float('nan')]]))
    with pytest.raises(ValueError): guard.margins(arrays([[1, 2]]))
