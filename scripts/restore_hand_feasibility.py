"""Restore rejected serialized controls without relaxing any original cap.

Elastic slack exists only in the proposal problem. Every real acceptance check
uses the original zero-slack constraints; internal infeasible iterates are not
accepted animations.
"""
import numpy as np
from scipy import sparse
from hand_norm_proposal import validate, measurement, linearize


def assemble(model,trust,objective_ceiling):
    base=validate(model['base']);point=np.asarray(model['point'],float);jac=model['jacobian'];width=len(point)
    if point.ndim!=1 or not width or not np.isfinite(point).all() or np.any(abs(point)>1) or not np.isfinite(trust) or not 0<trust<=1 or not np.isfinite(objective_ceiling) or objective_ceiling<0:
        raise ValueError('Bounded controls, positive trust and finite objective ceiling required')
    for key in ['vectors','margins','depths']:
        if jac[key].shape!=base[key].shape+(width,) or not np.isfinite(jac[key]).all():raise ValueError('Matching finite derivatives required')
    lower=np.maximum(-1.,(-1.-point)/trust);upper=np.minimum(1.,(1.-point)/trust)
    box=np.maximum(abs(lower),abs(upper))*trust
    depth_reach=np.abs(jac['depths'])@box
    depth_reserve=4*(width+4)*np.finfo(float).eps*np.maximum(1.,abs(base['depths'])+depth_reach+objective_ceiling)+1e-12
    depth_keep=np.flatnonzero(base['depths']+depth_reach+depth_reserve>=objective_ceiling)
    def block(matrix,last):return sparse.hstack([sparse.csc_matrix(matrix),sparse.csc_matrix(np.asarray(last).reshape(-1,1))],format='csc')
    mats=[block(-jac['margins']*trust,-np.ones(len(base['margins']))),block(np.eye(width),np.zeros(width)),
        block(-np.eye(width),np.zeros(width)),block(jac['depths'][depth_keep]*trust/.02,np.zeros(len(depth_keep))),
        sparse.csc_matrix(np.r_[np.zeros(width),-1.][None,:])]
    rhs=[base['margins'],upper,-lower,(objective_ceiling-base['depths'][depth_keep])/.02,np.zeros(1)]
    linear_count=sum(len(v) for v in rhs)
    magnitude=np.linalg.norm(base['vectors'],axis=1)
    reach=(np.linalg.norm(jac['vectors'],axis=1)*np.maximum(abs(lower),abs(upper))*trust).sum(axis=1)
    reserve=4*(width+4)*np.finfo(float).eps*np.maximum(1.,magnitude+reach+base['caps'])+1e-12
    keep=np.flatnonzero(magnitude+reach+reserve>=base['caps'])
    for row in keep:
        matrix=np.vstack([np.zeros(width),-jac['vectors'][row]*trust])/base['scales'][row]
        mats.append(block(matrix,[-1.,0.,0.,0.]));rhs.append(np.r_[base['caps'][row],base['vectors'][row]]/base['scales'][row])
    return sparse.vstack(mats,format='csc'),np.concatenate(rhs),dict(linear_rows=linear_count,retained_norm_rows=keep.tolist(),
        retained_depth_rows=depth_keep.tolist(),trust=float(trust),objective_ceiling_m=float(objective_ceiling))


def direction(model,trust,objective_ceiling,solver):
    a,b,record=assemble(model,trust,objective_ceiling);width=len(model['point'])
    cones=[solver.NonnegativeConeT(record['linear_rows'])]+[solver.SecondOrderConeT(4) for _ in record['retained_norm_rows']]
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-12
    if hasattr(settings,'max_threads'):settings.max_threads=1
    p=sparse.diags(np.r_[np.repeat(1e-12,width),0.],format='csc')
    result=solver.DefaultSolver(p,np.r_[np.zeros(width),1.],a,b,cones,settings).solve();z=np.asarray(result.x)
    record.update(status=str(result.status),iterations=result.iterations,retained_norm_count=len(record.pop('retained_norm_rows')),
        retained_depth_count=len(record.pop('retained_depth_rows')))
    if str(result.status) not in ['Solved','AlmostSolved'] or z.shape!=(width+1,) or not np.isfinite(z).all():return None,record
    delta=z[:-1]*trust
    if np.any(abs(delta)>trust+1e-12) or np.any(abs(model['point']+delta)>1):return None,dict(record,rejected='control bounds')
    return delta,dict(record,proposal_slack=float(z[-1]),delta=delta.tolist())


