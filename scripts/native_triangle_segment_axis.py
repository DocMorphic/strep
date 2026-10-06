"""Rank complete triangle directions on a common affine control segment.

Each direction uses all nine vertex-pair lines and one common segment fraction.
The caller must check both native endpoints. This ranking does not prove that
all triangles share an optimum or certify nonlinear geometry. Solver controls,
original native conditions and decoded acceptance remain unchanged downstream.
"""
import numpy as np
from native_triangle_control_axis import candidate_axes
from native_partner_surface_rows import separation_axis

SCHEMA = 'strep-native-triangle-segment-axis-v1'
_PAIRS = np.array([(a, b) for a in range(9) for b in range(a+1, 9)])


def segment_scores(gaps, slopes):
    """Maximize the minimum of nine lines on [0,1], for every supplied axis.

    Endpoints and all pairwise line crossings suffice for this concave,
    piecewise-linear objective. Floating values are guidance, not exact bounds.
    An exact score tie prefers the smallest fraction in the finite population.
    """
    values = [np.asarray(v) for v in (gaps, slopes)]
    if any(v.dtype.kind not in 'fiu' for v in values):
        raise ValueError('Complete finite real nine-line populations required')
    gaps, slopes = [np.asarray(v, float) for v in values]
    if (gaps.ndim != 2 or not 1 <= len(gaps) <= 36 or gaps.shape[1] != 9
            or slopes.shape != gaps.shape or not np.isfinite([gaps, slopes]).all()):
        raise ValueError('Complete finite real nine-line populations required')
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        denominator = slopes[:, _PAIRS[:, 0]]-slopes[:, _PAIRS[:, 1]]
        numerator = gaps[:, _PAIRS[:, 1]]-gaps[:, _PAIRS[:, 0]]
        if not np.isfinite([denominator, numerator]).all():
            raise ValueError('Finite complete segment arithmetic required')
        crossing = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator != 0)
        crossing = np.where((crossing >= 0) & (crossing <= 1), crossing, 0.)
        fractions = np.c_[np.zeros(len(gaps)), np.ones(len(gaps)), crossing]
        values = gaps[:, None, :]+fractions[:, :, None]*slopes[:, None, :]
    if not np.isfinite(values).all():
        raise ValueError('Finite complete segment scores required; no partial selection')
    minimum = values.min(axis=2)
    scores = minimum.max(axis=1)
    fraction = np.where(minimum == scores[:, None], fractions, np.inf).min(axis=1)
    return scores, fraction


def choose(left, right, left_jacobian, right_jacobian, direction, *, baseline_normal=None):
    """Choose among the original finite family and both baseline orientations.

    The same complete control direction drives all vertices and all nine pairs.
    A triangle may rank a different fraction than another triangle; this is not
    a simultaneous full-system feasibility test. Retain all nine rows afterward.
    """
    axes = candidate_axes(left, right)
    left, right = np.asarray(left, float), np.asarray(right, float)
    baseline, _ = separation_axis(left, right)
    if baseline_normal is not None:
        raw = np.asarray(baseline_normal)
        if raw.shape != (3,) or raw.dtype.kind not in 'fiu':
            raise ValueError('Finite explicit unit baseline normal required')
        baseline = np.asarray(raw, float)
        if not np.isfinite(baseline).all() or abs(np.linalg.norm(baseline)-1) > 1e-10:
            raise ValueError('Finite explicit unit baseline normal required')
    if not np.any(np.all(axes == baseline, axis=1)):
        axes = np.vstack([axes, baseline, -baseline])
    values = [np.asarray(v) for v in (left_jacobian, right_jacobian, direction)]
    if any(v.dtype.kind not in 'fiu' for v in values):
        raise ValueError('Complete real vertex derivatives and common direction required')
    jl, jr, step = [np.asarray(v, float) for v in values]
    if (step.ndim != 1 or not 1 <= len(step) <= 96
            or jl.shape != (3, 3, len(step)) or jr.shape != jl.shape
            or any(not np.isfinite(v).all() for v in (jl, jr, step))):
        raise ValueError('Complete finite vertex derivatives and common direction required')
    with np.errstate(over='ignore', invalid='ignore'):
        gaps = ((left@axes.T).T[:, :, None]-(right@axes.T).T[:, None, :]).reshape(len(axes), 9)
        motion = np.einsum('vkc,c->vk', jl, step)[:, None]-np.einsum('vkc,c->vk', jr, step)[None, :]
        slopes = np.einsum('ak,ijk->aij', axes, motion).reshape(len(axes), 9)
    scores, fractions = segment_scores(gaps, slopes)
    current = gaps.min(axis=1)
    original = selected = int(np.flatnonzero(np.all(axes == baseline, axis=1))[0])
    for index in range(len(axes)):
        if scores[index] > scores[selected] or (scores[index] == scores[selected] and current[index] > current[selected]):
            selected = index
    return axes[selected].copy(), dict(schema=SCHEMA, candidate_directions=len(axes),
        baseline_index=original, selected_index=selected, changed_direction=bool(selected != original),
        baseline_gap_m=float(current[original]), selected_gap_m=float(current[selected]),
        baseline_joint_segment_gap_m=float(scores[original]), selected_joint_segment_gap_m=float(scores[selected]),
        baseline_fraction=float(fractions[original]), selected_fraction=float(fractions[selected]),
        all_nine_pairs_scored_per_direction=True, all_controls_scored=True,
        common_fraction_per_triangle=True, native_segment_endpoints_checked=False,
        simultaneous_affine_feasibility_proven=False, nonlinear_geometry_infeasibility_proven=False,
        quality_approved=False, release_approved=False,
        scope='Complete finite face/edge family and both orientations, plus the supplied original baseline. '
              'Each triangle ranks the minimum of all nine lines at one common fraction of an explicit shared direction. '
              'Caller must verify original native endpoints; different triangles may prefer different fractions. '
              'No full-system, other-path, authored-range or nonlinear geometry feasibility certificate.')
