"""Keep previously clear sample times clear without widening original ceilings."""
import numpy as np


def protected_caps(original_depths, starting_depths):
    original, start = np.asarray(original_depths, float), np.asarray(starting_depths, float)
    if original.ndim != 1 or not len(original) or start.shape != original.shape:
        raise ValueError('Matched nonempty depth populations required')
    if not np.isfinite(original).all() or not np.isfinite(start).all() or np.any(original < 0) or np.any(start < 0):
        raise ValueError('Finite nonnegative depths required')
    ceilings = np.maximum(.005, original)
    if np.any(start > ceilings + 1e-6):
        raise ValueError('Starting depths exceed original ceilings')
    return np.where(start <= .005, .005, ceilings)


def compare_depths(starting_depths, candidate_depths, caps):
    start, candidate, caps = (np.asarray(v, float) for v in (starting_depths, candidate_depths, caps))
    if start.ndim != 1 or not len(start) or candidate.shape != start.shape or caps.shape != start.shape:
        raise ValueError('Matched nonempty depth populations required')
    if any(not np.isfinite(v).all() or np.any(v < 0) for v in (start, candidate, caps)):
        raise ValueError('Finite nonnegative depths required')
    excess = np.maximum(0., candidate - caps)
    return dict(start_peak_m=float(start.max()), candidate_peak_m=float(candidate.max()),
                improvement_m=float(start.max()-candidate.max()),
                maximum_cap_excess_m=float(excess.max()),
                cap_failures_over_1e_6=int(np.sum(excess > 1e-6)),
                lost_clearances_strict=int(np.sum((start <= .005) & (candidate > .005))),
                lost_clearances_over_1e_6=int(np.sum((start <= .005) & (candidate > .005001))))
