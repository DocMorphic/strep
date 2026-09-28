from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from foot_acceleration import acceleration_caps, foot_acceleration_pair, foot_acceleration_energy


@pytest.mark.parametrize('frame', [0, 1, 4, 7, 8])
def test_coordinate_gradient_and_global_energy_change(frame):
    rng = np.random.default_rng(8172)
    track = rng.normal(0, .01, (9, 2, 3))
    jac = rng.normal(0, .1, (2, 3, 7))
    caps = np.full((7, 2), 3.)
    x = rng.normal(0, .01, 7)
    candidate = track[frame]+np.einsum('sip,p->si', jac, x)
    r, j = foot_acceleration_pair(track, frame, candidate, jac, caps, 30., .7)
    old, _ = foot_acceleration_pair(track, frame, track[frame], jac, caps, 30., .7)
    changed = track.copy(); changed[frame] = candidate
    assert r@r-old@old == pytest.approx(foot_acceleration_energy(changed, caps, 30., .7)-foot_acceleration_energy(track, caps, 30., .7), abs=1e-10)
    eps = 1e-7
    numerical = np.column_stack([(foot_acceleration_pair(track, frame, candidate+eps*d, jac, caps, 30., .7)[0]-foot_acceleration_pair(track, frame, candidate-eps*d, jac, caps, 30., .7)[0])/(2*eps) for d in np.moveaxis(jac, -1, 0)])
    np.testing.assert_allclose(j, numerical, atol=2e-7, rtol=1e-7)


def test_fixed_baseline_caps_and_swing_snap_detected():
    raw = np.zeros((9, 2, 3)); raw[:, :, 0] = np.arange(9)[:, None]*.002
    caps = acceleration_caps(raw, raw, 30.)
    assert foot_acceleration_energy(raw, caps, 30., 1.) == 0
    snap = raw.copy(); snap[:4, 0, 0] += .008
    assert foot_acceleration_energy(snap, caps, 30., 1.) > 100
    np.testing.assert_allclose(caps, 1e-5, atol=1e-14)


def test_inactive_zero_and_threshold_are_finite():
    track = np.zeros((5, 2, 3)); caps = np.zeros((3, 2)); jac = np.ones((2, 3, 4))
    r, j = foot_acceleration_pair(track, 2, track[2], jac, caps, 30., 1.)
    assert not r.any() and not j.any()
    r, j = foot_acceleration_pair(track, 2, np.ones((2, 3)), jac, caps, 30., 0.)
    assert not r.any() and not j.any()


def test_invalid_inputs_rejected():
    track = np.zeros((5, 2, 3)); caps = np.zeros((3, 2)); jac = np.ones((2, 3, 4))
    for fps, weight in [(0, 1), (30, -1), (float('nan'), 1)]:
        with pytest.raises(ValueError): foot_acceleration_pair(track, 2, track[2], jac, caps, fps, weight)
    with pytest.raises(ValueError): foot_acceleration_energy(track, caps-1, 30., 1.)
    with pytest.raises(ValueError): acceleration_caps(track, track[:-1], 30.)
