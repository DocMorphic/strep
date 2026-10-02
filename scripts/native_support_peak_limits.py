"""Additional full-clip peak bounds; original time-bin caps remain unchanged."""
import numpy as np
from absolute_rate_peaks import compare

STRICT_PEAK_TOLERANCE = 1e-7


def limits(source_rates, caps):
    """Intersect each existing cap-plus-tolerance with its source joint peak."""
    # Validate the same four groups used by the independent final comparison.
    compare(source_rates, source_rates, tolerance=STRICT_PEAK_TOLERANCE)
    if len(caps.caps) != 4 or not np.isfinite(caps.tolerance) or caps.tolerance < 0:
        raise ValueError('Four finite nonnegative source cap groups required')
    result = []
    for source, cap in zip(source_rates, caps.caps):
        source, cap = np.asarray(source, float), np.asarray(cap, float)
        if cap.shape != source.shape or not np.isfinite(cap).all() or np.any(cap < 0):
            raise ValueError('Source rates and time-bin caps must match')
        result.append(np.minimum(cap+caps.tolerance, source.max(axis=0)+STRICT_PEAK_TOLERANCE))
    return tuple(result)
