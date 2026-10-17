"""Time-aware, bounded pose-control taper on an unchanged native key clock.

The underlying weight is C2. Native-key quaternion interpolation, world edit
bounds, rates, contacts and collisions require separate decoded validation.
"""
import numpy as np


def taper(clock, anchor, *, start_key, peak_key, end_key):
    clock = np.asarray(clock); anchor = np.asarray(anchor)
    if (clock.dtype.kind not in 'fiu' or clock.ndim != 1 or not 3 <= len(clock) <= 4096
            or not np.isfinite(clock).all() or clock[0] < 0
            or np.any(np.diff(clock.astype(float)) <= 0)
            or any(type(k) is not int for k in (start_key, peak_key, end_key))
            or not 0 <= start_key < peak_key < end_key < len(clock)
            or anchor.dtype.kind not in 'fiu' or anchor.ndim != 2 or anchor.shape[1:] != (3,)
            or not 1 <= len(anchor) <= 32 or not np.isfinite(anchor).all()):
        raise ValueError('Increasing native clock, ordered existing keys and 1-32 complete finite control vectors required')
    with np.errstate(over='ignore', invalid='ignore'):
        norms = np.linalg.norm(anchor.astype(float), axis=1)
    if not np.isfinite(norms).all() or np.any(norms > 1):
        raise ValueError('Original-relative normalized rotation controls must fit each unit ball')
    times = clock.astype(float); weights = np.zeros(len(times))
    for first, last, rising in ((start_key, peak_key, True), (peak_key, end_key, False)):
        u = (times[first:last+1]-times[first])/(times[last]-times[first])
        if not rising:
            u = 1-u
        # Clipping bounds floating-point evaluation of a polynomial in [0,1].
        weights[first:last+1] = np.clip(u**3*(10+u*(-15+6*u)), 0., 1.)
    weights[start_key] = weights[end_key] = 0.; weights[peak_key] = 1.
    values = weights[:, None, None] * anchor.astype(float)[None]
    report = dict(schema='strep-native-key-control-taper-v1', native_keys=len(times),
        controlled_joints=len(anchor), start_key=start_key, peak_key=peak_key, end_key=end_key,
        start_s=float(times[start_key]), peak_s=float(times[peak_key]), end_s=float(times[end_key]),
        maximum_anchor_fraction=float(norms.max()), native_clock_resampled=False,
        source_reference_recentered=False, quality_approved=False, release_approved=False,
        scope='Convex scaling of supplied original-relative rotation-vector controls at every supplied key. '
              'Underlying weight is C2 in seconds; no decoded quaternion smoothness, subkey angular/world '
              'bounds, contact, collision, rate, engine or human quality certificate.')
    return values, weights, report
