"""Complete affine mesh-pair separation guards within an explicit control box.

These preserve starting positive fixed-axis support gaps; they do not resolve
existing crossings or certify actual nonlinear/exported geometry.
"""
from dataclasses import dataclass
from itertools import combinations
import numpy as np
from scipy import sparse
from native_partner_surface_rows import separation_axis


def coordinate_bounds(points, jacobian, lower_step, upper_step):
    """Outward rounded bounds on the represented affine point model.

    Each product and accumulated sum rounds outward. This encloses exact real
    arithmetic on these Float64 inputs, not a nonlinear skinning trajectory.
    """
    low = np.zeros_like(points); high = np.zeros_like(points)
    for c in range(len(lower_step)):
        j = jacobian[..., c]
        a = j*np.where(j >= 0, lower_step[c], upper_step[c])
        b = j*np.where(j >= 0, upper_step[c], lower_step[c])
        low = np.nextafter(low+np.nextafter(a, -np.inf), -np.inf)
        high = np.nextafter(high+np.nextafter(b, np.inf), np.inf)
    low = np.nextafter(points+low, -np.inf)
    high = np.nextafter(points+high, np.inf)
    if not np.isfinite(low).all() or not np.isfinite(high).all():
        raise ValueError('Finite complete outward affine point bounds required')
    return low, high


@dataclass
class SeparationGuards:
    gaps_m: np.ndarray
    jacobian: object
    clearances_m: np.ndarray
    descriptors: list
    report: dict


