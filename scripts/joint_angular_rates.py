"""Sampled world-frame rotation rates, independent of joint translations."""
import numpy as np
from scipy.spatial.transform import Rotation


def angular_vectors(rotations, times):
    r = np.asarray(rotations, float); times = np.asarray(times, float)
    if r.ndim != 4 or r.shape[-2:] != (3, 3) or r.shape[0] < 3 or r.shape[1] < 1 or not np.isfinite(r).all():
        raise ValueError('Finite time-by-joint proper rotation matrices required')
    if times.shape != (len(r),) or not np.isfinite(times).all() or np.any(np.diff(times) <= 0) or not np.allclose(np.diff(times), times[1]-times[0], atol=1e-12, rtol=0):
        raise ValueError('Matching increasing uniform seconds required')
    if not np.allclose(r@r.transpose(0, 1, 3, 2), np.eye(3), atol=1e-6, rtol=0) or not np.allclose(np.linalg.det(r), 1., atol=1e-6, rtol=0):
        raise ValueError('Scaled, reflected or sheared matrices are not rotation tracks')
    delta = Rotation.from_matrix((r[1:]@r[:-1].transpose(0, 1, 3, 2)).reshape(-1, 3, 3)).as_rotvec().reshape(len(r)-1, r.shape[1], 3)
    if np.any(np.linalg.norm(delta, axis=2) >= np.pi-1e-6): raise ValueError('Ambiguous near-pi sampled angular step')
    dt = float(times[1]-times[0]); velocity = delta/dt
    return [(velocity, (times[1:]+times[:-1])/2), (np.diff(velocity, axis=0)/dt, times[1:-1])]


def compare_angular_rates(source, candidate, times, knots, names, *, speed_tolerance, acceleration_tolerance):
    before = angular_vectors(source, times); after = angular_vectors(candidate, times)
    knots = np.asarray(knots, float)
    if np.shape(source) != np.shape(candidate) or len(names) != np.shape(source)[1] or len(set(names)) != len(names):
        raise ValueError('Matching tracks and distinct joint names required')
    if knots.ndim != 1 or len(knots) < 3 or not np.isfinite(knots).all() or np.any(np.diff(knots) <= 0):
        raise ValueError('Increasing source knot times required')
    tolerances = [speed_tolerance, acceleration_tolerance]
    if any(type(t) not in (int, float) or not np.isfinite(t) or t < 0 for t in tolerances): raise ValueError('Explicit finite nonnegative angular tolerances required')
    result = {}
    for metric, (a, clock), (b, other_clock), tolerance in zip(['angular_speed_rad_s', 'angular_acceleration_rad_s2'], before, after, tolerances):
        np.testing.assert_array_equal(clock, other_clock)
        a = np.linalg.norm(a, axis=2); b = np.linalg.norm(b, axis=2)
        bins = np.searchsorted(knots[1:-1], clock, side='right'); summaries = []; comparisons = 0; failures = 0; maximum = 0.
        for span in np.unique(bins):
            mask = bins == span; cap = a[mask].max(axis=0); excess = b[mask]-cap
            comparisons += excess.size; failures += int((excess > tolerance).sum()); maximum = max(maximum, float(excess.max()))
            for j, name in enumerate(names):
                peak = int(np.argmax(b[mask, j]))
                summaries.append(dict(joint=name, span=int(span), source_peak=float(cap[j]), candidate_peak=float(b[mask, j].max()),
                    candidate_peak_time_s=float(clock[mask][peak]), maximum_increase=float(excess[:, j].max()),
                    observations=int(mask.sum()), exceeding_observations=int((excess[:, j] > tolerance).sum())))
        result[metric] = dict(tolerance=tolerance, observations=comparisons, exceeding_observations=failures,
            maximum_increase=maximum, joint_spans=summaries)
    return result
