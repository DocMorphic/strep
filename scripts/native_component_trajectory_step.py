"""Complete sampled component correction under original hard local conditions.

Large trajectory rows are separate from bounded legacy material witnesses.
All initially positive component samples and full-mesh guards stay hard.
Represented affine passes remain provisional until actual stored scene checks.
"""
import copy
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_scene_conic import solver_module
from native_affine_ray_retreat import FRACTIONS
from native_component_trajectory_model import ComponentTrajectoryModel
from native_triangle_separation_guards import SeparationGuards


def _trajectory(model,n):
    if not isinstance(model,ComponentTrajectoryModel):
        raise ValueError('Separately typed complete trajectory required')
    r=model.report
    gaps,margins,weights=[np.asarray(v,float) for v in (model.gaps_m,model.clearances_m,model.weights_s)]
    jac=sparse.csr_matrix(model.jacobian,copy=True)
    groups=model.groups
    if (not isinstance(r,dict) or r.get('schema')!='strep-native-component-trajectory-model-v1'
            or type(r.get('controls')) is not int or r['controls']!=n or r.get('required_times_exact') is not True
            or r.get('complete_component_pair_rows') is not True
            or r.get('full_mesh_pair_partition') is not False or r.get('continuous_coverage') is not False
            or not isinstance(groups,list) or not 1<=len(groups)<=4096
            or type(r.get('component_samples')) is not int or r['component_samples']!=len(groups) or not isinstance(r.get('times_s'),list)
            or len(r['times_s'])!=len(groups) or not isinstance(r.get('source_vertex_ids'),dict)
            or len(r['source_vertex_ids'])!=2 or any(type(a) is not str or not a for a in r['source_vertex_ids'])
            or gaps.ndim!=1 or not 1<=len(gaps)<=400000 or margins.shape!=gaps.shape
            or weights.shape!=(len(groups),) or jac.shape!=(len(gaps),n) or type(r.get('rows')) is not int or r['rows']!=len(gaps)
            or any(not np.isfinite(v).all() for v in (gaps,margins,weights,jac.data))
            or np.any(margins<=0) or np.any(weights<=0)
            or type(r.get('requested_clearance_m')) not in (int,float)
            or not 1e-9<=r['requested_clearance_m']<=.001):
        raise ValueError('Complete finite clock, trajectory groups and columns required')
    ids=r['source_vertex_ids']
    for v in ids.values():
        if (not isinstance(v,list) or not 4<=len(v)<=64 or any(type(i) is not int or i<0 for i in v)
                or v!=sorted(set(v))):raise ValueError('Complete ordered original component IDs required')
    if any(type(t) not in (int,float) for t in r['times_s']):raise ValueError('Explicit numeric original times required')
    a,b=list(ids);pairs=len(ids[a])*len(ids[b]);times=np.array(r['times_s'],float)
    if (len(gaps)!=len(groups)*pairs or not np.isfinite(times).all() or np.any(times<0) or np.any(np.diff(times)<=0)):
        raise ValueError('Every original pair at every ordered time required')
    expected_weights=np.ones(1) if len(times)==1 else np.r_[(times[1]-times[0])/2,
        (times[2:]-times[:-2])/2,(times[-1]-times[-2])/2]
    if not np.array_equal(weights,expected_weights):raise ValueError('Exact original-clock quadrature required')
    rows=[];positive=[]
    for k,g in enumerate(groups):
        first,last=k*pairs,(k+1)*pairs;smallest=float(gaps[first:last].min())
        margin=min(r['requested_clearance_m'],smallest) if smallest>0 else r['requested_clearance_m']
        if not isinstance(g,dict):raise ValueError('Complete indexed groups required')
        axis=g.get('axis_world')
        if (g.get('actors')!=[a,b] or g.get('left_vertex_ids')!=ids[a] or g.get('right_vertex_ids')!=ids[b]
                or type(g.get('first_row')) is not int or type(g.get('stop_row')) is not int
                or any(not isinstance(g.get(key),list) or any(type(v) is not int for v in g[key])
                       for key in ('left_vertex_ids','right_vertex_ids'))
                or g['first_row']!=first or g['stop_row']!=last or type(g.get('time_s')) not in (int,float)
                or g['time_s']!=times[k] or not isinstance(axis,list) or len(axis)!=3
                or any(type(v) not in (int,float) for v in axis) or not np.isfinite(axis).all()
                or abs(np.linalg.norm(axis)-1.)>1e-12 or type(g.get('starts_positive')) is not bool
                or g['starts_positive']!=(smallest>0) or g.get('starting_minimum_support_gap_m')!=smallest
                or g.get('clearance_m')!=margin or not np.all(margins[first:last]==margin)
                or g.get('quadrature_weight_s')!=weights[k]):
            raise ValueError('Every complete source/time group, fixed axis and capped margin required')
        rows.append(np.arange(first,last))
        if smallest>0:positive.append(k)
    if (not isinstance(r.get('positive_sample_indices'),list)
            or any(type(i) is not int for i in r['positive_sample_indices']) or r['positive_sample_indices']!=positive):
        raise ValueError('Every initially positive component sample must be retained')
    positive_rows=np.concatenate([rows[k] for k in positive]) if positive else np.array([],int)
    return gaps,margins,weights,jac,rows,positive_rows


