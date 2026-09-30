"""Identify sampled collisions that no permitted native-key edit can change."""
import numpy as np


def movable_times(model):
    movable = np.zeros(len(model.times), bool)
    for entry in model.entries:
        for row, key in enumerate(entry['ids']):
            if np.any(entry['weights'][row] != 0):
                movable |= (model.times > entry['clock'][key-1]) & (model.times < entry['clock'][key+1])
    return movable


def fixed_collision_floor(models, samples, tolerance_m=.005):
    if len(models) != 2 or not np.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError('Two models and positive clearance tolerance required')
    times = models[0].times; np.testing.assert_array_equal(times, models[1].times)
    if len(samples) != len(times) or [r['sample'] for r in samples] != list(range(len(times))) or not np.array_equal([r['time_s'] for r in samples], times):
        raise ValueError('Complete matching sampled geometry required')
    moving = [movable_times(m) for m in models]; fixed = ~(moving[0] | moving[1]); rows = []
    for index in np.flatnonzero(fixed):
        depths = [d['maximum_depth_m'] for d in samples[index]['directions']]
        if len(depths) != 2 or any(not np.isfinite(d) or d < 0 for d in depths): raise ValueError('Two finite source depths required')
        depth = float(max(depths)); rows.append(dict(sample=int(index), time_s=float(times[index]), depth_m=depth, exceeds_tolerance=depth > tolerance_m))
    peak = max((r['depth_m'] for r in rows), default=0.)
    return dict(fixed_samples=rows, fixed_sample_count=len(rows), fixed_failing_samples=sum(r['exceeds_tolerance'] for r in rows),
        unavoidable_sampled_peak_m=peak, clearance_ruled_out_by_fixed_samples=bool(peak > tolerance_m), tolerance_m=tolerance_m,
        scope='Only samples where neither actor has any editable quaternion-key support. A fixed violating sample rules out complete sampled clearance for this request. Absence of one does not prove reachability or feasibility.', quality_approved=False)
