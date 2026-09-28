"""Development-only step selection; final motion still needs a full audit."""
import numpy as np


SCREEN = dict(max_sample_penetration_m=.005, max_contact_distance_m=.003,
              min_triangle_area_m2=2.5e-5, opposing_normal_max_degrees=20.)


def select_step(previous, candidate, old_energy, new_energy, region):
    before, after = np.asarray(previous, float), np.asarray(candidate, float)
    if before.ndim != 1 or before.size == 0 or after.shape != before.shape:
        raise ValueError('Matching nonempty sample depths required')
    if not np.isfinite(np.r_[before, after, old_energy, new_energy]).all() or np.any(before < 0) or np.any(after < 0):
        raise ValueError('Finite nonnegative depths and finite energies required')
    directions = region['directions']
    if len(directions) != 2 or {(d['source'], d['target']) for d in directions} != {(0, 1), (1, 0)}:
        raise ValueError('Both contact directions required')
    values = [region['opposing_normal_degrees']]
    for d in directions:
        values.extend([d['within_tolerance_count'], d['source_area_witness']['area_m2'], d['target_area_witness']['area_m2']])
    if not np.isfinite(values).all() or min(values) < 0:
        raise ValueError('Finite nonnegative contact measurements required')
    checks = dict(
        passing_samples_stay_below_screen=bool(np.all(after[before <= SCREEN['max_sample_penetration_m']] <= SCREEN['max_sample_penetration_m'])),
        failing_samples_do_not_worsen=bool(np.all(after[before > SCREEN['max_sample_penetration_m']] <= before[before > SCREEN['max_sample_penetration_m']] + 1e-9)),
        peak_does_not_worsen=bool(after.max() <= before.max() + 1e-9),
        objective_does_not_worsen=bool(new_energy <= old_energy + 1e-9),
        event_region_area=all(d['within_tolerance_count'] >= 3 and min(d['source_area_witness']['area_m2'], d['target_area_witness']['area_m2']) >= SCREEN['min_triangle_area_m2'] for d in directions),
        event_opposing_normals=bool(region['opposing_normal_degrees'] <= SCREEN['opposing_normal_max_degrees']),
    )
    return dict(accepted=all(checks.values()), checks=checks, quality_approved=False)
