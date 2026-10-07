"""Whole-source convex component support objective with full-mesh guards.

Caller authenticates complete source membership and same-point models.
Strict affine checks are provisional; original stored scene gates still decide.
"""
import copy
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_affine_ray_retreat import FRACTIONS
from native_triangle_separation_guards import SeparationGuards
from native_component_separation_guards import ComponentSeparationGuards


def _groups(groups, witnesses, component, clearances):
    if not isinstance(groups,list) or not groups:
        raise ValueError('Explicit complete component groups required')
    result=[];seen=set();identities=set()
    for k,group in enumerate(groups):
        if not isinstance(group,dict):raise ValueError('Indexed component group metadata required')
        left,right,ids,actors,axis,t=[group.get(key) for key in
            ('left_vertex_ids','right_vertex_ids','row_indices','actors','axis_world','time_s')]
        if (any(not isinstance(v,list) or not 4<=len(v)<=64 or any(type(i) is not int or i<0 for i in v)
                or v!=sorted(set(v)) for v in (left,right))
            or not isinstance(ids,list) or len(ids)!=len(left)*len(right)
            or any(type(i) is not int or i<0 or i>=len(witnesses) for i in ids)
            or len(set(ids))!=len(ids) or seen.intersection(ids)
            or not isinstance(actors,list) or len(actors)!=2 or any(not isinstance(n,str) or not n for n in actors)
            or actors[0]==actors[1] or type(t) not in (int,float) or not np.isfinite(t) or t<0
            or not isinstance(axis,list) or len(axis)!=3 or any(type(v) not in (int,float) for v in axis)
            or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.)>1e-12):
            raise ValueError('Complete distinct ordered component vertices, pair rows, actors, time and unit axis required')
        identity=(t,tuple(sorted(((actors[0],tuple(left)),(actors[1],tuple(right))))))
        if identity in identities:raise ValueError('A complete component/time pair must contribute only once')
        identities.add(identity)
        for i,(a,b) in zip(ids,((a,b) for a in left for b in right)):
            w=witnesses[i]
            if (w.get('kind')!='component-separation' or type(w.get('component_group_index')) is not int
                or w['component_group_index']!=k or type(w.get('descriptor_index')) is not int or w['descriptor_index']!=i
                or type(w.get('left_vertex')) is not int or type(w.get('right_vertex')) is not int
                or (w['left_vertex'],w['right_vertex'])!=(a,b)):
                raise ValueError('Each typed component row must match its complete ordered source vertex pair')
        if not np.all(clearances[ids]==clearances[ids[0]]):
            raise ValueError('One explicit uniform clearance per complete component group required')
        seen.update(ids);result.append(np.array(ids,int))
    if seen!=set(component.tolist()):raise ValueError('Every component row must occur exactly once in its complete group')
    return result


