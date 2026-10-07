"""Actual LINEAR native-key support of an authored control basis.

A control knot at an event is not necessarily an exported animation key.
For rotation tracks this describes interpolation support of key parameters,
not a SLERP pose Jacobian or a guarantee of meeting a contact target.
"""
import numpy as np
from native_support_clock import NativeSupportSampler


def effective_basis(clock, editable_keys, key_weights, time):
    clock = np.asarray(clock)
    ids = np.asarray(editable_keys)
    weights = np.asarray(key_weights)
    if (clock.ndim != 1 or len(clock) < 2 or clock.dtype.kind not in 'fiu'
            or not np.isfinite(clock).all() or clock[0] < 0 or np.any(np.diff(clock) <= 0)
            or ids.ndim != 1 or ids.dtype.kind not in 'iu' or not len(ids)
            or np.any(ids < 0) or np.any(ids >= len(clock)) or np.any(np.diff(ids.astype(np.int64)) <= 0)
            or weights.ndim != 2 or weights.shape[0] != len(ids) or not 1 <= weights.shape[1] <= 96
            or weights.dtype.kind not in 'fiu' or not np.isfinite(weights).all()
            or isinstance(time, (bool, np.bool_)) or not isinstance(time, (int, float, np.integer, np.floating))
            or not np.isfinite(time) or time < 0):
        raise ValueError('Complete increasing native clock, ordered editable key basis and finite nonnegative scalar time required')
    # Preserve native clock dtype and incoming scalar time. In particular, do
    # not turn Float32 key subtraction or endpoint comparisons into Float64.
    values = np.zeros((len(clock), weights.shape[1]), dtype=float)
    values[ids] = weights
    result = NativeSupportSampler.value('translation', clock, values, 'LINEAR', time)
    if not np.isfinite(result).all():
        raise ValueError('Complete finite sampled control basis required')
    return result