def build(vertices, point_jacobians, triangles, times_s, value, lower, upper, trust,
          *, clearance_m=1e-8, maximum_triangle_pairs=1_000_000,
          maximum_guard_rows=400_000, maximum_elements=60_000_000):
    """Caller binds complete original meshes/clocks/point derivatives and box.

    Every unordered actor/triangle/time pair is either outside outward whole-
    box coordinate bounds, given all nine starting separation rows, or recorded
    unresolved. No selected body patch or prior crossing list defines coverage.
    """
    value, lower, upper, times = [np.asarray(a, float) for a in (value, lower, upper, times_s)]
    n = len(value) if value.ndim == 1 else 0
    if (not 1 <= n <= 96 or lower.shape != value.shape or upper.shape != value.shape
            or times.ndim != 1 or not 1 <= len(times) <= 10000
            or any(not np.isfinite(a).all() for a in (value, lower, upper, times))
            or np.any(times < 0) or np.any(np.diff(times) <= 0) or np.any(lower >= upper)
            or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or type(clearance_m) not in (int, float) or not np.isfinite(clearance_m) or not 1e-9 <= clearance_m <= .001
            or not isinstance(vertices, dict) or not 2 <= len(vertices) <= 8
            or not isinstance(point_jacobians, dict) or not isinstance(triangles, dict)
            or set(vertices) != set(point_jacobians) or set(vertices) != set(triangles)
            or any(type(k) is not str or not k for k in vertices)
            or type(maximum_triangle_pairs) is not int or not 1 <= maximum_triangle_pairs <= 1_000_000
            or type(maximum_guard_rows) is not int or not 1 <= maximum_guard_rows <= 400_000
            or type(maximum_elements) is not int or not 1 <= maximum_elements <= 60_000_000):
        raise ValueError('Complete actor meshes, finite original bounds, clock and explicit budgets required')
    points, derivatives, faces = {}, {}, {}
    for name in vertices:
        p, j, f = np.asarray(vertices[name], float), np.asarray(point_jacobians[name], float), np.asarray(triangles[name])
        if (p.ndim != 3 or p.shape[0] != len(times) or p.shape[2] != 3 or p.shape[1] < 3
                or j.shape != (*p.shape, n) or f.ndim != 2 or f.shape[1] != 3 or not len(f)
                or not np.issubdtype(f.dtype, np.integer) or f.min() < 0 or f.max() >= p.shape[1]
                or np.any(np.diff(np.sort(f, axis=1), axis=1) == 0)
                or not np.isfinite(p).all() or not np.isfinite(j).all()):
            raise ValueError('Complete finite indexed triangle points and all control columns required')
        points[name], derivatives[name], faces[name] = p, j, f.astype(np.int64, copy=True)
    pairs = list(combinations(points, 2))
    complete_pairs = len(times)*sum(len(faces[a])*len(faces[b]) for a, b in pairs)
    if complete_pairs > maximum_triangle_pairs or sum(j.size for j in derivatives.values()) > maximum_elements:
        raise ValueError('Complete mesh-pair/point population exceeds its explicit resource budget')
    lo, hi = np.maximum(-trust, lower-value), np.minimum(trust, upper-value)
    bounds = {name: coordinate_bounds(p, derivatives[name], lo, hi) for name, p in points.items()}
    for name, p in points.items():
        t = p[:, faces[name]]
        area = np.linalg.norm(np.cross(t[:, :, 1]-t[:, :, 0], t[:, :, 2]-t[:, :, 0]), axis=-1)
        if not np.isfinite(area).all() or np.any(area <= 1e-16):
            raise ValueError('Every original anchor triangle must be nondegenerate')
    gaps, columns, clearances, descriptors, frames = [], [], [], [], []
    for frame, time in enumerate(times):
        for a, b in pairs:
            left_lo, left_hi = [bound[frame, faces[a]].min(axis=1) if i == 0 else bound[frame, faces[a]].max(axis=1)
                                for i, bound in enumerate(bounds[a])]
            right_lo, right_hi = [bound[frame, faces[b]].min(axis=1) if i == 0 else bound[frame, faces[b]].max(axis=1)
                                  for i, bound in enumerate(bounds[b])]
            disjoint = np.any((np.nextafter(left_hi[:, None]+clearance_m, np.inf) < right_lo[None]) |
                              (np.nextafter(right_hi[None]+clearance_m, np.inf) < left_lo[:, None]), axis=-1)
            candidates = np.argwhere(~disjoint)
            unresolved, separated = [], 0
            for fa, fb in candidates:
                va, vb = faces[a][fa], faces[b][fb]
                axis, _ = separation_axis(points[a][frame, va], points[b][frame, vb])
                values = np.array([float((points[a][frame, av]-points[b][frame, bv])@axis) for av in va for bv in vb])
                smallest = float(values.min())
                if not np.isfinite(values).all() or not np.isfinite(axis).all():
                    raise ValueError('Finite complete separation rows required')
                if smallest <= 0:
                    unresolved.append(dict(left_triangle=int(fa), right_triangle=int(fb), support_gap_m=smallest))
                    continue
                if len(gaps)+9 > maximum_guard_rows or (len(gaps)+9)*n > maximum_elements:
                    raise ValueError('Complete separated pair guards exceed their budget; no subset returned')
                margin = min(clearance_m, smallest)
                for k, (av, bv) in enumerate((av, bv) for av in va for bv in vb):
                    derivative = axis@(derivatives[a][frame, av]-derivatives[b][frame, bv])
                    if not np.isfinite(derivative).all():
                        raise ValueError('Finite complete guard derivative required')
                    gaps.append(values[k]); columns.append(derivative); clearances.append(margin)
                    descriptors.append(dict(time_s=float(time), actors=[a, b], left_triangle=int(fa), right_triangle=int(fb),
                        left_vertex=int(av), right_vertex=int(bv), axis_world=axis.tolist(), clearance_m=margin,
                        starting_minimum_support_gap_m=smallest))
                separated += 1
            frames.append(dict(time_s=float(time), actors=[a, b], triangle_pairs=int(disjoint.size),
                whole_box_disjoint_pairs=int(disjoint.sum()), candidate_pairs=len(candidates),
                positively_separated_pairs=separated, unresolved_pairs=unresolved))
    report = dict(schema='strep-native-triangle-separation-guards-v1', complete_triangle_pairs=complete_pairs,
        guard_rows=len(gaps), controls=n, frames=frames,
        maximum_triangle_pairs=maximum_triangle_pairs, maximum_guard_rows=maximum_guard_rows,
        maximum_elements=maximum_elements, requested_clearance_m=clearance_m,
        original_control_trust_box_retained=True, all_original_point_columns_retained=True,
        complete_pair_partition=True, outward_affine_coordinate_bounds=True,
        source_vertices={k:p.shape[1] for k,p in points.items()}, source_triangles={k:len(f) for k,f in faces.items()},
        quality_approved=False, release_approved=False,
        scope='Complete declared-time original inter-actor triangle population partitioned under outward bounds '
              'of the represented affine skin-point model. Every positive candidate separation gets all nine rows. '
              'Each positive margin is the requested clearance capped by the exact represented anchor minimum. '
              'Unresolved pairs are retained explicitly, not certified disjoint. No self/object/continuous collision '
              'or nonlinear nonregression claim. Actual stored motion and full scene checks remain required.')
    return SeparationGuards(np.array(gaps), sparse.csr_matrix(np.array(columns).reshape(-1, n)),
                            np.array(clearances), descriptors, report)
