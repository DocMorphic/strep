"""Compare actual per-joint peak rates independently of changing reference caps."""
import numpy as np


def compare(before, after, tolerance=1e-7):
    if len(before) != 4 or len(after) != 4 or not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Four rate groups and a finite nonnegative tolerance required')
    result = []
    for kind, source, candidate in zip(('position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'), before, after):
        source, candidate = np.asarray(source, float), np.asarray(candidate, float)
        if (source.ndim != 2 or not all(source.shape) or source.shape != candidate.shape
                or not np.isfinite(source).all() or not np.isfinite(candidate).all()
                or np.any(source < 0) or np.any(candidate < 0)):
            raise ValueError('Matching finite nonnegative sampled joint rates required')
        a, b = source.max(axis=0), candidate.max(axis=0); increase = b-a
        result.append(dict(kind=kind, source_peaks=a.tolist(), candidate_peaks=b.tolist(),
            regressing_joints=int(np.count_nonzero(increase > tolerance)), maximum_increase=float(increase.max()),
            worst_column=int(increase.argmax())))
    return dict(tolerance=tolerance, rates=result, absolute_peak_guard_pass=all(r['regressing_joints'] == 0 for r in result), quality_approved=False)
