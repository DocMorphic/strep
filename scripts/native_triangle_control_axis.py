"""Control-box-aware selection among finite triangle separation directions.

Optimistic independent-row maxima rank directions; they are not a simultaneous
feasibility test. Every selected direction still requires all nine vertex-pair
rows and complete decoded native/reference/geometry acceptance downstream.
Existing pose-only producers are unchanged.
"""
import numpy as np
from native_partner_surface_rows import separation_axis

SCHEMA = 'strep-native-triangle-control-axis-v1'


def candidate_axes(left, right):
    """Keep both orientations of the original finite edge/face axis family."""
    values = [np.asarray(v) for v in (left, right)]
    if any(v.shape != (3, 3) or v.dtype.kind not in 'fiu' for v in values):
        raise ValueError('Two complete finite real triangles required')
    left, right = [np.asarray(v, float) for v in values]
    if any(not np.isfinite(v).all() for v in (left, right)):
        raise ValueError('Two complete finite real triangles required')
    edges = [np.roll(t, -1, axis=0)-t for t in (left, right)]
    na, nb = [np.cross(e[0], e[1]) for e in edges]
    lengths = np.linalg.norm([na, nb], axis=1)
    if not np.isfinite(lengths).all() or min(lengths) <= 1e-16:
        raise ValueError('Nondegenerate finite triangle axis family required')
    raw = [na, nb]+[np.cross(a, b) for a in edges[0] for b in edges[1]]
    raw += [np.cross(na, e) for e in edges[0]]+[np.cross(nb, e) for e in edges[1]]
    axes = []
    for vector in raw:
        length = np.linalg.norm(vector)
        if not np.isfinite(length):
            raise ValueError('Finite triangle axis family required')
        if length > 1e-16:
            normal = vector/length
            axes.extend((normal, -normal))
    return np.array(axes)


def choose(left, right, left_jacobian, right_jacobian, delta_lower, delta_upper, *, baseline_normal=None):
    """Choose the greatest optimistic minimum over all nine scalar rows.

    For each direction, maximize each row independently over the full supplied
    box, then take the minimum of those maxima. This is a mathematical upper
    bound on simultaneous affine separation; floating scoring is heuristic,
    not an outward/exact certificate. Original native constraints are ignored.
    Prefer the pose-only direction on exact ties with equal current gap.
    """
    axes = candidate_axes(left, right)
    if baseline_normal is not None:
        supplied=np.asarray(baseline_normal)
        if supplied.shape!=(3,) or supplied.dtype.kind not in 'fiu':
            raise ValueError('Explicit finite unit baseline normal required')
        supplied=np.asarray(supplied,float)
        if not np.isfinite(supplied).all() or abs(np.linalg.norm(supplied)-1)>1e-10:
            raise ValueError('Explicit finite unit baseline normal required')
        if not np.any(np.all(axes==supplied,axis=1)):
            axes=np.vstack([axes,supplied,-supplied])
    values = [np.asarray(v) for v in (left_jacobian, right_jacobian, delta_lower, delta_upper)]
    if any(v.dtype.kind not in 'fiu' for v in values):
        raise ValueError('Complete real vertex derivatives and delta box required')
    jl, jr, lower, upper = [np.asarray(v, float) for v in values]
    if (lower.ndim != 1 or not 1 <= len(lower) <= 96 or upper.shape != lower.shape
            or jl.shape != (3, 3, len(lower)) or jr.shape != jl.shape
            or any(not np.isfinite(v).all() for v in (jl, jr, lower, upper))
            or np.any(lower > 0) or np.any(upper < 0) or np.any(lower > upper)):
        raise ValueError('Complete finite vertex derivatives and zero-containing delta box required')
    left, right = np.asarray(left, float), np.asarray(right, float)
    with np.errstate(over='ignore', invalid='ignore'):
        gaps = ((left@axes.T).T[:, :, None]-(right@axes.T).T[:, None, :]).reshape(len(axes), 9)
        derivatives = np.einsum('ak,ijkc->aijc', axes, jl[:, None]-jr[None, :]).reshape(len(axes), 9, len(lower))
        maxima = gaps+np.maximum(derivatives, 0)@upper+np.minimum(derivatives, 0)@lower
    if any(not np.isfinite(v).all() for v in (gaps, derivatives, maxima)):
        raise ValueError('Finite complete axis scores required; no partial selection returned')
    current = gaps.min(axis=1); optimistic = maxima.min(axis=1)
    normal, pose_gap = separation_axis(left, right)
    if baseline_normal is not None:
        normal=supplied;pose_gap=float((left@normal).min()-(right@normal).max())
    matches = np.flatnonzero(np.all(axes == normal, axis=1))
    if not len(matches):
        raise ValueError('Original pose-only axis must remain in the complete family')
    baseline = selected = int(matches[0])
    for index in range(len(axes)):
        if (optimistic[index] > optimistic[selected]
                or (optimistic[index] == optimistic[selected] and current[index] > current[selected])):
            selected = index
    return axes[selected].copy(), dict(schema=SCHEMA, candidate_directions=len(axes),
        baseline_index=baseline, selected_index=selected, changed_direction=bool(selected != baseline),
        baseline_gap_m=float(pose_gap), selected_gap_m=float(current[selected]), explicit_baseline_retained=baseline_normal is not None,
        baseline_optimistic_gap_m=float(optimistic[baseline]), selected_optimistic_gap_m=float(optimistic[selected]),
        all_nine_pairs_scored_per_direction=True, all_controls_scored=True,
        native_constraints_ignored=True, simultaneous_affine_feasibility_proven=False,
        nonlinear_geometry_infeasibility_proven=False, quality_approved=False, release_approved=False,
        scope='Finite face/edge axis family with both orientations and any explicitly supplied original baseline normal, ranked by optimistic independent-row box maxima. '
              'Floating scores are heuristic, not exact/outward certificates or a joint affine/native feasibility test. '
              'Retain all nine selected-axis rows and full decoded native/reference/geometry checks. '
              'This does not search every possible direction, control path or authored range.')
