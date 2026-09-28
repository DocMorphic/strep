import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inspect_kneel_phases import summarize_trace


def trace(phases):
    # S: standing, K: both knees near ground, C: deeply flexed standing crouch.
    values = {'S': (1., .5, 10.), 'K': (.5, .02, 120.), 'C': (.5, .3, 120.)}
    p, k, f = np.array([values[c] for c in phases]).T
    return summarize_trace(p, np.stack([k, k], axis=1), np.stack([f, f], axis=1), 30.)


def test_complete_order_and_missing_lowering_are_distinct():
    assert trace('S' * 12 + 'K' * 20 + 'S' * 12)['upright_kneel_upright_proxy_present']
    missing = trace('K' * 32 + 'S' * 12)
    assert not missing['sustained_upright_start']
    assert not missing['upright_kneel_upright_proxy_present']
    assert missing['action_correctness'] is None


def test_start_guide_alone_does_not_establish_order():
    assert not trace('S' * 44)['upright_kneel_upright_proxy_present']
    assert not trace('S' * 12 + 'K' * 32)['upright_kneel_upright_proxy_present']
    assert not trace('S' + 'K' * 31 + 'S' * 12)['upright_kneel_upright_proxy_present']


def test_crouch_and_single_frame_glitch_do_not_count_as_kneeling():
    assert not trace('S' * 12 + 'C' * 20 + 'S' * 12)['upright_kneel_upright_proxy_present']
    assert not trace('S' * 12 + 'K' + 'S' * 12)['upright_kneel_upright_proxy_present']


def test_invalid_trace_is_rejected():
    with pytest.raises(ValueError):
        summarize_trace([1., np.nan], np.ones((2, 2)), np.zeros((2, 2)), 30.)