def _auxiliary(guard, n):
    if not isinstance(guard, ComponentSeparationGuards):
        raise ValueError('Separately typed complete positive component guards required')
    gaps, clearances = np.asarray(guard.gaps_m, float), np.asarray(guard.clearances_m, float)
    jac = sparse.csr_matrix(guard.jacobian, copy=True)
    r = guard.report
    if (not isinstance(r, dict) or r.get('schema') != 'strep-native-component-separation-guards-v1'
            or r.get('controls') != n or r.get('complete_component_pair_rows') is not True
            or r.get('full_mesh_pair_partition') is not False or r.get('continuous_coverage') is not False
            or gaps.ndim != 1 or not 1 <= len(gaps) <= 400000 or clearances.shape != gaps.shape
            or jac.shape != (len(gaps), n) or r.get('guard_rows') != len(gaps)
            or any(not np.isfinite(v).all() for v in (gaps, clearances, jac.data))
            or np.any(clearances <= 0) or np.any(clearances > .001)
            or not isinstance(guard.groups, list) or not 1 <= len(guard.groups) <= 4096
            or r.get('component_samples') != len(guard.groups)
            or not isinstance(guard.descriptors, list) or len(guard.descriptors) != len(gaps)
            or not isinstance(r.get('source_vertex_ids'), dict) or len(r['source_vertex_ids']) != 2
            or not isinstance(r.get('times_s'), list) or len(r['times_s']) != len(guard.groups)):
        raise ValueError('Complete finite separately covered component guard model required')
    seen = set(); previous = -1.
    for k, group in enumerate(guard.groups):
        if not isinstance(group, dict):raise ValueError('Complete component guard groups required')
        actors, left, right, ids, axis, t = [group.get(key) for key in
            ('actors','left_vertex_ids','right_vertex_ids','row_indices','axis_world','time_s')]
        if (not isinstance(actors,list) or len(actors)!=2 or actors[0]==actors[1]
                or any(type(a) is not str or not a for a in actors) or set(actors)!=set(r['source_vertex_ids'])
                or any(not isinstance(v,list) or not 4<=len(v)<=64
                       or any(type(i) is not int or i<0 for i in v) or v!=sorted(set(v)) for v in (left,right))
                or r['source_vertex_ids'][actors[0]]!=left or r['source_vertex_ids'][actors[1]]!=right
                or not isinstance(ids,list) or len(ids)!=len(left)*len(right)
                or any(type(i) is not int or i<0 or i>=len(gaps) for i in ids)
                or len(set(ids))!=len(ids) or seen.intersection(ids)
                or type(t) not in (int,float) or not np.isfinite(t) or t<0 or t<=previous or r['times_s'][k]!=t
                or not isinstance(axis,list) or len(axis)!=3 or any(type(v) not in (int,float) for v in axis)
                or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.)>1e-12
                or type(group.get('clearance_m')) not in (int,float)
                or not np.all(clearances[ids]==group['clearance_m'])):
            raise ValueError('Exact complete ordered component guard groups, clocks and margins required')
        for i,(a,b) in zip(ids,((a,b) for a in left for b in right)):
            d=guard.descriptors[i]
            if (not isinstance(d,dict) or d.get('kind')!='component-separation-guard'
                    or type(d.get('group_index')) is not int or d['group_index']!=k
                    or type(d.get('left_vertex')) is not int or type(d.get('right_vertex')) is not int
                    or (d['left_vertex'],d['right_vertex'])!=(a,b)
                    or d.get('actors')!=actors or d.get('time_s')!=t or d.get('axis_world')!=axis
                    or d.get('clearance_m')!=clearances[i]):
                raise ValueError('Every auxiliary row must match its complete typed source pair')
        seen.update(ids);previous=t
    if seen!=set(range(len(gaps))):raise ValueError('Every auxiliary component guard row must occur exactly once')
    return gaps, clearances, jac