def restore(exact,smooth,original,seed,solver,*,iterations=3,trust=.001,step=1e-4,observe=None,checkpoint=None):
    original=np.asarray(original,float).copy();point=np.asarray(seed,float).copy()
    if (original.ndim!=1 or not len(original) or point.shape!=original.shape or not np.isfinite(original).all() or not np.isfinite(point).all()
            or np.any(abs(original)>1) or np.any(abs(point)>1) or type(iterations) is not int or not 1<=iterations<=12
            or not np.isfinite(trust) or not 0<trust<=1 or not np.isfinite(step) or not 0<step<1):
        raise ValueError('Finite bounded controls and explicit restoration budget required')
    reference={k:v.copy() for k,v in validate(exact(original)).items()};baseline=measurement(reference)
    if baseline['minimum_margin']<0:raise ValueError('Original controls must be feasible')
    ceiling=baseline['witness_peak_m']-1e-9
    if ceiling<0:raise ValueError('Original objective has no improvement budget')
    def bound(fn):
        def evaluate(x):
            value=validate(fn(x))
            if any(value[k].shape!=reference[k].shape for k in reference) or any(not np.array_equal(value[k],reference[k]) for k in ['caps','scales']):
                raise ValueError('Original population, caps and scales must remain fixed')
            return value
        return evaluate
    exact,smooth=bound(exact),bound(smooth);current=measurement(exact(point));initial=current.copy()
    if current['witness_peak_m']>ceiling:raise ValueError('Restoration seed must improve the original objective')
    history=[];reason='restoration_budget'
    for iteration in range(iterations):
        if current['minimum_margin']>=0:reason='numerically_feasible';break
        if np.any(abs(point)+step>1):reason='central_probe_boundary';break
        def progress(n,total):
            if observe:observe(dict(phase='restoration_jacobian',iteration=iteration+1,coordinates=n,total=total))
        model=linearize(exact,smooth,point,step,progress)
        delta,proposal=direction(model,trust,ceiling,solver);selected=None;best=current;trials=[]
        if delta is not None:
            for fraction in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
                candidate=point+fraction*delta
                if np.any(abs(candidate)>1):trials.append(dict(fraction=fraction,eligible=False,reason='control bounds'));continue
                try:metric=measurement(exact(candidate))
                except ValueError as error:
                    if 'outside two-bone reach' not in str(error):raise
                    trials.append(dict(fraction=fraction,eligible=False,reason='outside two-bone reach'));continue
                eligible=metric['witness_peak_m']<=ceiling
                improves=eligible and metric['minimum_margin']>best['minimum_margin']
                trials.append(dict(fraction=fraction,eligible=bool(eligible),**metric))
                if improves:selected=candidate.copy();best=metric
        row=dict(iteration=iteration+1,point_before=point.tolist(),before=current,proposal=proposal,trials=trials,
            internal_step=selected is not None,point_after=(point if selected is None else selected).tolist(),after=best)
        history.append(row)
        if checkpoint:checkpoint(model,row)
        if observe:observe(dict(phase='restoration',iteration=iteration+1,internal_step=row['internal_step'],**best))
        if selected is None:reason='no_violation_reduction';break
        point,current=selected,best
    final=measurement(exact(point));feasible=final['minimum_margin']>=0 and final['witness_peak_m']<=ceiling
    if feasible:reason='numerically_feasible'
    return (point.copy() if feasible else None),dict(method='serialized_feasibility_restoration_v1',original=baseline,seed=initial,
        final=final,final_point=point.tolist(),history=history,stop_reason=reason,iterations_limit=iterations,trust=float(trust),
        objective_ceiling_m=float(ceiling),numerically_feasible=bool(feasible),mesh_validation_required=True,
        accepted_for_publication=False,quality_approved=False)
