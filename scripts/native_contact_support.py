"""Identify contact clocks that declared native edits cannot change.

This structural diagnostic keeps original channels, contact limits and clocks.
It is a necessary-condition check, never a correction or quality approval.
"""
import numpy as np


def fixed_actor_times(edits, name, times):
    times = np.asarray(times, float)
    if times.ndim != 1 or not len(times) or not np.isfinite(times).all():
        raise ValueError('Complete finite contact times required')
    fixed = np.ones(len(times), bool)
    if name not in edits.actors:
        return fixed
    for entry in edits.actors[name]['tracks']:
        clock = np.asarray(entry['clock'], float)
        ids = np.asarray(entry['ids'])
        weights = np.asarray(entry['weights'], float)
        if (clock.ndim != 1 or len(clock) < 2 or not np.isfinite(clock).all()
                or np.any(np.diff(clock) <= 0) or ids.ndim != 1 or ids.dtype.kind not in 'iu'
                or np.any(ids < 0) or np.any(ids >= len(clock)) or len(np.unique(ids)) != len(ids)
                or weights.ndim != 2 or weights.shape[0] != len(ids)
                or not weights.shape[1] or not np.isfinite(weights).all()):
            raise ValueError('Complete original native clocks, key indices and weights required')
        mutable = np.zeros(len(clock), bool)
        mutable[ids] = np.any(weights != 0, axis=1)
        # LINEAR native channels clamp at the endpoints. An exact key only
        # depends on that key; an interior time uses both neighboring keys.
        right = np.searchsorted(clock, times, side='left')
        safe = np.minimum(right, len(clock)-1)
        exact = (right < len(clock)) & (clock[safe] == times)
        left = np.clip(right-1, 0, len(clock)-1)
        right = np.clip(right, 0, len(clock)-1)
        left[exact] = right[exact]
        fixed &= ~(mutable[left] | mutable[right])
    return fixed


def contact_support(problem):
    """Full ContactNorms row order: orientations, then both facing sides."""
    point_masks = []; observations = []; identity = []
    for data in problem.rows:
        entry = data['entry']; row = entry['authored']; target = row['target']
        actors = [row['actor']]
        if target['space'] == 'actor':
            actors.append(target['actor'])
        if any(n not in problem.scene.actors for n in actors):
            raise ValueError('Existing contact actors required')
        times = np.asarray(data['times'], float)
        mask = np.ones(len(times), bool)
        for name in actors:
            mask &= fixed_actor_times(problem.edits, name, times)
        count = 1 if row['reduction'] == 'centroid' else len(entry['ids'])
        if not count:
            raise ValueError('Complete nonempty contact references required')
        point_masks.append(np.repeat(mask, count))
        observations.append(dict(contact=row['id'],times_s=times.tolist(),
            fixed_pose_times=mask.tolist(),points_per_time=count))
        identity.extend(dict(contact=row['id'],time_s=float(t),point=k)
            for t in times for k in range(count))
    if not point_masks:
        raise ValueError('Complete nonempty contact population required')
    points = np.concatenate(point_masks)
    return np.r_[points, np.repeat(points, 2)], dict(
        point_identity=identity,contacts=observations,complete_point_observations=len(points),
        complete_surface_rows=3*len(points),structurally_fixed_point_observations=int(points.sum()),
        structurally_fixed_surface_rows=3*int(points.sum()),
        support_rule='All declared tracks of every involved actor have unchanged native interpolation keys. Object/world targets retain their source trajectories.',
        conservative=True,original_conditions_unchanged=True,
        quality_approved=False,release_approved=False)


def diagnose(problem, source_contact_residual):
    """Reduce an independently measured complete unchanged-source population.

    The caller must supply ContactNorms residuals from the canonical source,
    not a candidate, partial audit or reordered population. This function
    diagnoses structural support; it does not authenticate a measurement.
    """
    problem.scene.check_inputs()
    fixed, report = contact_support(problem)
    residual = np.asarray(source_contact_residual, float)
    if residual.shape != fixed.shape or not np.isfinite(residual).all():
        raise ValueError('Matching complete finite source contact residuals required')
    failed = np.flatnonzero(fixed & (residual > 0))
    report.update(fixed_source_failures_present=bool(len(failed)),
        failed_fixed_surface_rows=failed.tolist(),failed_fixed_surface_row_count=len(failed),
        maximum_fixed_source_violation=float(np.maximum(residual[fixed],0).max(initial=0)),
        measurement_authenticated=False,
        scope='Conditional necessary support diagnostic on supplied unchanged-source residuals. Fixed failing contacts require an explicitly revised edit setup or targets; no limit is changed here. Absence of a fixed failure does not prove feasibility, collision safety, dynamics or quality.')
    problem.scene.check_inputs()
    return fixed, report
