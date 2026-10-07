"""Project a secondary proposal around a verified depth-priority candidate.

Original native norms, absolute control/trust bounds and peak ceiling stay hard.
The checked first-phase step is the retreat anchor; the original pose is not.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_affine_ray_retreat import FRACTIONS


def project(native,native_jacobian,gaps_m,gap_jacobian,witnesses,
            value,lower,upper,trust,baseline_step,target_step,*,parameter_rows=None,
            clearance_m=.0001,scale_m=.005,solver_sink=None):
    value,lower,upper,base,target,gaps=[np.asarray(a,float) for a in
        (value,lower,upper,baseline_step,target_step,gaps_m)]
    vectors,caps,scales=[np.asarray(a,float) for a in (native.vectors,native.caps,native.scales)]
    n=len(value) if value.ndim==1 else 0
    nj,gj=[sparse.csr_matrix(a,copy=True) for a in (native_jacobian,gap_jacobian)]
    eq=sparse.csr_matrix((0,n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows,copy=True)
    if (not 1<=n<=96 or any(a.shape!=(n,) for a in (lower,upper,base,target))
        or vectors.ndim!=2 or vectors.shape[1:]!=(3,) or not len(vectors)
        or caps.shape!=(len(vectors),) or scales.shape!=caps.shape or nj.shape!=(vectors.size,n)
        or gaps.ndim!=1 or not 1<=len(gaps)<=4096 or gj.shape!=(len(gaps),n)
        or eq.shape[1]!=n or eq.shape[0]>96 or nj.nnz+gj.nnz>60_000_000
        or not isinstance(witnesses,list) or len(witnesses)!=len(gaps)
        or any(not isinstance(w,dict) or w.get('kind') not in ('triangle-separation','penetrating-vertex') for w in witnesses)
        or any(not np.isfinite(a).all() for a in (value,lower,upper,base,target,gaps,vectors,caps,scales,nj.data,gj.data,eq.data))
        or np.any(caps<0) or np.any(scales<=0) or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
        or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6<=trust<=.02
        or type(clearance_m) not in (int,float) or not np.isfinite(clearance_m) or not 0<=clearance_m<=.1
        or type(scale_m) not in (int,float) or not np.isfinite(scale_m) or not 1e-6<=scale_m<=1.
        or solver_sink is not None and not callable(solver_sink)):
        raise ValueError('Complete finite original model, indexed witnesses, baseline/target and bounds required')
    ids=np.array([i for i,w in enumerate(witnesses) if w['kind']=='penetrating-vertex'],int)
    if not len(ids) or np.any(gaps[ids]>0):raise ValueError('Complete nonpositive containment witness gaps required')
    lo,hi=np.maximum(-trust,lower-value),np.minimum(trust,upper-value)
    def measures(step):
        moved=vectors+(nj@step).reshape(vectors.shape)
        gap=gaps+gj@step;neg=np.minimum((gap-clearance_m)/scale_m,0.)
        return (float(((np.linalg.norm(moved,axis=1)-caps)/scales).max()),
            float(max(0.,(-gap[ids]).max())),float(neg@neg),
            float(abs(eq@step).max()) if eq.shape[0] else 0.)
    excess,ceiling,loss,parameter=measures(base)
    info=dict(schema='strep-native-material-priority-projection-v1',status='not-solved',records=[],
        controls=n,original_norm_rows=len(caps),complete_guide_rows=len(gaps),parameter_rows=eq.shape[0],
        containment_rows=ids.tolist(),baseline_control_step=base.tolist(),target_control_step=target.tolist(),
        verified_depth_ceiling_m=ceiling,baseline_complete_guide_squared_deficit=loss,
        baseline_native_maximum_excess=excess,baseline_parameter_maximum_absolute_residual=parameter,
        all_original_rows_columns_caps_scales_retained=True,absolute_original_trust_box_retained=True,
        solver_optimality_verified=False,parameter_proposal_tolerance=1e-9,
        depth_priority_acceptance_allowance_m=0.,native_acceptance_allowance=0.,
        quality_approved=False,release_approved=False,
        scope='Nearest secondary control proposal with every original native norm and absolute control/trust '
            'box hard, complete parameter equations and all declared depth inequalities. Retreat is toward '
            'a separately checked first-phase candidate. No changed depth ceiling, affine optimum, '
            'actual stored-motion/geometry, collision, engine or human-quality approval.')
    if np.any(base<lo) or np.any(base>hi) or excess>0 or parameter>1e-9:
        return None,dict(info,status='BaselineNotStrictlyVerified')
    if np.any(target<lo-1e-9) or np.any(target>hi+1e-9):
        return None,dict(info,status='TargetOutsideOriginalBox')
    nj.eliminate_zeros();count=np.diff(nj.indptr).reshape(-1,3).sum(axis=1);active=np.flatnonzero(count!=0)
    solver=solver_module();anchored=vectors+(nj@base).reshape(vectors.shape)
    # Corrections may range across the entire original box (up to +/-2 in
    # normalized units); no narrower trust box is imposed around the baseline.
    mats=[sparse.eye(n,format='csc'),-sparse.eye(n,format='csc')]
    rhs=[(hi-base)/trust,-(lo-base)/trust];cones=[solver.NonnegativeConeT(2*n)]
    if eq.shape[0]:
        mats.append(eq*trust);rhs.append(-eq@base);cones.append(solver.ZeroConeT(eq.shape[0]))
    original_ids=(3*active[:,None]+np.arange(3)).ravel()
    d=nj[original_ids].multiply((-trust/np.repeat(scales[active],3))[:,None]).tocoo()
    mats.append(sparse.csc_matrix((d.data,(4*(d.row//3)+1+d.row%3,d.col)),shape=(4*len(active),n)))
    rhs.append((np.c_[caps[active],anchored[active]]/scales[active,None]).ravel())
    cones.extend(solver.SecondOrderConeT(4) for _ in active)
    mats.append(-trust/scale_m*gj[ids]);rhs.append((gaps[ids]+gj[ids]@base+ceiling)/scale_m)
    cones.append(solver.NonnegativeConeT(len(ids)))
    P=sparse.eye(n,format='csc');q=-(target-base)/trust;A=sparse.vstack(mats,format='csc');b=np.concatenate(rhs)
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_feas=settings.tol_gap_abs=settings.tol_gap_rel=1e-11
    if hasattr(settings,'max_threads'):settings.max_threads=1
    solution=solver.DefaultSolver(P,q,A,b,cones,settings).solve();point=np.asarray(solution.x,float)
    info.update(solver_status=str(solution.status),solver_version=solver.__version__,solver_iterations=solution.iterations,
        returned_correction=point.tolist(),active_original_norm_cones=len(active),
        omitted_exactly_fixed_passing_norms=int((count==0).sum()))
    if solver_sink is not None:
        solver_sink(dict(quadratic=P.copy(),linear=q.copy(),matrix=A.copy(),rhs=b.copy(),cones=[str(c) for c in cones]))
    if str(solution.status) not in ('Solved','AlmostSolved','InsufficientProgress','MaxIterations','MaxTime'):
        return None,dict(info,status='NotMotionIterateStatus')
    if point.shape!=(n,) or not np.isfinite(point).all():return None,dict(info,status='InvalidReturnedCorrection')
    raw=base+trust*point;info['raw_control_step']=raw.tolist()
    if np.any(raw<lo-1e-9) or np.any(raw>hi+1e-9):return None,dict(info,status='CorrectionOutsideOriginalBox')
    for alpha in FRACTIONS:
        step=np.clip(base+alpha*(raw-base),lo,hi)
        step=np.clip(value+step,lower,upper)-value
        e,depth,after,pe=measures(step)
        inside=bool(np.all(step>=lo) and np.all(step<=hi));changed=bool(np.any(step!=base))
        record=dict(fraction=alpha,original_step_box_pass=inside,original_native_maximum_excess=e,
            material_peak_depth_m=depth,complete_guide_squared_deficit=after,parameter_maximum_absolute_residual=pe,
            changed_from_baseline=changed,strict_depth_priority_pass=depth<=ceiling,
            strict_complete_guide_improvement=after<loss)
        info['records'].append(record)
        if inside and e<=0 and depth<=ceiling and pe<=1e-9 and changed and after<loss:
            return step,dict(info,status='ProvisionalStrictPriorityProjection',selected_fraction=alpha,
                selected_control_step=step.tolist(),selected_material_peak_depth_m=depth,
                selected_complete_guide_squared_deficit=after)
    return None,dict(info,status='NoStrictImprovingProjectedProposal')