def direction(native, native_jacobian, gaps_m, gap_jacobian, witnesses,
              value, lower, upper, trust, *, separation_guards, component_separation_guards, component_groups, guide_clearances_m, parameter_rows=None,
              scale_m=.005, solver_sink=None):
    """Reduce whole-component support deficits under original hard local bounds.

    Each complete ordered vertex Cartesian product contributes its worst
    fixed-axis deficit once. Preserve starting worst containment and legacy
    triangle deficit ceilings, all positive guards and original native norms.
    Caller authenticates full source membership and same-point descriptors.
    Actual stored motion/contact/reference/full-mesh checks remain decisive.
    """
    value, lower, upper, gaps = [np.asarray(a, float) for a in (value, lower, upper, gaps_m)]
    vectors, caps, scales = [np.asarray(a, float) for a in (native.vectors, native.caps, native.scales)]
    n = len(value) if value.ndim == 1 else 0
    clearances=np.asarray(guide_clearances_m,float)
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
    auxiliary=component_separation_guards
    aux_gaps,aux_clearances,aux_j=_auxiliary(auxiliary,n)
    nj, gj = [sparse.csr_matrix(a, copy=True) for a in (native_jacobian, gap_jacobian)]
    eq = sparse.csr_matrix((0, n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows, copy=True)
    if (not 1 <= n <= 96 or lower.shape != value.shape or upper.shape != value.shape
            or vectors.ndim != 2 or vectors.shape[1:] != (3,) or not len(vectors)
            or caps.shape != (len(vectors),) or scales.shape != caps.shape or nj.shape != (vectors.size, n)
            or gaps.ndim != 1 or not 1 <= len(gaps) <= 4096 or gj.shape != (len(gaps), n)
            or eq.shape[1] != n or eq.shape[0] > 96 or nj.nnz + gj.nnz + eq.nnz + guard_j.nnz + aux_j.nnz > 60_000_000
            or len(guard_gaps)+len(aux_gaps)>400_000
            or not isinstance(witnesses, list) or len(witnesses) != len(gaps)
            or any(not isinstance(w, dict) or w.get('kind') not in ('triangle-separation', 'penetrating-vertex', 'component-separation') for w in witnesses)
            or any(not np.isfinite(a).all() for a in (value, lower, upper, vectors, caps, scales, gaps, nj.data, gj.data, eq.data))
            or np.any(caps < 0) or np.any(scales <= 0) or np.any(lower >= upper)
            or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or clearances.shape!=gaps.shape or not np.isfinite(clearances).all() or np.any(clearances<0) or np.any(clearances>.1)
            or type(scale_m) not in (int, float) or not np.isfinite(scale_m) or not 1e-6 <= scale_m <= 1.
            or solver_sink is not None and not callable(solver_sink)):
        raise ValueError('Complete finite native/material model, witnesses, ordered bounds and settings required')
    triangle = np.array([i for i, w in enumerate(witnesses) if w['kind'] == 'triangle-separation'], int)
    inside = np.array([i for i, w in enumerate(witnesses) if w['kind'] == 'penetrating-vertex'], int)
    if len(inside) and np.any(gaps[inside] > 0):
        raise ValueError('Every declared containment witness needs a nonpositive anchor gap')
    component=np.array([i for i,w in enumerate(witnesses) if w['kind']=='component-separation'],int)
    group_ids=_groups(component_groups,witnesses,component,clearances)
    def group_deficits(shifted):
        return np.array([max(0.,float((clearances[ids]-shifted[ids]).max())) for ids in group_ids])
    grouped_before = group_deficits(gaps)
    grouped_merit_before = float(grouped_before.sum())
    depth = float(max(0., (-gaps[inside]).max())) if len(inside) else 0.
    triangle_ceiling=float(max(0.,(clearances[triangle]-gaps[triangle]).max())) if len(triangle) else 0.
    before = float(grouped_before.max())
    anchor = float(((np.linalg.norm(vectors, axis=1) - caps) / scales).max())
    info = dict(schema='strep-native-material-component-guarded-support-step-v1', status='not-solved',
        original_norm_rows=len(caps), controls=n, complete_guide_rows=len(gaps),
        triangle_rows=triangle.tolist(), containment_rows=inside.tolist(), parameter_rows=eq.shape[0],
        witnesses=copy.deepcopy(witnesses), original_anchor_maximum_excess=anchor,
        component_rows=component.tolist(),component_groups=copy.deepcopy(component_groups),component_group_count=len(group_ids),
        component_group_sizes=[len(g) for g in group_ids],guide_clearances_m=clearances.tolist(),
        initial_group_deficits_m=grouped_before.tolist(), initial_grouped_deficit_sum_m=grouped_merit_before,
        objective='Sum of complete component-pair maximum vertex deficits, one contribution per component/time pair.',
        initial_worst_component_deficit_m=before, original_material_depth_ceiling_m=depth,
        original_triangle_deficit_ceiling_m=triangle_ceiling, scale_m=scale_m, original_caps_scales_clocks_unchanged=True,
        complete_separation_guard_rows=len(guard_gaps), separation_guard_partition=copy.deepcopy(guard.report),
        original_guard_anchor_maximum_excess_m=float((guard_clearances-guard_gaps).max()) if len(guard_gaps) else 0.,
        strict_separation_guard_tolerance_m=0., guard_descriptors=copy.deepcopy(guard.descriptors),
        auxiliary_component_guard_rows=len(aux_gaps),auxiliary_component_guard_coverage=copy.deepcopy(auxiliary.report),
        auxiliary_component_guard_groups=copy.deepcopy(auxiliary.groups),auxiliary_component_guard_descriptors=copy.deepcopy(auxiliary.descriptors),
        auxiliary_component_anchor_maximum_excess_m=float((aux_clearances-aux_gaps).max()),
        strict_auxiliary_component_guard_tolerance_m=0.,
        all_original_native_rows_columns_retained=True, all_guide_rows_retained=True,
        strict_native_acceptance_tolerance=0., strict_material_depth_tolerance_m=0.,
        parameter_proposal_tolerance=1e-9, solver_statuses_preserved=True,
        solver_optimality_verified=False, quality_approved=False, release_approved=False,
        scope='Sum of complete component/time worst fixed-axis support deficits with all original hard native norms '
              'and starting material vertex-depth and legacy triangle-deficit ceilings; every complete positive separation guard is hard. '
              'Separate complete positive component sample guards are also hard and retain their own coverage metadata. '
              'An explicit81-fraction prefix rechecks all represented hard conditions with zero acceptance allowance. '
              'Every ordered source vertex pair retained; unequal component sizes receive one objective contribution each. '
              'Strict represented checks do not prove nonlinear nonregression, mesh separation or contact. '
              'Caller authenticates complete witnesses and same-point derivatives. Actual stored motion, '
              'contacts, references and complete scene geometry remain required.')
    if anchor > 0:
        return None, dict(info, status='OriginalAnchorNotStrictlyPassing')
    if info['original_guard_anchor_maximum_excess_m'] > 0:
        return None, dict(info, status='OriginalSeparationGuardAnchorNotPassing')
    if info['auxiliary_component_anchor_maximum_excess_m'] > 0:
        return None,dict(info,status='OriginalAuxiliaryComponentGuardAnchorNotPassing')
    if before == 0.:
        return None, dict(info, status='NoComponentDeficit')
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
    if len(triangle):
        mats.append(sparse.hstack([-trust/scale_m*gj[triangle],sparse.csc_matrix((len(triangle),extra))],format='csc'))
        rhs.append((gaps[triangle]-clearances[triangle]+triangle_ceiling)/scale_m);cones.append(solver.NonnegativeConeT(len(triangle)))
    if len(guard_gaps):
        mats.append(sparse.hstack([-trust/scale_m*guard_j, sparse.csc_matrix((len(guard_gaps), extra))], format='csc'))
        rhs.append((guard_gaps-guard_clearances)/scale_m); cones.append(solver.NonnegativeConeT(len(guard_gaps)))
    mats.append(sparse.hstack([-trust/scale_m*aux_j,sparse.csc_matrix((len(aux_gaps),extra))],format='csc'))
    rhs.append((aux_gaps-aux_clearances)/scale_m);cones.append(solver.NonnegativeConeT(len(aux_gaps)))
    ordered=np.concatenate(group_ids)
    slack=sparse.csc_matrix((-np.ones(len(ordered)),(np.arange(len(ordered)),np.repeat(np.arange(extra),[len(ids) for ids in group_ids]))),shape=(len(ordered),extra))
    mats.append(sparse.hstack([-trust/scale_m*gj[ordered],slack],format='csc'))
    rhs.append((gaps[ordered]-clearances[ordered])/scale_m);cones.append(solver.NonnegativeConeT(len(ordered)))
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
        after=float(group_deficits(moved).max())
        triangle_after=float(max(0.,(clearances[triangle]-moved[triangle]).max())) if len(triangle) else 0.
        actual_depth = float(max(0., (-moved[inside]).max())) if len(inside) else 0.
        guard_excess = float((guard_clearances-(guard_gaps+guard_j@delta)).max()) if len(guard_gaps) else 0.
        aux_excess=float((aux_clearances-(aux_gaps+aux_j@delta)).max())
        parameter_error = float(abs(eq@delta).max()) if eq.shape[0] else 0.
        grouped = group_deficits(moved); grouped_merit = float(grouped.sum())
        box_pass = bool(np.all(delta >= step_lo) and np.all(delta <= step_hi))
        nonzero = bool(np.any(delta != 0))
        records.append(dict(fraction=alpha,original_step_box_pass=box_pass,original_native_maximum_excess=excess,
            material_peak_depth_m=actual_depth,separation_guard_maximum_excess_m=guard_excess,
            parameter_maximum_absolute_residual=parameter_error,worst_component_deficit_m=after,
            worst_legacy_triangle_deficit_m=triangle_after,auxiliary_component_guard_maximum_excess_m=aux_excess,
            nonzero_step=nonzero,strict_grouped_improvement=grouped_merit<grouped_merit_before,grouped_deficit_sum_m=grouped_merit))
        if (box_pass and nonzero and excess <= 0 and actual_depth <= depth and triangle_after <= triangle_ceiling and guard_excess <= 0
                and aux_excess <= 0 and parameter_error <= 1e-9 and grouped_merit < grouped_merit_before):
            return delta, dict(info,status='ProvisionalStrictComponentSupportCandidate',records=records,
                selected_fraction=alpha,selected_control_step=delta.tolist(),selected_worst_component_deficit_m=after,selected_worst_legacy_triangle_deficit_m=triangle_after,
                selected_group_deficits_m=grouped.tolist(),selected_grouped_deficit_sum_m=grouped_merit,
                selected_material_peak_depth_m=actual_depth,selected_separation_guard_maximum_excess_m=guard_excess,
                selected_native_maximum_excess=excess,selected_auxiliary_component_guard_maximum_excess_m=aux_excess,parameter_maximum_absolute_residual=parameter_error)
    return None, dict(info,status='NoStrictImprovingComponentRay',records=records)
