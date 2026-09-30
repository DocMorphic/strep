import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_scene_pair_fit import rate_check


def test_independent_replay_detects_rate_increase_and_counts_every_joint():
    times = np.arange(25)/120; source = np.zeros((25, 2, 3))
    source[:, 0, 0] = times; knots = [0., .05, .1, .15, .2]
    candidate = source.copy(); candidate[12, 1, 1] = .001
    result = rate_check(source, candidate, times, knots)
    assert result['checked'] == (24+23)*2
    assert result['failures'] == 5  # Two velocity and three acceleration stencils.
    assert result['maximum_excess'] > 20
    unchanged = rate_check(source, source.copy(), times, knots)
    assert unchanged['failures'] == 0


def test_replay_preserves_local_span_caps_instead_of_global_peak_allowance():
    times = np.arange(61)/120; source = np.zeros((61, 1, 3))
    source[:25, 0, 0] = np.sin(times[:25]*10)
    candidate = source.copy(); candidate[50, 0, 1] = .0001
    result = rate_check(source, candidate, times, [0., .25, .4, .5])
    assert result['failures'] == 5
