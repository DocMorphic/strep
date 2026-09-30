import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_clearance_policy import protected_caps, compare_depths


def test_newly_cleared_time_is_protected_without_rebasing_original_failed_caps():
    np.testing.assert_array_equal(protected_caps([.008, .020, .002], [.004, .017, .003]), [.005, .020, .005])


def test_lower_peak_does_not_hide_lost_clearance():
    result = compare_depths([.004, .020], [.0051, .019], [.005, .020])
    assert result['improvement_m'] > 0
    assert result['lost_clearances_strict'] == result['lost_clearances_over_1e_6'] == 1
    assert result['cap_failures_over_1e_6'] == 1


def test_identical_motion_cannot_improve_by_rebinding():
    assert compare_depths([.004, .020], [.004, .020], [.005, .023])['improvement_m'] == 0


def test_strict_and_numerical_clearance_counts_are_distinct():
    result = compare_depths([.004], [.0050005], [.005])
    assert result['lost_clearances_strict'] == 1
    assert result['lost_clearances_over_1e_6'] == result['cap_failures_over_1e_6'] == 0


@pytest.mark.parametrize('original,start', [([.01], [.012]), ([float('nan')], [.0]), ([-.01], [.0]), ([], []), ([.01], [.01, .02])])
def test_invalid_or_regressed_start_is_rejected(original, start):
    with pytest.raises(ValueError):
        protected_caps(original, start)


def test_nonfinite_candidate_is_rejected():
    with pytest.raises(ValueError):
        compare_depths([.004], [float('nan')], [.005])
