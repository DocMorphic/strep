"""Deterministic mesh sample clock covering the full editable interval."""
import numpy as np


def edit_interval_clock(window, clocks, required=()):
    bounds=np.asarray(window,float);required=np.asarray(required,float)
    if bounds.shape!=(2,) or not np.isfinite(bounds).all() or not 0<=bounds[0]<bounds[1]:
        raise ValueError('Finite positive edit interval required')
    if required.ndim!=1 or not np.isfinite(required).all() or np.any(required<0):raise ValueError('Finite nonnegative required times needed')
    values=[bounds]
    if not clocks:raise ValueError('Native clocks required')
    for clock in clocks:
        clock=np.asarray(clock,float)
        if clock.ndim!=1 or not len(clock) or not np.isfinite(clock).all() or clock[0]<0 or np.any(np.diff(clock)<=0):
            raise ValueError('Nonempty increasing native clocks required')
        values.append(clock[(clock>bounds[0])&(clock<bounds[1])])
    breaks=np.unique(np.concatenate(values));midpoints=breaks[:-1]+np.diff(breaks)/2
    times=np.unique(np.r_[breaks,midpoints,required])
    return times,dict(window_s=bounds.tolist(),native_partition_s=breaks.tolist(),sample_count=len(times),
        maximum_partition_gap_s=float(np.diff(breaks).max()),continuous_collision_certified=False,
        scope='Every native partition boundary and midpoint inside the complete edit interval, plus all required historical samples.')
