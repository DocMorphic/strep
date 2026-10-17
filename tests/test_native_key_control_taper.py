"""Native clock, reference and angular bounds survive local pose tapering."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_key_control_taper import taper


def test_anchor_and_outside_keys_are_exact_and_readonly_inputs_are_unchanged():
    clock = np.arange(9, dtype=np.float32); anchor = np.array([[.6, .8, 0], [0, -.2, .1]])
    clock.setflags(write=False); anchor.setflags(write=False)
    result, weights, report = taper(clock, anchor, start_key=1, peak_key=4, end_key=7)
    np.testing.assert_array_equal(result[4], anchor)
    np.testing.assert_array_equal(result[[0, 1, 7, 8]], np.zeros((4, 2, 3)))
    assert np.all((weights >= 0) & (weights <= 1))
    assert np.all(np.linalg.norm(result, axis=-1) <= 1)
    assert report['native_clock_resampled'] is report['source_reference_recentered'] is False
    assert not report['quality_approved']
    np.testing.assert_array_equal(clock, np.arange(9, dtype=np.float32))
    np.testing.assert_array_equal(anchor, [[.6, .8, 0], [0, -.2, .1]])


def test_nonuniform_clock_uses_seconds_instead_of_key_indices():
    _, weights, _ = taper([0., .25, 1., 2., 5.], [[1., 0, 0]], start_key=0, peak_key=2, end_key=4)
    np.testing.assert_array_equal(weights, [0., .103515625, 1., .896484375, 0.])


def test_clock_subdivision_does_not_change_existing_weight_or_control_values():
    anchor = [[.1, -.2, .3]]
    a, aw, _ = taper([0., .25, 1., 2., 5.], anchor, start_key=0, peak_key=2, end_key=4)
    b, bw, _ = taper([0., .125, .25, .75, 1., 1.5, 2., 4., 5.], anchor, start_key=0, peak_key=4, end_key=8)
    np.testing.assert_array_equal(a, b[[0, 2, 4, 6, 8]])
    np.testing.assert_array_equal(aw, bw[[0, 2, 4, 6, 8]])


def test_source_relative_quaternion_angles_match_the_authored_key_bounds():
    anchor = np.array([[.6, .8, 0], [0, -.4, .2]])
    values, weights, _ = taper(np.linspace(0, 3, 31), anchor, start_key=0, peak_key=20, end_key=30)
    caps = np.radians([15., 30.]);rng = np.random.default_rng(17)
    source = Rotation.random(len(values)*2, random_state=rng)
    edited = source * Rotation.from_rotvec((values*caps[None, :, None]).reshape(-1, 3))
    measured = (source.inv()*edited).magnitude().reshape(-1, 2)
    np.testing.assert_allclose(measured, weights[:, None]*np.linalg.norm(anchor, axis=1)*caps, atol=6e-16)
    assert np.all(measured <= caps+6e-16)


def test_underlying_weight_approaches_both_boundaries_cubically():
    h = 1e-3;clock = [0., h, 2*h, 1., 2.-2*h, 2.-h, 2.]
    _, weights, _ = taper(clock, [[1, 0, 0]], start_key=0, peak_key=3, end_key=6)
    assert 7.98 < weights[2]/weights[1] < 8.02
    assert 7.98 < weights[4]/weights[5] < 8.02


def test_complete_budget_and_zero_anchor_remain_valid():
    result, weights, report = taper(np.linspace(0, 100, 4096), np.zeros((32, 3)), start_key=0, peak_key=2048, end_key=4095)
    assert result.shape == (4096, 32, 3) and result.nbytes == 3145728
    assert not np.any(result) and weights[2048] == 1 and report['maximum_anchor_fraction'] == 0


@pytest.mark.parametrize('fault', ['short-clock', 'long-clock', 'unordered-clock', 'nan-clock', 'negative-clock',
    'bool-clock', 'bool-key', 'float-key', 'reversed-keys', 'coincident-keys', 'outside-key', 'empty-anchor',
    'wide-anchor', 'long-anchor', 'bool-anchor', 'nan-anchor', 'over-ball', 'overflow-anchor'])
def test_malformed_or_unbounded_inputs_reject(fault):
    clock = [0., 1., 2.];anchor = [[.1, .2, .3]];kwargs = dict(start_key=0, peak_key=1, end_key=2)
    if fault == 'short-clock': clock = [0., 1.]
    elif fault == 'long-clock': clock = list(range(4097))
    elif fault == 'unordered-clock': clock = [0., 2., 1.]
    elif fault == 'nan-clock': clock[1] = np.nan
    elif fault == 'negative-clock': clock[0] = -1.
    elif fault == 'bool-clock': clock = [False, True, True]
    elif fault == 'bool-key': kwargs['peak_key'] = True
    elif fault == 'float-key': kwargs['peak_key'] = 1.
    elif fault == 'reversed-keys': kwargs['start_key'] = 2
    elif fault == 'coincident-keys': kwargs['peak_key'] = 0
    elif fault == 'outside-key': kwargs['end_key'] = 3
    elif fault == 'empty-anchor': anchor = []
    elif fault == 'wide-anchor': anchor = [[.1, .2]]
    elif fault == 'long-anchor': anchor = [[0., 0, 0]]*33
    elif fault == 'bool-anchor': anchor = [[False, False, False]]
    elif fault == 'nan-anchor': anchor[0][0] = np.nan
    elif fault == 'over-ball': anchor = [[1., 1., 0.]]
    else: anchor = [[1e308, 0., 0.]]
    with pytest.raises(ValueError): taper(clock, anchor, **kwargs)
