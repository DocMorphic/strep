"""Reduce complete per-triangle-pair deficits while retaining separation guards.

Complete separation guards preserve existing positive affine gaps; actual scene checks still decide.
The caller authenticates complete same-point native, guide and guard models.
"""
import copy
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_affine_ray_retreat import FRACTIONS
from native_triangle_separation_guards import SeparationGuards


def direction(native, native_jacobian, gaps_m, gap_jacobian, witnesses,
              value, lower, upper, trust, *, separation_guards, triangle_groups, parameter_rows=None,
              clearance_m=.0001, scale_m=.005, solver_sink=None):
    """Minimize the sum of per-pair worst deficits, keeping containment hard.

    Complete original-mesh affine guards remain hard. Every declared triangle
    corner-pair contributes to its declared pair maximum. Each complete pair
    contributes once to the sum; no corner-population weighting is introduced. All containment
    witnesses are constrained by the starting worst depth. A strictly checked
    finite iterate is provisional; original exported scene checks still decide.
    """
    value, lower, upper, gaps = [np.asarray(a, float) for a in (value, lower, upper, gaps_m)]
    vectors, caps, scales = [np.asarray(a, float) for a in (native.vectors, native.caps, native.scales)]
    n = len(value) if value.ndim == 1 else 0
    if not isinstance(separation_guards, SeparationGuards):
        raise ValueError('Explicit complete separation guard model required')
    guard = separation_guards
    guard_gaps, guard_clearances = [np.asarray(a, float) for a in (guard.gaps_m, guard.clearances_m)]
    guard_j = sparse.csr_matrix(guard.jacobian, copy=True)
    if (guard_gaps.ndim != 1 or len(guard_gaps) > 400_000 or guard_clearances.shape != guard_gaps.shape
            or guard_j.shape != (len(guard_gaps), n) or len(guard.descriptors) != len(guard_gaps)
            or any(not np.isfinite(a).all() for a in (guard_gaps, guard_clearances, guard_j.data))
            or np.any(guard_clearances <= 0) or guard.report.get('complete_pair_partition') is not True
            or guard.report.get('controls') != n):
        raise ValueError('Complete finite indexed positive separation guard rows required')
    nj, gj = [sparse.csr_matrix(a, copy=True) for a in (native_jacobian, gap_jacobian)]
    eq = sparse.csr_matrix((0, n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows, copy=True)
    if (not 1 <= n <= 96 or lower.shape != value.shape or upper.shape != value.shape
            or vectors.ndim != 2 or vectors.shape[1:] != (3,) or not len(vectors)
            or caps.shape != (len(vectors),) or scales.shape != caps.shape or nj.shape != (vectors.size, n)
            or gaps.ndim != 1 or not 1 <= len(gaps) <= 4096 or gj.shape != (len(gaps), n)
            or eq.shape[1] != n or eq.shape[0] > 96 or nj.nnz + gj.nnz + eq.nnz + guard_j.nnz > 60_000_000
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
    if (not isinstance(triangle_groups, list) or not triangle_groups
            or any(not isinstance(group, list) or len(group) != 9 or any(type(i) is not int for i in group) for group in triangle_groups)):
        raise ValueError('Explicit complete nine-corner triangle groups required')
    flat = [i for group in triangle_groups for i in group]
    if len(set(flat)) != len(flat) or set(flat) != set(triangle.tolist()):
        raise ValueError('Every original triangle guide row must occur exactly once in its complete group')
    group_ids = np.array(triangle_groups, int)
    def group_deficits(shifted):
        return np.maximum(0., (clearance_m-shifted[group_ids]).max(axis=1))
    grouped_before = group_deficits(gaps)
    grouped_merit_before = float(grouped_before.sum())
    depth = float(max(0., (-gaps[inside]).max())) if len(inside) else 0.
    before = float(max(0., (clearance_m - gaps[triangle]).max())) if len(triangle) else 0.
    anchor = float(((np.linalg.norm(vectors, axis=1) - caps) / scales).max())
    info = dict(schema='strep-native-material-grouped-crossing-step-v1', status='not-solved',
        original_norm_rows=len(caps), controls=n, complete_guide_rows=len(gaps),
        triangle_rows=triangle.tolist(), containment_rows=inside.tolist(), parameter_rows=eq.shape[0],
        witnesses=copy.deepcopy(witnesses), original_anchor_maximum_excess=anchor,
        triangle_groups=copy.deepcopy(triangle_groups), triangle_group_count=len(group_ids),
        initial_group_deficits_m=grouped_before.tolist(), initial_grouped_deficit_sum_m=grouped_merit_before,
        objective='Sum of complete triangle-pair maximum corner deficits, one contribution per pair.',
        initial_worst_triangle_deficit_m=before, original_material_depth_ceiling_m=depth,
        clearance_m=clearance_m, scale_m=scale_m, original_caps_scales_clocks_unchanged=True,
        complete_separation_guard_rows=len(guard_gaps), separation_guard_partition=copy.deepcopy(guard.report),
        original_guard_anchor_maximum_excess_m=float((guard_clearances-guard_gaps).max()) if len(guard_gaps) else 0.,
        strict_separation_guard_tolerance_m=0., guard_descriptors=copy.deepcopy(guard.descriptors),
        all_original_native_rows_columns_retained=True, all_guide_rows_retained=True,
        strict_native_acceptance_tolerance=0., strict_material_depth_tolerance_m=0.,
        parameter_proposal_tolerance=1e-9, solver_statuses_preserved=True,
        solver_optimality_verified=False, quality_approved=False, release_approved=False,
        scope='Sum of complete per-pair worst fixed-axis support deficits with all original hard native norms '
              'and starting material vertex-depth ceiling; every complete positive separation guard is hard. '
              'An explicit81-fraction prefix rechecks all represented hard conditions with zero acceptance allowance. '
              'Repeated rows receive no added objective weight. '
              'Strict represented checks do not prove nonlinear nonregression, mesh separation or contact. '
              'Caller authenticates complete witnesses and same-point derivatives. Actual stored motion, '
              'contacts, references and complete scene geometry remain required.')
    if anchor > 0:
        return None, dict(info, status='OriginalAnchorNotStrictlyPassing')
    if info['original_guard_anchor_maximum_excess_m'] > 0:
        return None, dict(info, status='OriginalSeparationGuardAnchorNotPassing')
    if not len(triangle) or before == 0.:
        return None, dict(info, status='NoTriangleDeficit')
    solver = solver_module()
    nj.eliminate_zeros()
    counts = np.diff(nj.indptr).reshape(-1, 3).sum(axis=1)
    active = np.flatnonzero(counts != 0)
    lo, hi = np.maximum(-1., (lower-value)/trust), np.minimum(1., (upper-value)/trust)
    extra = len(group_ids); total = n + extra
    box = sparse.hstack([sparse.eye(n), sparse.csc_matrix((n, extra))], format='csc')
    mats, rhs = [box, -box], [hi, -lo]
    cones = [solver.NonnegativeConeT(2*n)]
    if eq.shape[0]:
        mats.append(sparse.hstack([eq*trust, sparse.csc_matrix((eq.shape[0], extra))], format='csc'))
        rhs.append(np.zeros(eq.shape[0])); cones.append(solver.ZeroConeT(eq.shape[0]))
    if len(active):
        selected = nj[(3*active[:, None]+np.arange(3)).ravel()].multiply(
            (-trust/np.repeat(scales[active], 3))[:, None]).tocoo()
        mats.append(sparse.csc_matrix((selected.data,
            (4*(selected.row//3)+1+selected.row%3, selected.col)), shape=(4*len(active), total)))
        rhs.append((np.c_[caps[active], vectors[active]]/scales[active, None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in active)
    if len(inside):
        mats.append(sparse.hstack([-trust/scale_m*gj[inside], sparse.csc_matrix((len(inside), extra))], format='csc'))
        rhs.append((gaps[inside]+depth)/scale_m); cones.append(solver.NonnegativeConeT(len(inside)))
    if len(guard_gaps):
        mats.append(sparse.hstack([-trust/scale_m*guard_j, sparse.csc_matrix((len(guard_gaps), extra))], format='csc'))
        rhs.append((guard_gaps-guard_clearances)/scale_m); cones.append(solver.NonnegativeConeT(len(guard_gaps)))
    ordered=group_ids.ravel()
    slack=sparse.csc_matrix((-np.ones(len(ordered)),(np.arange(len(ordered)),np.repeat(np.arange(extra),9))),shape=(len(ordered),extra))
    mats.append(sparse.hstack([-trust/scale_m*gj[ordered],slack],format='csc'))
    rhs.append((gaps[ordered]-clearance_m)/scale_m);cones.append(solver.NonnegativeConeT(len(ordered)))
    mats.append(sparse.hstack([sparse.csc_matrix((extra,n)),-sparse.eye(extra)],format='csc'))
    rhs.append(np.zeros(extra));cones.append(solver.NonnegativeConeT(extra))
    P=sparse.csc_matrix((total,total));q=np.r_[np.zeros(n),np.ones(extra)]
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
    step_lo, step_hi = np.maximum(-trust, lower-value), np.minimum(trust, upper-value)
    records = []
    for alpha in FRACTIONS:
        delta = np.clip(raw*alpha, step_lo, step_hi)
        delta = np.clip(value+delta, lower, upper)-value
        moved_native = vectors+(nj@delta).reshape(vectors.shape)
        excess = float(((np.linalg.norm(moved_native, axis=1)-caps)/scales).max())
        moved = gaps+gj@delta
        after = float(max(0., (clearance_m-moved[triangle]).max()))
        actual_depth = float(max(0., (-moved[inside]).max())) if len(inside) else 0.
        guard_excess = float((guard_clearances-(guard_gaps+guard_j@delta)).max()) if len(guard_gaps) else 0.
        parameter_error = float(abs(eq@delta).max()) if eq.shape[0] else 0.
        grouped = group_deficits(moved); grouped_merit = float(grouped.sum())
        box_pass = bool(np.all(delta >= step_lo) and np.all(delta <= step_hi))
        nonzero = bool(np.any(delta != 0))
        records.append(dict(fraction=alpha,original_step_box_pass=box_pass,original_native_maximum_excess=excess,
            material_peak_depth_m=actual_depth,separation_guard_maximum_excess_m=guard_excess,
            parameter_maximum_absolute_residual=parameter_error,worst_triangle_deficit_m=after,
            nonzero_step=nonzero,strict_grouped_improvement=grouped_merit<grouped_merit_before,grouped_deficit_sum_m=grouped_merit))
        if (box_pass and nonzero and excess <= 0 and actual_depth <= depth and guard_excess <= 0
                and parameter_error <= 1e-9 and grouped_merit < grouped_merit_before):
            return delta, dict(info,status='ProvisionalStrictGroupedCrossingCandidate',records=records,
                selected_fraction=alpha,selected_control_step=delta.tolist(),selected_worst_triangle_deficit_m=after,
                selected_group_deficits_m=grouped.tolist(),selected_grouped_deficit_sum_m=grouped_merit,
                selected_material_peak_depth_m=actual_depth,selected_separation_guard_maximum_excess_m=guard_excess,
                selected_native_maximum_excess=excess,parameter_maximum_absolute_residual=parameter_error)
    return None, dict(info,status='NoStrictImprovingGroupedRay',records=records)
