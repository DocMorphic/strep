"""Fit explicit affine pose guidance under every original native vector norm.

Optional homogeneous rows preserve native key-parameter contributions only.
Neither affine norm pass nor parameter preservation proves an exported pose,
contact, source rate, collision result, or animator-quality improvement.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_affine_ray_retreat import project


def direction(native, native_jacobian, guide_residual, guide_jacobian,
              value, lower, upper, trust, *, parameter_rows=None):
    value, lower, upper = [np.asarray(v, float) for v in (value, lower, upper)]
    residual = np.asarray(guide_residual, float)
    vectors, caps, scales = [np.asarray(v, float) for v in (native.vectors, native.caps, native.scales)]
    n = len(value) if value.ndim == 1 else 0
    nj = sparse.csr_matrix(native_jacobian, copy=True)
    gj = sparse.csr_matrix(guide_jacobian, copy=True)
    eq = sparse.csr_matrix((0, n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows, copy=True)
    if (not 1 <= n <= 96 or lower.shape != value.shape or upper.shape != value.shape
            or vectors.ndim != 2 or vectors.shape[1:] != (3,) or not len(vectors)
            or caps.shape != (len(vectors),) or scales.shape != caps.shape
            or nj.shape != (vectors.size, n) or residual.ndim != 1 or not 1 <= len(residual) <= 200000
            or gj.shape != (len(residual), n) or eq.shape[1] != n or eq.shape[0] > 96
            or any(not np.isfinite(v).all() for v in (value, lower, upper, vectors, caps, scales, residual, nj.data, gj.data, eq.data))
            or np.any(caps < 0) or np.any(scales <= 0) or np.any(lower >= upper)
            or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not 1e-6 <= trust <= .02):
        raise ValueError('Complete finite original norms, explicit guidance, ordered controls and bounded trust required')
    nj.eliminate_zeros(); eq.eliminate_zeros()
    anchor = (np.linalg.norm(vectors, axis=1)-caps)/scales
    info = dict(schema='strep-native-norm-guided-step-v1', status='not-solved', original_norm_rows=len(caps),
                guide_scalar_rows=len(residual), parameter_rows=eq.shape[0], original_anchor_maximum_excess=float(anchor.max()),
                all_original_caps_scales_unchanged=True, original_norms_always_hard=True,
                guide_squared_error_before=float(residual@residual), quality_approved=False, release_approved=False,
                scope='Quadratic affine guidance with complete original hard norm rows and optional homogeneous key-parameter rows. '
                      'A finite ray requires strict represented original norm and trust-box pass. Parameter rows are checked with a 1e-9 proposal tolerance only; original exported contact limits are never replaced. '
                      'No solver optimality, nonlinear/native export, collision, engine or animation-quality approval.')
    if np.any(anchor > 0):
        return None, dict(info, status='OriginalAnchorNotStrictlyPassing')
    solver = solver_module()
    lo, hi = np.maximum(-1., (lower-value)/trust), np.minimum(1., (upper-value)/trust)
    mats = [sparse.eye(n, format='csc'), -sparse.eye(n, format='csc')]
    rhs = [hi, -lo]; cones = [solver.NonnegativeConeT(2*n)]
    if eq.shape[0]:
        mats.append(eq.multiply(trust).tocsc()); rhs.append(np.zeros(eq.shape[0])); cones.append(solver.ZeroConeT(eq.shape[0]))
    counts = np.diff(nj.indptr).reshape(-1, 3).sum(axis=1)
    active = np.flatnonzero(counts != 0)
    if len(active):
        rows = (3*active[:, None]+np.arange(3)).ravel()
        selected = nj[rows].multiply((-trust/np.repeat(scales[active], 3))[:, None]).tocoo()
        matrix = sparse.csc_matrix((selected.data, (4*(selected.row//3)+1+selected.row%3, selected.col)),
                                   shape=(4*len(active), n))
        mats.append(matrix); rhs.append((np.c_[caps[active], vectors[active]]/scales[active, None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in active)
    # Only exactly zero-Jacobian passing rows are omitted; no approximate
    # derivative threshold, actor/time selection or affine-box pruning.
    h = gj.multiply(trust).tocsc()
    regularization = 1e-12
    quadratic = sparse.triu(h.T@h + regularization*sparse.eye(n), format='csc')
    linear = np.asarray(h.T@residual).ravel()
    settings = solver.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_feas = settings.tol_gap_abs = settings.tol_gap_rel = 1e-11
    if hasattr(settings, 'max_threads'):
        settings.max_threads = 1
    solution = solver.DefaultSolver(quadratic, linear, sparse.vstack(mats, format='csc'), np.concatenate(rhs), cones, settings).solve()
    info.update(solver_status=str(solution.status), solver_iterations=solution.iterations,
                solver_version=solver.__version__, active_original_norm_cones=len(active),
                omitted_exactly_fixed_passing_norms=int((counts == 0).sum()), normalized_step_regularization=regularization,
                requested_solver_tolerance=1e-11)
    point = np.asarray(solution.x, float)
    if (str(solution.status) not in ('Solved', 'AlmostSolved')
            or point.shape != value.shape or not np.isfinite(point).all()):
        return None, dict(info, status='NoFiniteSolverCandidate')
    raw = point*trust
    info['raw_control_step'] = raw.tolist()
    # Solver status alone cannot make an invalid proposal acceptable. Retain
    # finite failures before calling the independently strict ray validator.
    step_lower = np.maximum(-trust, lower-value)
    step_upper = np.minimum(trust, upper-value)
    if np.any(raw < step_lower-1e-9) or np.any(raw > step_upper+1e-9):
        return None, dict(info, status='SolverCandidateOutsideProposalBox',
                          proposal_box_tolerance=1e-9)
    delta, ray = project(native, nj, raw, value, lower, upper, trust)
    info['strict_original_norm_ray'] = ray
    if delta is None:
        return None, dict(info, status='NoStrictFiniteRayCandidate')
    parameter_error = float(np.abs(eq@delta).max()) if eq.shape[0] else 0.
    error = residual + gj@delta
    after = float(error@error)
    info.update(parameter_row_maximum_absolute_residual=parameter_error,
                parameter_row_proposal_tolerance=1e-9, guide_squared_error_after=after,
                selected_control_step=delta.tolist(), selected_original_native_maximum_excess=ray['selected_native_maximum_excess'])
    if parameter_error > 1e-9:
        return None, dict(info, status='UnverifiedParameterRows')
    if not after < info['guide_squared_error_before']:
        return None, dict(info, status='NoStrictGuideImprovement')
    return delta, dict(info, status='VerifiedAffineGuideCandidate', recovered_ray_not_solver_optimum=True)
