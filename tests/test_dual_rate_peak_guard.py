import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from dual_rate_peak_guard import DualRatePeakGuard
from sample_rate_peak_guard import SampleRatePeakGuard


def arrays(x): return [np.asarray(x, float) for _ in range(4)]


def test_rejects_absolute_growth_hidden_by_changing_caps():
    source, caps, candidate = arrays([[10], [6]]), arrays([[8], [1]]), arrays([[11], [5]])
    guard = DualRatePeakGuard(source, caps, [0], cap_tolerance=0)
    report = guard.report(candidate)
    assert report['per_joint_peak_guard_pass']
    assert not report['absolute_peak_guard']['absolute_peak_guard_pass']
    assert not report['dual_peak_guard_pass']
    assert guard.margins(candidate).min() < 0
    assert guard.sample_margins(candidate).min() < 0


@pytest.mark.parametrize('proposal', [False, True])
def test_combined_envelope_equals_both_separate_constraints(proposal):
    rng = np.random.default_rng(73)
    source = [rng.uniform(0, 5, (8, 3)) for _ in range(4)]
    caps = [rng.uniform(.1, 3, (8, 3)) for _ in range(4)]
    values = [rng.uniform(0, 5, (8, 3)) for _ in range(4)]
    guard = DualRatePeakGuard(source, caps, [0, 1, 2])
    relative = SampleRatePeakGuard(source, caps, [0, 1, 2])
    relative_rows = relative.sample_margins(values, proposal=proposal)
    absolute_rows = np.concatenate([((p-(r if proposal else 0)-v+guard.guard_tolerance)/s).ravel()
        for p, r, v, s in zip(guard.absolute, guard.absolute_reserve, values, guard.scales)])
    actual = guard.sample_margins(values, proposal=proposal)
    np.testing.assert_allclose(actual, np.minimum(relative_rows, absolute_rows), atol=1e-14, rtol=0)
    np.testing.assert_allclose(actual.reshape(4, 8, 3).min(axis=1).ravel(), guard.margins(values, proposal=proposal), atol=1e-14, rtol=0)


def test_source_is_actual_feasible_but_reserve_tightens_proposal():
    source = arrays([[3, 0], [2, 0]])
    guard = DualRatePeakGuard(source, arrays([[1, 1], [1, 1]]), [0, 1], guard_tolerance=0)
    assert guard.margins(source).min() == 0
    assert guard.report(source)['dual_peak_guard_pass']
    assert not guard.report(source)['original_motion_caps_pass']
    assert guard.sample_margins(source, proposal=True).min() < 0
    assert all(r[1] == 0 for r in guard.absolute_reserve)
    source[0][0, 0] = 100
    assert guard.absolute[0][0] == 3 and guard.source[0][0, 0] == 3


def test_full_acceptance_catches_omitted_joint_regression_and_invalid_values():
    guard = DualRatePeakGuard(arrays([[10, 2], [6, 1]]), arrays([[8, 1], [1, 1]]), [1], cap_tolerance=0)
    candidate = arrays([[11, 1.9], [5, 1]])
    assert guard.sample_margins(candidate).min() > 0
    assert not guard.report(candidate)['dual_peak_guard_pass']
    assert guard.margins(candidate).min() < 0
    with pytest.raises(ValueError): guard.sample_margins(arrays([[np.nan, 1], [1, 1]]))
