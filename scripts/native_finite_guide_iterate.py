"""Inspect a returned conic iterate without changing its solver status.

This explicit diagnostic path can propose actual-export checks, never approval.
Infeasibility certificates and numerical-error results are not motion iterates.
"""
import numpy as np
from scipy import sparse
from native_affine_ray_retreat import project


ITERATE_STATUSES = ('Solved', 'AlmostSolved', 'InsufficientProgress', 'MaxIterations', 'MaxTime')


def assess(native, native_jacobian, guide_residual, guide_jacobian,
           value, lower, upper, trust, *, solver_status, solver_point, parameter_rows=None):
    """Validate all original affine bounds for an explicitly supplied iterate.

    ``solver_point`` is the original solution.x: normalized controls followed
    by all guide slacks. Caller binds its solver, unchanged model and inputs.
    This function neither solves nor substitutes Solved for a stalled status.
    """
    value, lower, upper = [np.asarray(v, float) for v in (value, lower, upper)]
    vectors, caps, scales = [np.asarray(v, float) for v in (native.vectors, native.caps, native.scales)]
    residual = np.asarray(guide_residual, float)
    n = len(value) if value.ndim == 1 else 0
    nj, gj = [sparse.csr_matrix(j, copy=True) for j in (native_jacobian, guide_jacobian)]
    eq = sparse.csr_matrix((0, n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows, copy=True)
    if (not 1 <= n <= 96 or lower.shape != value.shape or upper.shape != value.shape
            or vectors.ndim != 2 or vectors.shape[1:] != (3,) or not len(vectors)
            or caps.shape != (len(vectors),) or scales.shape != caps.shape
            or nj.shape != (vectors.size, n) or residual.ndim != 1 or not 1 <= len(residual) <= 4096
            or gj.shape != (len(residual), n) or eq.shape[1] != n or eq.shape[0] > 96
            or any(not np.isfinite(v).all() for v in (value, lower, upper, vectors, caps, scales, residual, nj.data, gj.data, eq.data))
            or np.any(caps < 0) or np.any(scales <= 0) or np.any(lower >= upper)
            or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or type(solver_status) is not str):
        raise ValueError('Complete finite original affine model, controls, bounds and explicit solver status required')
    before = np.minimum(residual, 0.)
    anchor = (np.linalg.norm(vectors, axis=1)-caps)/scales
    info = dict(schema='strep-native-finite-guide-iterate-v1', status='not-assessed',
        solver_status=solver_status, solver_status_preserved=True, solver_optimality_verified=False,
        original_norm_rows=len(caps), guide_scalar_rows=len(residual), parameter_rows=eq.shape[0],
        all_original_rows_columns_caps_scales_retained=True, original_anchor_maximum_excess=float(anchor.max()),
        guide_squared_error_before=float(before@before), raw_control_step=None, selected_control_step=None,
        diagnostic_only=True, actual_export_required=True, quality_approved=False, release_approved=False,
        scope='Finite solver output inspected against the complete unchanged affine model. '
              'Strict original norm/trust ray validation and separate homogeneous parameter checks. '
              'No infeasibility or optimality conclusion; no stored-motion/contact/geometry, engine or quality approval.')
    if solver_status not in ITERATE_STATUSES:
        return None, dict(info, status='NotMotionIterateStatus')
    if np.any(anchor > 0):
        return None, dict(info, status='OriginalAnchorNotStrictlyPassing')
    try:
        point = np.asarray(solver_point, float)
    except (TypeError, ValueError):
        return None, dict(info, status='InvalidReturnedPoint')
    if point.shape != (n+len(residual),) or not np.isfinite(point).all():
        return None, dict(info, status='InvalidReturnedPoint')
    raw, slack = point[:n]*trust, point[n:]
    gap = residual+gj@raw
    native_excess = (np.linalg.norm(vectors+(nj@raw).reshape(vectors.shape), axis=1)-caps)/scales
    lo, hi = np.maximum(-trust, lower-value), np.minimum(trust, upper-value)
    slack_excess = float(max((-slack).max(), (-gap-slack).max()))
    info.update(raw_control_step=raw.tolist(), raw_guide_slacks=slack.tolist(),
        raw_original_native_maximum_excess=float(native_excess.max()),
        raw_original_native_failed_rows=int((native_excess > 0).sum()),
        raw_parameter_maximum_absolute_residual=float(np.abs(eq@raw).max()) if eq.shape[0] else 0.,
        raw_guide_slack_constraint_maximum_excess=slack_excess,
        proposal_box_tolerance=1e-9, proposal_slack_tolerance=1e-9,
        parameter_row_proposal_tolerance=1e-9)
    if np.any(raw < lo-1e-9) or np.any(raw > hi+1e-9):
        return None, dict(info, status='IterateOutsideOriginalProposalBox')
    if slack_excess > 1e-9:
        return None, dict(info, status='UnverifiedReturnedGuideSlacks')
    delta, ray = project(native, nj, raw, value, lower, upper, trust)
    info['strict_original_norm_ray'] = ray
    if delta is None:
        return None, dict(info, status='NoStrictPositiveIterateRay')
    parameter_error = float(np.abs(eq@delta).max()) if eq.shape[0] else 0.
    deficit = np.minimum(residual+gj@delta, 0.)
    after = float(deficit@deficit)
    info.update(selected_control_step=delta.tolist(), parameter_row_maximum_absolute_residual=parameter_error,
        guide_squared_error_after=after, selected_original_native_maximum_excess=ray['selected_native_maximum_excess'])
    if parameter_error > 1e-9:
        return None, dict(info, status='UnverifiedParameterRows')
    if not after < info['guide_squared_error_before']:
        return None, dict(info, status='NoStrictGuideImprovement')
    return delta, dict(info, status='ProvisionalStrictAffineIterate', recovered_ray_not_solver_optimum=True)
