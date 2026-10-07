"""Staged sampled correction with explicit unchanged original material ceilings.

This separate opt-in solver preserves the original solver's hard native,
component, mesh, edit, trust and parameter conditions. Caller-authenticated
ceilings survive pose changes; affine proposals require actual export checks.
No empirical margin, nonlinear collision or source approval is inferred.
"""
import copy
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_scene_conic import solver_module
from native_affine_ray_retreat import FRACTIONS
from native_component_trajectory_step import _trajectory
from native_triangle_separation_guards import SeparationGuards


def direction(native,native_jacobian,trajectory,value,lower,upper,trust,*,separation_guards,
              material_gaps_m,material_gap_jacobian,material_witnesses,material_clearances_m,
              material_depth_ceiling_m,material_triangle_deficit_ceiling_m,
              parameter_rows=None,scale_m=.005,solver_sink=None):
    """Reduce clock-weighted complete support deficits with original hard bounds.

Keep native norms, edit/trust box, equalities, full-mesh guards and every
initially clear component sample. Legacy containment/triangle rows retain
caller-bound original ceilings and their separate4096-row population limit.
Ceilings are mandatory and never reset to the current staged anchor. The
caller authenticates their provenance; this API does not infer it.
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
    anchor_depth,anchor_triangle=depth,ceiling
    for name,cap in (('depth',material_depth_ceiling_m),('triangle deficit',material_triangle_deficit_ceiling_m)):
        if type(cap) not in (int,float) or not np.isfinite(cap) or not 0.<=cap<=.1:
            raise ValueError('Explicit finite original material '+name+' ceiling required')
    depth=float(material_depth_ceiling_m);ceiling=float(material_triangle_deficit_ceiling_m)
    def deficits(moved):return np.array([max(0.,float((margins[ids]-moved[ids]).max())) for ids in groups])
    before=deficits(gaps);integral=float(before@weights)
    anchor=float(((np.linalg.norm(vectors,axis=1)-caps)/scales).max())
    info=dict(schema='strep-native-component-trajectory-fixed-ceiling-step-v1',status='not-solved',controls=n,original_norm_rows=len(caps),
        complete_component_rows=len(gaps),component_group_count=len(groups),positive_component_rows=len(positive_rows),
        trajectory_coverage=copy.deepcopy(trajectory.report),component_groups=copy.deepcopy(trajectory.groups),
        initial_group_deficits_m=before.tolist(),initial_deficit_integral_m_s=integral,initial_deficit_sum_m=float(before.sum()),
        objective='Normalized original-clock trapezoidal integral of complete component/time worst deficits.',
        material_rows=len(mg),triangle_rows=triangle.tolist(),containment_rows=inside.tolist(),material_witnesses=copy.deepcopy(material_witnesses),
        original_material_depth_ceiling_m=depth,original_triangle_deficit_ceiling_m=ceiling,
        initial_material_depth_m=anchor_depth,initial_triangle_deficit_m=anchor_triangle,
        material_ceilings_recomputed_from_anchor=False,ceiling_provenance_verified=False,
        complete_separation_guard_rows=len(gg),separation_guard_partition=copy.deepcopy(separation_guards.report),
        guard_descriptors=copy.deepcopy(separation_guards.descriptors),parameter_rows=eq.shape[0],scale_m=scale_m,
        original_anchor_maximum_excess=anchor,strict_native_acceptance_tolerance=0.,strict_guard_tolerance_m=0.,
        strict_material_depth_tolerance_m=0.,parameter_proposal_tolerance=1e-9,
        original_caps_scales_clocks_unchanged=True,all_original_native_rows_columns_retained=True,
        all_trajectory_rows_times_columns_retained=True,solver_statuses_preserved=True,solver_optimality_verified=False,
        quality_approved=False,release_approved=False,
        scope='Complete sampled component objective under original hard native/control/trust/parameter conditions, '
              'explicit caller-bound original material ceilings and complete full-mesh guards. Every initially positive component '
              'pair row remains hard without objective slack. All81 strict ray checks preserve statuses. '
              'Caller binds source/clock/fresh same-pose derivatives; actual stored motion, references, contacts '
              'and full original scene checks remain decisive. No nonlinear or between-sample certificate.')
    if anchor_depth>depth or anchor_triangle>ceiling:
        return None,dict(info,status='OriginalMaterialCeilingsNotPassingAtAnchor')
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
