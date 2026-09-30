import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from hand_witness_envelope import limits, guarded
from hand_norm_proposal import measurement, linearize, backtrack


def motion(x):
    # A maximum-only objective prefers x=1, although a previously safe contact
    # crosses 5 mm. The envelope must reject that exact proposal.
    return dict(vectors=np.zeros((1, 3)), caps=np.ones(1), scales=np.ones(1),
                margins=np.ones(1), depths=np.array([.02-.005*x[0], .004+.004*x[0]]))


def test_exact_backoff_prevents_worsening_safe_contact_despite_peak_improvement():
    evaluate = guarded(motion, limits(motion([0.])['depths']))
    assert measurement(motion([1.]))['witness_peak_m'] < measurement(motion([0.]))['witness_peak_m']
    assert measurement(evaluate([1.]))['minimum_margin'] < 0
    candidate, attempts = backtrack(evaluate, np.zeros(1), np.ones(1), evaluate([0.]))
    np.testing.assert_array_equal(candidate, [.25])
    assert not attempts[0]['accepted'] and not attempts[1]['accepted'] and attempts[2]['accepted']


def test_bound_is_original_not_rebased_after_successful_step():
    bounds = limits(motion([0.])['depths']); evaluate = guarded(motion, bounds)
    bounds[:] = 100.  # External caller cannot relax the copied envelope.
    assert measurement(evaluate([.25]))['minimum_margin'] >= 0
    assert measurement(evaluate([.5]))['minimum_margin'] < 0
    again = linearize(evaluate, evaluate, [.25])
    np.testing.assert_allclose(again['jacobian']['margins'][-1], [-.2], atol=1e-12)
    assert again['base']['margins'][-1] < 1e-6


def test_penetrating_contact_preserves_own_depth_and_clear_contact_gets_tolerance():
    np.testing.assert_allclose(limits([-.1, .004, .02]), [.00500001, .00500001, .02000001], atol=1e-15)
    payload = motion([0.]); old = payload['margins'].copy()
    evaluate = guarded(lambda x: payload, limits(payload['depths']))
    assert len(evaluate([0.])['margins']) == 3
    np.testing.assert_array_equal(payload['margins'], old)


@pytest.mark.parametrize('depths', [[], [[.01]], [np.nan], [np.inf]])
def test_invalid_reference_rejected(depths):
    with pytest.raises(ValueError): limits(depths)


def test_changed_population_rejected():
    evaluate = guarded(motion, [.02])
    with pytest.raises(ValueError, match='population'): evaluate([0.])
