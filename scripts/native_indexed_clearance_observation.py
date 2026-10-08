"""Observe every declared clearance row from complete indexed point frames.

Clock and vertex lookups are built once per observation. Each projection keeps
the original scalar subtraction/dot arithmetic; no axis normalization, margin
adjustment, derivative, collision predicate or release approval is introduced.
Callers bind the declared point populations to actual decoded source assets.
"""
import copy
from dataclasses import dataclass
import numpy as np


@dataclass
class PointFrame:
    actor: str
    time_s: float
    vertex_ids: list
    points_world: np.ndarray


@dataclass
class ClearanceObservation:
    gaps_m: np.ndarray
    clearances_m: np.ndarray
    failed_rows: np.ndarray
    descriptors: list
    report: dict


def observe(descriptors, clearances_m, frames, required_times_s, required_actors,
            *, maximum_rows=400000, maximum_point_elements=60000000):
    """Retain every supplied row and validate all declared points, even unused.

One frame is required for every original actor/time. Vertex indices refer to
original assets and may differ between complete guide and component frames.
Duplicate row identities remain separate protections in their original order.
Declared frames do not independently prove full mesh or time coverage.
"""
    if (not isinstance(descriptors, list) or not isinstance(frames, list)
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 400000
            or type(maximum_point_elements) is not int or not 1 <= maximum_point_elements <= 60000000
            or len(descriptors) > maximum_rows
            or not isinstance(required_actors, list) or not 2 <= len(required_actors) <= 8
            or any(type(a) is not str or not a for a in required_actors)
            or len(set(required_actors)) != len(required_actors)
            or not isinstance(required_times_s, list) or not 1 <= len(required_times_s) <= 4096
            or any(type(t) not in (int, float) for t in required_times_s)
            or len(frames) != len(required_actors)*len(required_times_s)):
        raise ValueError('Complete original row, actor, clock and point-frame populations required')
    times = np.array(required_times_s, dtype=float)
    if not np.isfinite(times).all() or np.any(times < 0) or np.any(np.diff(times) <= 0):
        raise ValueError('Finite ordered original clock required')
    margins = np.asarray(clearances_m)
    if (margins.shape != (len(descriptors),) or margins.dtype.kind not in 'fiu'
            or not np.isfinite(margins).all() or np.any(margins <= 0)):
        raise ValueError('Every original finite positive clearance margin required')
    margins = margins.astype(float, copy=True)
    if not np.isfinite(margins).all():
        raise ValueError('Original margins must remain finite in Float64')
    actors, clock = set(required_actors), set(required_times_s)
    lookup, elements = {}, 0
    for frame in frames:
        if (not isinstance(frame, PointFrame) or type(frame.actor) is not str
                or frame.actor not in actors or type(frame.time_s) not in (int, float)
                or frame.time_s not in clock or (frame.actor, frame.time_s) in lookup
                or not isinstance(frame.vertex_ids, list) or not frame.vertex_ids
                or any(type(v) is not int or v < 0 for v in frame.vertex_ids)
                or frame.vertex_ids != sorted(set(frame.vertex_ids))):
            raise ValueError('One explicitly indexed point frame per original actor/time required')
        points = np.asarray(frame.points_world)
        if (points.shape != (len(frame.vertex_ids), 3) or points.dtype.kind not in 'fiu'
                or not np.isfinite(points).all()):
            raise ValueError('Every declared point must have three finite numeric coordinates')
        elements += points.size
        if elements > maximum_point_elements:
            raise ValueError('Complete point population exceeds its explicit budget')
        points = points.astype(float, copy=True)
        if not np.isfinite(points).all():
            raise ValueError('Complete point population must remain finite in Float64')
        lookup[frame.actor, frame.time_s] = (points, {v: i for i, v in enumerate(frame.vertex_ids)})
    if set(lookup) != {(a, t) for a in actors for t in clock}:
        raise ValueError('Every original actor/time must be represented')
    gaps = np.empty(len(descriptors), dtype=float)
    for i, (descriptor, margin) in enumerate(zip(descriptors, margins)):
        if not isinstance(descriptor, dict):
            raise ValueError('Explicit original clearance descriptor required')
        pair, time, axis = [descriptor.get(k) for k in ('actors', 'time_s', 'axis_world')]
        if (not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1]
                or any(type(a) is not str or a not in actors for a in pair)
                or type(time) not in (int, float) or time not in clock
                or not isinstance(axis, list) or len(axis) != 3
                or any(type(v) not in (int, float) for v in axis)
                or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.) > 1e-12
                or type(descriptor.get('clearance_m')) not in (int, float)
                or descriptor['clearance_m'] != margin):
            raise ValueError('Every original actor/time, unit axis and unchanged margin required')
        selected = []
        for actor, key in zip(pair, ('left_vertex', 'right_vertex')):
            points, indices = lookup[actor, time]
            vertex = descriptor.get(key)
            if type(vertex) is not int or vertex not in indices:
                raise ValueError('Every referenced original vertex must exist at its exact time')
            selected.append(points[indices[vertex]])
        gaps[i] = float((selected[0]-selected[1])@np.array(axis, dtype=float))
        if not np.isfinite(gaps[i]):
            raise ValueError('Every original scalar clearance projection must remain finite')
    failed = np.flatnonzero(gaps < margins)
    return ClearanceObservation(gaps, margins, failed, copy.deepcopy(descriptors), dict(
        complete_rows=len(gaps), complete_point_frames=len(frames), point_elements=elements,
        failed_rows=len(failed), declared_clearance_rows_pass=not len(failed),
        original_axes_margins_and_row_order_preserved=True, all_declared_points_validated=True,
        source_provenance_verified=False, full_mesh_or_time_coverage_certified=False,
        derivatives_used=False, collision_predicates_evaluated=False,
        quality_approved=False, release_approved=False))
