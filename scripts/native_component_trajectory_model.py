"""Complete sampled component trajectories for local collision correction.

Caller binds the required clock, whole original source components and fresh
same-pose point derivatives. These fixed axes do not certify the full mesh
or motion between samples. Original stored scene checks remain decisive.
"""
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from native_convex_component_support import support_pair


@dataclass
class ComponentTrajectoryModel:
    gaps_m: np.ndarray
    jacobian: object
    clearances_m: np.ndarray
    weights_s: np.ndarray
    groups: list
    report: dict


def build(vertices, point_jacobians, local_faces, source_vertex_ids, times_s,
          *, required_times_s, clearance_m=1e-8, maximum_groups=4096,
          maximum_rows=400_000, maximum_elements=60_000_000):
    """Retain all Cartesian vertex pairs at every required original time.

Unlike positive-only guards, colliding samples contribute objective groups.
Initially positive samples receive a capped positive margin. Budgets apply
to the entire population before any support query or row allocation.
    """
    times, required = [np.asarray(v, float) for v in (times_s, required_times_s)]
    if (not isinstance(vertices, dict) or len(vertices) != 2
            or any(type(k) is not str or not k for k in vertices)
            or any(not isinstance(d, dict) or set(d) != set(vertices)
                   for d in (point_jacobians, local_faces, source_vertex_ids))
            or times.ndim != 1 or not len(times) or not np.isfinite(times).all()
            or np.any(times < 0) or np.any(np.diff(times) <= 0)
            or not np.array_equal(times, required)
            or type(clearance_m) not in (int, float) or not np.isfinite(clearance_m)
            or not 1e-9 <= clearance_m <= .001
            or type(maximum_groups) is not int or not 1 <= maximum_groups <= 4096
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 400_000
            or type(maximum_elements) is not int or not 1 <= maximum_elements <= 60_000_000
            or len(times) > maximum_groups):
        raise ValueError('Exact required clock, complete component population and budgets required')
    points, derivatives, ids, faces = {}, {}, {}, {}
    controls = None
    for name in vertices:
        p, j, f = np.asarray(vertices[name], float), np.asarray(point_jacobians[name], float), np.asarray(local_faces[name])
        v = source_vertex_ids[name]
        if (not isinstance(v, list) or not 4 <= len(v) <= 64
                or any(type(i) is not int or i < 0 for i in v) or v != sorted(set(v))
                or p.shape != (len(times), len(v), 3)
                or j.ndim != 4 or j.shape[:3] != p.shape or not 1 <= j.shape[3] <= 96
                or not np.isfinite(p).all() or not np.isfinite(j).all()
                or f.ndim != 2 or f.shape[1] != 3):
            raise ValueError('Finite complete source points and every derivative column required')
        if controls is not None and controls != j.shape[3]:
            raise ValueError('All components must have the same control columns')
        controls = j.shape[3]
        points[name], derivatives[name], ids[name], faces[name] = p, j, list(v), f
    a, b = list(vertices)
    pairs = len(ids[a])*len(ids[b])
    total = len(times)*pairs
    if (total > maximum_rows or total*controls > maximum_elements
            or sum(j.size for j in derivatives.values()) > maximum_elements):
        raise ValueError('Complete trajectory exceeds budget; no subset returned')
    gaps, margins = np.empty(total), np.empty(total)
    columns = np.empty((total, controls))
    groups, positive = [], []
    weights = np.ones(1) if len(times) == 1 else np.concatenate([
        [float((times[1]-times[0])/2)], (times[2:]-times[:-2])/2,
        [float((times[-1]-times[-2])/2)]])
    for frame, time in enumerate(times):
        axis, pair_gaps, support = support_pair(points[a][frame], faces[a], points[b][frame], faces[b])
        first, last = frame*pairs, (frame+1)*pairs
        smallest = float(pair_gaps.min())
        margin = min(clearance_m, smallest) if smallest > 0 else clearance_m
        column = np.array([axis@(derivatives[a][frame,i]-derivatives[b][frame,k])
                           for i in range(len(ids[a])) for k in range(len(ids[b]))])
        if not np.isfinite(column).all():
            raise ValueError('Finite complete trajectory derivative required')
        gaps[first:last], margins[first:last] = pair_gaps.ravel(), margin
        columns[first:last] = column
        if smallest > 0: positive.append(frame)
        groups.append(dict(time_s=float(time), actors=[a,b],
            left_vertex_ids=ids[a].copy(), right_vertex_ids=ids[b].copy(),
            first_row=first, stop_row=last, axis_world=axis.tolist(),
            starting_minimum_support_gap_m=smallest, starts_positive=smallest>0,
            clearance_m=margin, quadrature_weight_s=float(weights[frame]), support_report=support))
    report = dict(schema='strep-native-component-trajectory-model-v1', controls=controls,
        component_samples=len(times), rows=total, times_s=times.tolist(),
        required_times_exact=True, source_vertex_ids=ids,
        complete_component_pair_rows=True, positive_sample_indices=positive,
        full_mesh_pair_partition=False, continuous_coverage=False,
        requested_clearance_m=clearance_m, maximum_groups=maximum_groups,
        maximum_rows=maximum_rows, maximum_elements=maximum_elements,
        weight_policy='trapezoidal clock weights; single-sample weight one',
        quality_approved=False, release_approved=False,
        scope='Every required sampled time and every ordered vertex pair of two supplied '
              'complete convex components. Fixed selected axes and all same-pose control '
              'columns; fresh derivative/source/clock provenance remains caller responsibility. '
              'No original full-mesh, self/object or between-sample collision certificate.')
    return ComponentTrajectoryModel(gaps, sparse.csr_matrix(columns), margins,
                                    weights, groups, report)


def observe(model, vertices):
    """Evaluate the complete declared axes on actual stored component points."""
    if not isinstance(model, ComponentTrajectoryModel):
        raise ValueError('Complete component trajectory model required')
    ids = model.report.get('source_vertex_ids', {})
    if not isinstance(vertices, dict) or set(vertices) != set(ids):
        raise ValueError('Every declared actual component required')
    arrays = {}
    for name, source in ids.items():
        p = np.asarray(vertices[name], float)
        if p.shape != (model.report['component_samples'], len(source), 3) or not np.isfinite(p).all():
            raise ValueError('Every finite actual trajectory sample required')
        arrays[name] = p
    values = np.empty_like(model.gaps_m)
    for frame, group in enumerate(model.groups):
        a,b = group['actors'];axis = np.array(group['axis_world'])
        values[group['first_row']:group['stop_row']] = (
            (arrays[a][frame,:,None]-arrays[b][frame,None,:])@axis).ravel()
    if not np.isfinite(values).all():
        raise ValueError('Finite complete actual trajectory gaps required')
    return values


def deficits(model, gaps_m):
    """Return one worst deficit per sample and clock-weighted diagnostic totals."""
    if not isinstance(model, ComponentTrajectoryModel):
        raise ValueError('Complete component trajectory model required')
    gaps = np.asarray(gaps_m, float)
    if gaps.shape != model.gaps_m.shape or not np.isfinite(gaps).all():
        raise ValueError('Complete finite gap observations required')
    worst = np.array([max(0., float(np.max(model.clearances_m[g['first_row']:g['stop_row']]
                   -gaps[g['first_row']:g['stop_row']]))) for g in model.groups])
    return dict(per_sample_m=worst, sum_m=float(worst.sum()),
                integral_m_s=float(worst@model.weights_s), maximum_m=float(worst.max()))
