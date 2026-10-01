"""Explicit native-key and fractional-event clocks for engine comparisons."""
import numpy as np


def clock_echo_matches(requested, observed):
    requested, observed = float(requested), float(observed)
    # Godot's JSON decimal parser can differ by two double ULPs. Do not
    # substitute the much looser pose tolerance for the requested clock.
    return bool(np.isfinite(requested) and np.isfinite(observed) and requested >= 0 and
                abs(requested-observed) <= 2*abs(np.spacing(requested)))


def audit_clock(duration, key_times, declared_times, event, hz=120):
    duration, event = float(duration), float(event)
    if not np.isfinite(duration) or not 0 < duration <= 30 or not np.isfinite(event) or not 0 <= event <= duration:
        raise ValueError('Finite clip duration and in-range event required')
    if type(hz) is not int or not 1 <= hz <= 1000:
        raise ValueError('Integer sampling frequency required')
    groups = [np.arange(int(np.floor(duration*hz))+1, dtype=float)/hz, np.array([duration, event])]
    for keys in key_times:
        keys = np.asarray(keys, float)
        if keys.ndim != 1 or not len(keys) or not np.isfinite(keys).all() or np.any(np.diff(keys) <= 0):
            raise ValueError('Increasing finite native keys required')
        groups.extend([keys, (keys[:-1]+keys[1:])/2])
    declared = np.asarray(declared_times, float)
    if declared.ndim != 1:
        raise ValueError('Declared samples must be a vector')
    groups.append(declared)
    times = np.unique(np.concatenate(groups))
    if not np.isfinite(times).all() or times[0] < 0 or times[-1] > duration:
        raise ValueError('Audit samples outside actual duration')
    # Exact deduplication only: float32 keys and nearby authored events differ.
    return times


def compare_poses(expected, found):
    expected, found = np.asarray(expected, float), np.asarray(found, float)
    if expected.ndim != 3 or expected.shape[1:] != (4, 4) or found.shape != (len(expected), 4, 3):
        raise ValueError('Joint matrix dimensions differ')
    if not np.isfinite(expected).all() or not np.isfinite(found).all():
        raise ValueError('Non-finite engine/source pose')
    return dict(position_error_m=float(np.abs(found[:, 3]-expected[:, :3, 3]).max()),
                basis_element_error=float(np.abs(found[:, :3].transpose(0, 2, 1)-expected[:, :3, :3]).max()))