def direction(native,native_jacobian,trajectory,value,lower,upper,trust,*,separation_guards,
              material_gaps_m,material_gap_jacobian,material_witnesses,material_clearances_m,
              parameter_rows=None,scale_m=.005,solver_sink=None):
    """Reduce clock-weighted complete support deficits with original hard bounds.

Keep native norms, edit/trust box, equalities, full-mesh guards and every
initially clear component sample. Legacy containment/triangle rows retain
their starting ceilings and their separate4096-row population limit.
    """
    value,lower,upper,mg,mc=[np.asarray(v,float) for v in
        (value,lower,upper,material_gaps_m,material_clearances_m)]
    n=len(value) if value.ndim==1 else 0
    if not isinstance(native,NormRows) or not isinstance(separation_guards,SeparationGuards):
        raise ValueError('Complete native norms and full-mesh guard model required')
    vectors,caps,scales=native.vectors,native.caps,native.scales
    nj,mj,guard_j=[sparse.csr_matrix(v,copy=True) for v in
        (native_jacobian,material_gap_jacobian,separation_guards.jacobian)]
    gg,gc=[np.asarray(v,float) for v in (separation_guards.gaps_m,separation_guards.clearances_m)]
    eq=sparse.csr_matrix((0,n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows,copy=True)
    gaps,margins,weights,tj,groups,positive_rows=_trajectory(trajectory,n)
    if (not 1<=n<=96 or lower.shape!=value.shape or upper.shape!=value.shape or len(caps)>400000
            or nj.shape!=(vectors.size,n) or mg.ndim!=1 or len(mg)>4096 or mc.shape!=mg.shape or mj.shape!=(len(mg),n)
            or not isinstance(material_witnesses,list) or len(material_witnesses)!=len(mg)
            or any(not isinstance(w,dict) or w.get('kind') not in ('triangle-separation','penetrating-vertex') for w in material_witnesses)
            or gg.ndim!=1 or gc.shape!=gg.shape or guard_j.shape!=(len(gg),n)
            or len(separation_guards.descriptors)!=len(gg) or separation_guards.report.get('complete_pair_partition') is not True
            or separation_guards.report.get('controls')!=n or np.any(gc<=0)
            or len(gaps)+len(gg)+len(mg)>400000 or eq.shape[1]!=n or eq.shape[0]>96
            or nj.nnz+tj.nnz+mj.nnz+guard_j.nnz+eq.nnz>60000000
            or any(not np.isfinite(v).all() for v in (value,lower,upper,vectors,caps,scales,mg,mc,gg,gc,nj.data,mj.data,guard_j.data,eq.data))
            or np.any(caps<0) or np.any(scales<=0) or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
            or np.any(mc<0) or np.any(mc>.1)
            or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6<=trust<=.02
            or type(scale_m) not in (int,float) or not np.isfinite(scale_m) or not 1e-6<=scale_m<=1.
            or solver_sink is not None and not callable(solver_sink)):
        raise ValueError('Complete finite original model, separately bounded legacy witnesses and hard conditions required')
    inside=np.array([i for i,w in enumerate(material_witnesses) if w['kind']=='penetrating-vertex'],int)
    triangle=np.array([i for i,w in enumerate(material_witnesses) if w['kind']=='triangle-separation'],int)
    if len(inside) and np.any(mg[inside]>0):raise ValueError('Containment gaps must start nonpositive')
    depth=float(max(0.,(-mg[inside]).max())) if len(inside) else 0.
    ceiling=float(max(0.,(mc[triangle]-mg[triangle]).max())) if len(triangle) else 0.
    def deficits(moved):return np.array([max(0.,float((margins[ids]-moved[ids]).max())) for ids in groups])
    before=deficits(gaps);integral=float(before@weights)
    anchor=float(((np.linalg.norm(vectors,axis=1)-caps)/scales).max())
    info=dict(schema='strep-native-component-trajectory-step-v1',status='not-solved',controls=n,original_norm_rows=len(caps),
        complete_component_rows=len(gaps),component_group_count=len(groups),positive_component_rows=len(positive_rows),
        trajectory_coverage=copy.deepcopy(trajectory.report),component_groups=copy.deepcopy(trajectory.groups),
        initial_group_deficits_m=before.tolist(),initial_deficit_integral_m_s=integral,initial_deficit_sum_m=float(before.sum()),
        objective='Normalized original-clock trapezoidal integral of complete component/time worst deficits.',
        material_rows=len(mg),triangle_rows=triangle.tolist(),containment_rows=inside.tolist(),material_witnesses=copy.deepcopy(material_witnesses),
        original_material_depth_ceiling_m=depth,original_triangle_deficit_ceiling_m=ceiling,
        complete_separation_guard_rows=len(gg),separation_guard_partition=copy.deepcopy(separation_guards.report),
        guard_descriptors=copy.deepcopy(separation_guards.descriptors),parameter_rows=eq.shape[0],scale_m=scale_m,
        original_anchor_maximum_excess=anchor,strict_native_acceptance_tolerance=0.,strict_guard_tolerance_m=0.,
        strict_material_depth_tolerance_m=0.,parameter_proposal_tolerance=1e-9,
        original_caps_scales_clocks_unchanged=True,all_original_native_rows_columns_retained=True,
        all_trajectory_rows_times_columns_retained=True,solver_statuses_preserved=True,solver_optimality_verified=False,
        quality_approved=False,release_approved=False,
        scope='Complete sampled component objective under original hard native/control/trust/parameter conditions, '
              'separate legacy material ceilings and complete full-mesh guards. Every initially positive component '
              'pair row remains hard without objective slack. All81 strict ray checks preserve statuses. '
              'Caller binds source/clock/fresh same-pose derivatives; actual stored motion, references, contacts '
              'and full original scene checks remain decisive. No nonlinear or between-sample certificate.')
    if anchor>0:return None,dict(info,status='OriginalAnchorNotStrictlyPassing')
    if len(gg) and np.any(gc-gg>0):return None,dict(info,status='OriginalSeparationGuardAnchorNotPassing')
    if np.any(margins[positive_rows]-gaps[positive_rows]>0):return None,dict(info,status='OriginalPositiveComponentAnchorNotPassing')
    if integral==0:return None,dict(info,status='NoComponentDeficit')
    solver=solver_module();nj.eliminate_zeros();counts=np.diff(nj.indptr).reshape(-1,3).sum(axis=1)
    active=np.flatnonzero(counts!=0);extra=len(groups);total=n+extra
    if 2*n+eq.shape[0]+4*len(active)+len(mg)+len(gg)+len(positive_rows)+len(gaps)+extra>2000000:
        raise ValueError('Complete conic population exceeds row budget; no subset returned')
    lo,hi=np.maximum(-1.,(lower-value)/trust),np.minimum(1.,(upper-value)/trust)
    box=sparse.hstack([sparse.eye(n),sparse.csc_matrix((n,extra))],format='csc')
    mats,rhs=[box,-box],[hi,-lo];cones=[solver.NonnegativeConeT(2*n)]
    def hard(j,b):
        mats.append(sparse.hstack([-trust/scale_m*j,sparse.csc_matrix((len(b),extra))],format='csc'))
        rhs.append(b/scale_m);cones.append(solver.NonnegativeConeT(len(b)))
    if eq.shape[0]:
        mats.append(sparse.hstack([eq*trust,sparse.csc_matrix((eq.shape[0],extra))],format='csc'))
        rhs.append(np.zeros(eq.shape[0]));cones.append(solver.ZeroConeT(eq.shape[0]))
    if len(active):
        selected=nj[(3*active[:,None]+np.arange(3)).ravel()].multiply((-trust/np.repeat(scales[active],3))[:,None]).tocoo()
        mats.append(sparse.csc_matrix((selected.data,(4*(selected.row//3)+1+selected.row%3,selected.col)),shape=(4*len(active),total)))
        rhs.append((np.c_[caps[active],vectors[active]]/scales[active,None]).ravel());cones.extend(solver.SecondOrderConeT(4) for _ in active)
    if len(inside):hard(mj[inside],mg[inside]+depth)
    if len(triangle):hard(mj[triangle],mg[triangle]-mc[triangle]+ceiling)
    if len(gg):hard(guard_j,gg-gc)
    if len(positive_rows):hard(tj[positive_rows],gaps[positive_rows]-margins[positive_rows])
    slack=sparse.csc_matrix((-np.ones(len(gaps)),(np.arange(len(gaps)),np.repeat(np.arange(extra),[len(g) for g in groups]))),shape=(len(gaps),extra))
    mats.append(sparse.hstack([-trust/scale_m*tj,slack],format='csc'));rhs.append((gaps-margins)/scale_m);cones.append(solver.NonnegativeConeT(len(gaps)))
    mats.append(sparse.hstack([sparse.csc_matrix((extra,n)),-sparse.eye(extra)],format='csc'));rhs.append(np.zeros(extra));cones.append(solver.NonnegativeConeT(extra))
    P=sparse.csc_matrix((total,total));q=np.r_[np.zeros(n),weights/weights.sum()]
    A,b=sparse.vstack(mats,format='csc'),np.concatenate(rhs)
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_feas=settings.tol_gap_abs=settings.tol_gap_rel=1e-11
    if hasattr(settings,'max_threads'):settings.max_threads=1
    solution=solver.DefaultSolver(P,q,A,b,cones,settings).solve();point=np.asarray(solution.x,float)
    info.update(solver_status=str(solution.status),iterations=solution.iterations,solver_version=solver.__version__,
        returned_point=point.tolist(),active_original_norm_cones=len(active),omitted_exactly_fixed_passing_norms=int((counts==0).sum()))
    if solver_sink is not None:solver_sink(dict(quadratic=P.copy(),linear=q.copy(),matrix=A.copy(),rhs=b.copy(),cones=[str(c) for c in cones],record=copy.deepcopy(info)))
    if str(solution.status) not in ('Solved','AlmostSolved','InsufficientProgress','MaxIterations','MaxTime'):
        return None,dict(info,status='NotMotionIterateStatus')
    if point.shape!=(total,) or not np.isfinite(point).all():return None,dict(info,status='InvalidReturnedPoint')
    raw=point[:n]*trust;info['raw_control_step']=raw.tolist()
    if np.any(raw<lo*trust-1e-9) or np.any(raw>hi*trust+1e-9):return None,dict(info,status='IterateOutsideOriginalBox')
    step_lo,step_hi=np.maximum(-trust,lower-value),np.minimum(trust,upper-value);records=[]
    for alpha in FRACTIONS:
        delta=np.clip(raw*alpha,step_lo,step_hi);delta=np.clip(value+delta,lower,upper)-value
        excess=float(((np.linalg.norm(vectors+(nj@delta).reshape(vectors.shape),axis=1)-caps)/scales).max())
        moved=gaps+tj@delta;grouped=deficits(moved);after=float(grouped@weights)
        moved_m=mg+mj@delta;depth_after=float(max(0.,(-moved_m[inside]).max())) if len(inside) else 0.
        triangle_after=float(max(0.,(mc[triangle]-moved_m[triangle]).max())) if len(triangle) else 0.
        guard_excess=float((gc-(gg+guard_j@delta)).max()) if len(gg) else 0.
        positive_excess=float((margins[positive_rows]-moved[positive_rows]).max()) if len(positive_rows) else 0.
        parameter_error=float(abs(eq@delta).max()) if eq.shape[0] else 0.
        box_pass=bool(np.all(delta>=step_lo) and np.all(delta<=step_hi));nonzero=bool(np.any(delta!=0))
        records.append(dict(fraction=alpha,original_step_box_pass=box_pass,original_native_maximum_excess=excess,
            material_peak_depth_m=depth_after,worst_legacy_triangle_deficit_m=triangle_after,
            separation_guard_maximum_excess_m=guard_excess,positive_component_maximum_excess_m=positive_excess,
            parameter_maximum_absolute_residual=parameter_error,nonzero_step=nonzero,
            strict_integral_improvement=after<integral,deficit_integral_m_s=after,deficit_sum_m=float(grouped.sum()),
            worst_component_deficit_m=float(grouped.max())))
        if (box_pass and nonzero and excess<=0 and depth_after<=depth and triangle_after<=ceiling
                and guard_excess<=0 and positive_excess<=0 and parameter_error<=1e-9 and after<integral):
            return delta,dict(info,status='ProvisionalStrictTrajectoryCandidate',records=records,selected_fraction=alpha,
                selected_control_step=delta.tolist(),selected_group_deficits_m=grouped.tolist(),selected_deficit_integral_m_s=after,
                selected_deficit_sum_m=float(grouped.sum()),selected_native_maximum_excess=excess,
                selected_material_peak_depth_m=depth_after,selected_worst_legacy_triangle_deficit_m=triangle_after,
                selected_separation_guard_maximum_excess_m=guard_excess,selected_positive_component_maximum_excess_m=positive_excess,
                parameter_maximum_absolute_residual=parameter_error)
    return None,dict(info,status='NoStrictImprovingTrajectoryRay',records=records)
