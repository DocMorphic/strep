"""Sampled complete convex-component guards, distinct from full-mesh coverage.

Caller authenticates the source membership and same-point skin derivatives.
Positive fixed-axis rows constrain a local affine model only. Actual stored
points and the original full scene must still be checked.
"""
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from native_convex_component_support import support_pair


@dataclass
class ComponentSeparationGuards:
    gaps_m: np.ndarray
    jacobian: object
    clearances_m: np.ndarray
    descriptors: list
    groups: list
    report: dict


def build(vertices, point_jacobians, local_faces, source_vertex_ids, times_s,
          *, clearance_m=1e-8, maximum_groups=4096,
          maximum_guard_rows=400_000, maximum_elements=60_000_000):
    """Cover every ordered vertex pair at every supplied positive sample.

Exactly two complete source components, ordered increasing clocks and all
control columns are required. An invalid/nonpositive frame or budget overflow
rejects the entire model; no selected subset or full-mesh label is returned.
    """
    times = np.asarray(times_s, float)
    if (not isinstance(vertices, dict) or len(vertices) != 2
            or any(type(k) is not str or not k for k in vertices)
            or any(not isinstance(d, dict) or set(d) != set(vertices)
                   for d in (point_jacobians, local_faces, source_vertex_ids))
            or times.ndim != 1 or not len(times) or not np.isfinite(times).all()
            or np.any(times < 0) or np.any(np.diff(times) <= 0)
            or type(clearance_m) not in (int, float) or not np.isfinite(clearance_m)
            or not 1e-9 <= clearance_m <= .001
            or type(maximum_groups) is not int or not 1 <= maximum_groups <= 4096
            or type(maximum_guard_rows) is not int or not 1 <= maximum_guard_rows <= 400_000
            or type(maximum_elements) is not int or not 1 <= maximum_elements <= 60_000_000
            or len(times) > maximum_groups):
        raise ValueError('Explicit complete component population, clock and budgets required')
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
            raise ValueError('Finite complete source components and all derivative columns required')
        if controls is not None and controls != j.shape[3]:
            raise ValueError('Every component must use the same control columns')
        controls = j.shape[3]
        points[name], derivatives[name], ids[name], faces[name] = p, j, list(v), f
    a, b = list(vertices)
    total_rows = len(times)*len(ids[a])*len(ids[b])
    if (total_rows > maximum_guard_rows or total_rows*controls > maximum_elements
            or sum(j.size for j in derivatives.values()) > maximum_elements):
        raise ValueError('Complete component population exceeds budget; no subset returned')
    gaps, columns, clearances, descriptors, groups = [], [], [], [], []
    for frame, time in enumerate(times):
        axis, pair_gaps, support = support_pair(points[a][frame], faces[a], points[b][frame], faces[b])
        smallest = float(pair_gaps.min())
        if smallest <= 0:
            raise ValueError('Every declared component sample must start strictly positive')
        margin = min(clearance_m, smallest)
        first = len(gaps)
        for i, left in enumerate(ids[a]):
            for k, right in enumerate(ids[b]):
                column = axis@(derivatives[a][frame, i]-derivatives[b][frame, k])
                if not np.isfinite(column).all():
                    raise ValueError('Finite complete component guard derivative required')
                gaps.append(float(pair_gaps[i, k])); columns.append(column); clearances.append(margin)
                descriptors.append(dict(kind='component-separation-guard', group_index=frame,
                    time_s=float(time), actors=[a, b], left_vertex=left, right_vertex=right,
                    axis_world=axis.tolist(), clearance_m=margin))
        groups.append(dict(time_s=float(time), actors=[a, b], left_vertex_ids=ids[a].copy(),
            right_vertex_ids=ids[b].copy(), row_indices=list(range(first, len(gaps))),
            axis_world=axis.tolist(), starting_minimum_support_gap_m=smallest,
            clearance_m=margin, support_report=support))
    report = dict(schema='strep-native-component-separation-guards-v1', controls=controls,
        component_samples=len(times), guard_rows=len(gaps), times_s=times.tolist(),
        source_vertex_ids=ids, complete_component_pair_rows=True,
        full_mesh_pair_partition=False, continuous_coverage=False,
        requested_clearance_m=clearance_m, maximum_groups=maximum_groups,
        maximum_guard_rows=maximum_guard_rows, maximum_elements=maximum_elements,
        quality_approved=False, release_approved=False,
        scope='All ordered vertices of two supplied complete convex source components at every '
              'declared positive sample. Fixed-axis affine guards with capped positive margin; '
              'source completeness and derivative provenance remain caller obligations. '
              'No full-mesh, self/object, nonlinear/export or between-sample certificate.')
    return ComponentSeparationGuards(np.array(gaps), sparse.csr_matrix(np.array(columns)),
                                    np.array(clearances), descriptors, groups, report)


def observe(guards, vertices):
    """Measure the declared fixed-axis gaps on actual component points.

Does not choose new axes or approve other geometry. Caller binds exactly the
declared times, original source IDs and actual stored payloads.
    """
    if not isinstance(guards, ComponentSeparationGuards):
        raise ValueError('Separately typed component guard model required')
    ids = guards.report.get('source_vertex_ids', {})
    if not isinstance(vertices, dict) or set(vertices) != set(ids):
        raise ValueError('Every declared actual source component required')
    arrays = {}
    for name, source in ids.items():
        p = np.asarray(vertices[name], float)
        if p.shape != (guards.report['component_samples'], len(source), 3) or not np.isfinite(p).all():
            raise ValueError('Complete finite actual component points required')
        arrays[name] = p
    gaps = []
    for frame, group in enumerate(guards.groups):
        a, b = group['actors']; axis = np.array(group['axis_world'])
        gaps.extend(((arrays[a][frame, :, None]-arrays[b][frame, None, :])@axis).ravel())
    values = np.array(gaps)
    if values.shape != guards.gaps_m.shape or not np.isfinite(values).all():
        raise ValueError('Complete finite actual component guard observations required')
    return values
