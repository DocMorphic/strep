import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from sample_rate_peak_guard import SampleRatePeakGuard


def arrays(x): return [np.asarray(x, float) for _ in range(4)]


@pytest.mark.parametrize('proposal', [False, True])
def test_sample_rows_are_equivalent_to_peak_guard_for_all_columns(proposal):
    rng = np.random.default_rng(27); source = [rng.uniform(0, 3, (7, 3)) for _ in range(4)]
    caps = [rng.uniform(.1, 2, (7, 3)) for _ in range(4)]; values = [rng.uniform(0, 3, (7, 3)) for _ in range(4)]
    guard = SampleRatePeakGuard(source, caps, [0, 1, 2])
    rows = guard.sample_margins(values, proposal=proposal).reshape(4, 7, 3)
    np.testing.assert_allclose(rows.min(axis=1).ravel(), guard.margins(values, proposal=proposal), rtol=0, atol=1e-14)


def test_both_sides_of_switching_worst_time_remain_visible():
    guard = SampleRatePeakGuard(arrays([[2], [2]]), arrays([[1], [1]]), [0], cap_tolerance=0, guard_tolerance=0)
    def constraints(x): return guard.sample_margins(arrays([[2+x], [2-x]]))
    derivative = (constraints(1e-4)-constraints(-1e-4))/(2e-4)
    np.testing.assert_allclose(derivative[:2], [-1, 1], atol=1e-11)
    assert constraints(1e-4).min() < 0 and constraints(-1e-4).min() < 0


def test_omitted_joints_still_have_full_acceptance_guards():
    guard = SampleRatePeakGuard(arrays([[2, 2]]), arrays([[1, 1]]), [1])
    candidate = arrays([[3, 1.5]])
    assert guard.sample_margins(candidate).min() > 0
    assert not guard.report(candidate)['per_joint_peak_guard_pass']
    with pytest.raises(ValueError): SampleRatePeakGuard(arrays([[2, 2]]), arrays([[1, 1]]), [1, 1])
