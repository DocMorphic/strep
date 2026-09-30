"""Fixed signed-witness limits for correction experiments, not mesh clearance."""
import numpy as np


def limits(depths, tolerance=.005, numerical_slack=1e-8):
    depths = np.asarray(depths, float)
    if depths.ndim != 1 or not len(depths) or not np.isfinite(depths).all():
        raise ValueError('Nonempty finite signed witness depths required')
    if not np.isfinite(tolerance) or tolerance < 0 or not np.isfinite(numerical_slack) or numerical_slack < 0:
        raise ValueError('Finite nonnegative envelope tolerance and slack required')
    return np.maximum(tolerance, depths) + numerical_slack


def guarded(evaluate, bounds):
    """Copy limits once; append exact signed-depth margins on every evaluation."""
    bounds = np.array(bounds, dtype=float, copy=True)
    if bounds.ndim != 1 or not len(bounds) or not np.isfinite(bounds).all() or np.any(bounds < 0):
        raise ValueError('Nonempty finite nonnegative fixed witness bounds required')
    bounds.setflags(write=False)
    def sample(point):
        result = dict(evaluate(point)); depths = np.asarray(result['depths'], float)
        if depths.shape != bounds.shape or not np.isfinite(depths).all():
            raise ValueError('Fixed finite witness population required')
        # The same .02 m conditioning used by the existing depth epigraph.
        result['margins'] = np.r_[result['margins'], (bounds-depths)/.02]
        return result
    return sample
