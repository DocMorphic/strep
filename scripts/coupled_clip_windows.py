"""Choose bounded work from all remaining whole-clip root failures."""
import numpy as np


def choose_windows(acceleration, original_peak, frame_count, max_blocks=4, radius=2):
    values = np.asarray(acceleration, dtype=float)
    if values.shape != (frame_count-2,) or frame_count < 5 or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError('Finite whole-clip acceleration magnitudes required')
    if not np.isfinite(original_peak) or original_peak < 0 or max_blocks < 1 or radius < 0:
        raise ValueError('Positive work budget and nonnegative reference required')
    # Stable frame ordering resolves ties. Fixed endpoint frames keep their keys.
    ordered = sorted(np.flatnonzero(values > original_peak+.0036)+1, key=lambda c: (-values[c-1], c))
    covered, result = set(), []
    for center in ordered:
        if center in covered:
            continue
        frames = list(range(max(2, int(center)-radius), min(frame_count-2, int(center)+radius+1)))
        if not frames:
            continue
        affected = sorted({f+d for f in frames for d in [-1, 0, 1] if 1 <= f+d < frame_count-1})
        covered.update(affected)
        result.append(dict(center=int(center), frames=frames, affected_centers=affected))
        if len(result)==max_blocks:
            break
    return result
