"""Per-joint quaternion replay independent of the fitter's matrix-delta rows."""
import numpy as np
from scipy.spatial.transform import Rotation


def angular_replay(source, candidate, times, knots, tolerance=1e-5):
    source, candidate, times, knots = map(lambda x:np.asarray(x, float), [source, candidate, times, knots])
    if source.shape != candidate.shape or source.ndim != 4 or source.shape[2:] != (3, 3) or len(source) < 3 or source.shape[1] < 1:
        raise ValueError('Matching rotation tracks required')
    if times.shape != (len(source),) or not np.isfinite(times).all() or np.any(np.diff(times) <= 0) or not np.allclose(np.diff(times), times[1]-times[0], atol=1e-12, rtol=0):
        raise ValueError('Matching uniform increasing seconds required')
    if knots.ndim != 1 or len(knots) < 3 or not np.isfinite(knots).all() or np.any(np.diff(knots) <= 0) or not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Increasing knots and nonnegative tolerance required')
    for track in [source, candidate]:
        if not np.isfinite(track).all() or not np.allclose(track@track.transpose(0,1,3,2), np.eye(3), atol=1e-6, rtol=0) or not np.allclose(np.linalg.det(track), 1., atol=1e-6, rtol=0):
            raise ValueError('Proper rotation tracks required')
    result = {k:dict(observations=0, exceeding_observations=0, maximum_increase=0., tolerance=tolerance) for k in ['angular_speed_rad_s', 'angular_acceleration_rad_s2']}
    dt = float(times[1]-times[0]); edges = np.r_[-np.inf, knots[1:-1], np.inf]
    for joint in range(source.shape[1]):
        vectors = []
        for track in [source, candidate]:
            orientations = Rotation.from_matrix(track[:, joint])
            delta = (orientations[1:]*orientations[:-1].inv()).as_rotvec()
            if np.any(np.linalg.norm(delta, axis=1) >= np.pi-1e-6): raise ValueError('Ambiguous angular step')
            velocity = delta/dt; vectors.append([velocity, np.diff(velocity, axis=0)/dt])
        for order, (kind, summary) in enumerate(result.items()):
            clock = (times[:-1]+times[1:])/2 if order == 0 else times[1:-1]
            before, after = [np.linalg.norm(v[order], axis=1) for v in vectors]
            for left, right in zip(edges[:-1], edges[1:]):
                mask = (clock >= left) & (clock < right)
                if not mask.any(): continue
                excess = after[mask]-before[mask].max()
                summary['observations'] += int(mask.sum())
                summary['exceeding_observations'] += int((excess > tolerance).sum())
                summary['maximum_increase'] = max(summary['maximum_increase'], float(excess.max()))
    return result


def compare_saved(replayed, saved):
    if set(replayed) != set(saved): raise ValueError('Angular metric population differs')
    for kind, value in replayed.items():
        prior = saved[kind]
        if any(value[k] != prior[k] for k in ['observations', 'exceeding_observations', 'tolerance']):
            raise ValueError('Independent angular replay disagrees')
        if not np.isfinite(prior['maximum_increase']) or abs(value['maximum_increase']-prior['maximum_increase']) > 1e-8:
            raise ValueError('Independent angular peak differs')
