import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rotation_rate_support import rate_support, SupportedDualRatePeakGuard
from sampled_motion_caps import features, measures
from test_contact_rate_path import model


def test_rotation_cannot_move_own_origin_and_frozen_times_have_no_support():
    entries = [dict(node=1, clock=np.arange(5.), ids=np.array([2]))]
    masks = rate_support([-1, 0, 1, 2, 0], [0, 1, 2, 3, 4], entries, np.arange(0, 4.01, .5))
    for mask in masks[:2]:
        assert not mask[:, [0, 1, 4]].any()
        assert mask[:, [2, 3]].any()
    assert masks[2][:, 1].any()
    assert not masks[2][[0, -1]].any()
    assert not masks[2][:, [0, 4]].any()
    assert masks[3][1, 1]  # A three-pose stencil crosses into editable support.


@pytest.mark.parametrize('quantize', [False, True])
def test_mask_never_omits_changed_rates_on_native_noncommuting_motion(quantize):
    m = model(); times = np.linspace(0, 3, 121)
    ids = np.searchsorted(m.model.times, times); joints = list(range(len(m.model.parents)))
    masks = rate_support(m.model.parents, joints, m.model.entries, times)
    source = measures(features(m.world(np.zeros(m.size), True)[ids], joints), times[1]-times[0])
    for seed in [13, 37]:
        x = np.random.default_rng(seed).uniform(-.08, .08, m.size)
        values = measures(features(m.world(x, quantize)[ids], joints), times[1]-times[0])
        for before, after, mask in zip(source, values, masks):
            np.testing.assert_allclose(before[~mask], after[~mask], atol=1e-10, rtol=0)


def test_only_proposal_omits_frozen_rows_actual_guard_still_checks_everything():
    source = [np.array([[3., 2.], [1., 1.]]) for _ in range(4)]
    caps = [np.full((2,2), 10.) for _ in range(4)]
    support = [np.array([[False, True], [False, True]]) for _ in range(4)]
    guard = SupportedDualRatePeakGuard(source, caps, [0, 1], support)
    candidate = [np.array([[4., 1.9], [1., .9]]) for _ in range(4)]
    assert guard.sample_margins(candidate, proposal=True).min() > 0
    assert guard.margins(candidate).min() < 0
    assert not guard.report(candidate)['dual_peak_guard_pass']
    assert len(guard.sample_margins(candidate)) == 8


def test_invalid_support_or_hierarchy_is_rejected():
    with pytest.raises(ValueError): rate_support([1, 0], [0], [], [0,1,2])
    source = [np.ones((2, 2)) for _ in range(4)]
    with pytest.raises(ValueError): SupportedDualRatePeakGuard(source, source, [1], [np.ones((2,2),bool)]*4)
    with pytest.raises(ValueError): SupportedDualRatePeakGuard(source, source, [0,1], [np.zeros((2,2),bool)]*4)
