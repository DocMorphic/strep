"""Reduce worst declared triangle support deficit without buying deeper vertices.

Frozen axes and material points are local guidance, not collision certificates.
The caller must supply and authenticate every row of its same-point model.
"""
import copy
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_affine_ray_retreat import project


def direction(native, native_jacobian, gaps_m, gap_jacobian, witnesses,
              value, lower, upper, trust, *, parameter_rows=None,
              clearance_m=.0001, scale_m=.005, solver_sink=None):
    """Minimize the worst triangle gap deficit, keeping containment depth hard.

    Every declared triangle corner-pair contributes to a single maximum rather
    than gaining extra objective weight through repetition. All containment
    witnesses are constrained by the starting worst depth. A strictly checked
    finite iterate is provisional; original exported scene checks still decide.
    """
    value, lower, upper, gaps = [np.asarray(a, float) for a in (value, lower, upper, gaps_m)]
    vectors, caps, scales = [np.asarray(a, float) for a in (native.vectors, native.caps, native.scales)]
    n = len(value) if value.ndim == 1 else 0
    nj, gj = [sparse.csr_matrix(a, copy=True) for a in (native_jacobian, gap_jacobian)]
    eq = sparse.csr_matrix((0, n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows, copy=True)
    if (not 1 <= n <= 96 or lower.shape != value.shape or upper.shape != value.shape
            or vectors.ndim != 2 or vectors.shape[1:] != (3,) or not len(vectors)
            or caps.shape != (len(vectors),) or scales.shape != caps.shape or nj.shape != (vectors.size, n)
            or gaps.ndim != 1 or not 1 <= len(gaps) <= 4096 or gj.shape != (len(gaps), n)
            or eq.shape[1] != n or eq.shape[0] > 96 or nj.nnz + gj.nnz + eq.nnz > 60_000_000
            or not isinstance(witnesses, list) or len(witnesses) != len(gaps)
            or any(not isinstance(w, dict) or w.get('kind') not in ('triangle-separation', 'penetrating-vertex') for w in witnesses)
            or any(not np.isfinite(a).all() for a in (value, lower, upper, vectors, caps, scales, gaps, nj.data, gj.data, eq.data))
            or np.any(caps < 0) or np.any(scales <= 0) or np.any(lower >= upper)
            or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or type(clearance_m) not in (int, float) or not np.isfinite(clearance_m) or not 0 <= clearance_m <= .1
            or type(scale_m) not in (int, float) or not np.isfinite(scale_m) or not 1e-6 <= scale_m <= 1.
            or solver_sink is not None and not callable(solver_sink)):
        raise ValueError('Complete finite native/material model, witnesses, ordered bounds and settings required')
    triangle = np.array([i for i, w in enumerate(witnesses) if w['kind'] == 'triangle-separation'], int)
    inside = np.array([i for i, w in enumerate(witnesses) if w['kind'] == 'penetrating-vertex'], int)
    if len(inside) and np.any(gaps[inside] > 0):
        raise ValueError('Every declared containment witness needs a nonpositive anchor gap')
    depth = float(max(0., (-gaps[inside]).max())) if len(inside) else 0.
    before = float(max(0., (clearance_m - gaps[triangle]).max())) if len(triangle) else 0.
    anchor = float(((np.linalg.norm(vectors, axis=1) - caps) / scales).max())
    info = dict(schema='strep-native-material-crossing-step-v1', status='not-solved',
        original_norm_rows=len(caps), controls=n, complete_guide_rows=len(gaps),
        triangle_rows=triangle.tolist(), containment_rows=inside.tolist(), parameter_rows=eq.shape[0],
        witnesses=copy.deepcopy(witnesses), original_anchor_maximum_excess=anchor,
        initial_worst_triangle_deficit_m=before, original_material_depth_ceiling_m=depth,
        clearance_m=clearance_m, scale_m=scale_m, original_caps_scales_clocks_unchanged=True,
        all_original_native_rows_columns_retained=True, all_guide_rows_retained=True,
        strict_native_acceptance_tolerance=0., strict_material_depth_tolerance_m=0.,
        parameter_proposal_tolerance=1e-9, solver_statuses_preserved=True,
        solver_optimality_verified=False, quality_approved=False, release_approved=False,
        scope='Worst complete fixed-axis triangle support deficit with all original hard native norms '
              'and starting material vertex-depth ceiling. Repeated rows receive no added objective weight. '
              'Strict represented checks do not prove nonlinear nonregression, mesh separation or contact. '
              'Caller authenticates complete witnesses and same-point derivatives. Actual stored motion, '
              'contacts, references and complete scene geometry remain required.')
    if anchor > 0:
        return None, dict(info, status='OriginalAnchorNotStrictlyPassing')
    if not len(triangle) or before == 0.:
        return None, dict(info, status='NoTriangleDeficit')
    solver = solver_module()
    nj.eliminate_zeros()
    counts = np.diff(nj.indptr).reshape(-1, 3).sum(axis=1)
    active = np.flatnonzero(counts != 0)
    lo, hi = np.maximum(-1., (lower-value)/trust), np.minimum(1., (upper-value)/trust)
    total = n + 1
    box = sparse.hstack([sparse.eye(n), sparse.csc_matrix((n, 1))], format='csc')
    mats, rhs = [box, -box], [hi, -lo]
    cones = [solver.NonnegativeConeT(2*n)]
    if eq.shape[0]:
        mats.append(sparse.hstack([eq*trust, sparse.csc_matrix((eq.shape[0], 1))], format='csc'))
        rhs.append(np.zeros(eq.shape[0])); cones.append(solver.ZeroConeT(eq.shape[0]))
    if len(active):
        selected = nj[(3*active[:, None]+np.arange(3)).ravel()].multiply(
            (-trust/np.repeat(scales[active], 3))[:, None]).tocoo()
        mats.append(sparse.csc_matrix((selected.data,
            (4*(selected.row//3)+1+selected.row%3, selected.col)), shape=(4*len(active), total)))
        rhs.append((np.c_[caps[active], vectors[active]]/scales[active, None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in active)
    if len(inside):
        mats.append(sparse.hstack([-trust/scale_m*gj[inside], sparse.csc_matrix((len(inside), 1))], format='csc'))
        rhs.append((gaps[inside]+depth)/scale_m); cones.append(solver.NonnegativeConeT(len(inside)))
    mats.append(sparse.hstack([-trust/scale_m*gj[triangle], -np.ones((len(triangle), 1))], format='csc'))
    rhs.append((gaps[triangle]-clearance_m)/scale_m); cones.append(solver.NonnegativeConeT(len(triangle)))
    mats.append(sparse.csc_matrix(np.r_[np.zeros(n), -1.][None]))
    rhs.append(np.zeros(1)); cones.append(solver.NonnegativeConeT(1))
    P = sparse.csc_matrix((total, total)); q = np.r_[np.zeros(n), 1.]
    A, b = sparse.vstack(mats, format='csc'), np.concatenate(rhs)
    settings = solver.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_feas = settings.tol_gap_abs = settings.tol_gap_rel = 1e-11
    if hasattr(settings, 'max_threads'):
        settings.max_threads = 1
    solution = solver.DefaultSolver(P, q, A, b, cones, settings).solve()
    point = np.asarray(solution.x, float)
    info.update(solver_status=str(solution.status), iterations=solution.iterations,
        solver_version=solver.__version__, returned_point=point.tolist(),
        active_original_norm_cones=len(active), omitted_exactly_fixed_passing_norms=int((counts == 0).sum()))
    if solver_sink is not None:
        solver_sink(dict(quadratic=P.copy(), linear=q.copy(), matrix=A.copy(), rhs=b.copy(),
            cones=[str(c) for c in cones], record=copy.deepcopy(info)))
    if str(solution.status) not in ('Solved', 'AlmostSolved', 'InsufficientProgress', 'MaxIterations', 'MaxTime'):
        return None, dict(info, status='NotMotionIterateStatus')
    if point.shape != (total,) or not np.isfinite(point).all():
        return None, dict(info, status='InvalidReturnedPoint')
    raw = point[:n]*trust
    info['raw_control_step'] = raw.tolist()
    if np.any(raw < lo*trust-1e-9) or np.any(raw > hi*trust+1e-9):
        return None, dict(info, status='IterateOutsideOriginalBox')
    delta, ray = project(native, nj, raw, value, lower, upper, trust)
    info['strict_original_norm_ray'] = ray
    if delta is None:
        return None, dict(info, status='NoStrictPositiveRay')
    moved = gaps + gj@delta
    after = float(max(0., (clearance_m-moved[triangle]).max()))
    actual_depth = float(max(0., (-moved[inside]).max())) if len(inside) else 0.
    parameter_error = float(abs(eq@delta).max()) if eq.shape[0] else 0.
    info.update(selected_control_step=delta.tolist(), selected_worst_triangle_deficit_m=after,
        selected_material_peak_depth_m=actual_depth, parameter_maximum_absolute_residual=parameter_error)
    if parameter_error > 1e-9:
        return None, dict(info, status='UnverifiedParameterRows')
    if actual_depth > depth:
        return None, dict(info, status='MaterialDepthCeilingExceeded')
    if not after < before:
        return None, dict(info, status='NoStrictTriangleImprovement')
    return delta, dict(info, status='ProvisionalStrictCrossingCandidate')
