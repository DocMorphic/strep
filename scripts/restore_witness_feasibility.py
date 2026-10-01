"""Repair surface witnesses while keeping every already-feasible group hard."""
import numpy as np
from scipy import sparse
from hand_norm_proposal import validate, measurement, linearize
from restore_hand_feasibility import assemble as elastic_assemble


def assemble(model, trust, objective_ceiling, rows, reserve):
    base = validate(model['base']); rows = np.asarray(rows); reserve = np.asarray(reserve, float)
    if (rows.ndim != 1 or not len(rows) or not np.issubdtype(rows.dtype, np.integer)
            or len(np.unique(rows)) != len(rows) or rows.min() < 0 or rows.max() >= len(base['margins'])
            or reserve.shape != rows.shape or not np.isfinite(reserve).all() or np.any(reserve < 0)):
        raise ValueError('Distinct surface rows and finite nonnegative proposal reserves required')
    matrix, rhs, record = elastic_assemble(model, trust, objective_ceiling)
    # The shared assembly puts scalar margins first. Keep only selected witness
    # slack and t >= 0; vector cones and every other scalar remain hard.
    column = np.zeros(matrix.shape[0]); column[rows] = -1.
    column[record['linear_rows']-1] = -1.
    matrix = sparse.hstack([matrix[:, :-1], sparse.csc_matrix(column[:, None])], format='csc')
    rhs[rows] -= reserve
    return matrix, rhs, dict(record, witness_rows=rows.tolist(), reserve=reserve.tolist())


def direction(model, trust, ceiling, rows, reserve, solver):
    a,b,record=assemble(model,trust,ceiling,rows,reserve);width=len(model['point'])
    cones=[solver.NonnegativeConeT(record['linear_rows'])]+[solver.SecondOrderConeT(4) for _ in record['retained_norm_rows']]
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-12
    if hasattr(settings,'max_threads'):settings.max_threads=1
    result=solver.DefaultSolver(sparse.diags(np.r_[np.repeat(1e-12,width),0.],format='csc'),
        np.r_[np.zeros(width),1.],a,b,cones,settings).solve();z=np.asarray(result.x)
    record.update(status=str(result.status),iterations=result.iterations,
        retained_norm_count=len(record.pop('retained_norm_rows')),retained_depth_count=len(record.pop('retained_depth_rows')))
    if str(result.status) not in ['Solved','AlmostSolved'] or z.shape!=(width+1,) or not np.isfinite(z).all():return None,record
    delta=z[:-1]*trust
    if np.any(abs(delta)>trust+1e-12) or np.any(abs(model['point']+delta)>1):return None,dict(record,rejected='control bounds')
    return delta,dict(record,proposal_slack=float(z[-1]),delta=delta.tolist())


def hard_margin(sample, rows):
    keep=np.ones(len(sample['margins']),bool);keep[rows]=False
    scalar=float(sample['margins'][keep].min()) if np.any(keep) else np.inf
    return min(scalar,float(((sample['caps']-np.linalg.norm(sample['vectors'],axis=1))/sample['scales']).min()))


def restore(exact,smooth,original,seed,solver,*,witness_start,witness_count,iterations=3,trust=.001,step=1e-4,
            reserve_floor=5e-7,observe=None,checkpoint=None):
    original=np.asarray(original,float).copy();point=np.asarray(seed,float).copy()
    if (original.ndim!=1 or not len(original) or point.shape!=original.shape or not np.isfinite(original).all()
            or not np.isfinite(point).all() or np.any(abs(original)>1) or np.any(abs(point)>1)
            or type(iterations) is not int or not 1<=iterations<=12 or not np.isfinite(trust) or not 0<trust<=1
            or not np.isfinite(step) or not 0<step<1 or not np.isfinite(reserve_floor) or reserve_floor<0):
        raise ValueError('Finite bounded controls and explicit repair settings required')
    reference={k:v.copy() for k,v in validate(exact(original)).items()};baseline=measurement(reference)
    if (type(witness_start) is not int or type(witness_count) is not int or witness_start<0 or witness_count<1
            or witness_start+witness_count>len(reference['margins'])):raise ValueError('Valid surface witness range required')
    rows=np.arange(witness_start,witness_start+witness_count)
    if baseline['minimum_margin']<0:raise ValueError('Original controls must be feasible')
    ceiling=baseline['witness_peak_m']-1e-9
    def bound(fn):
        def evaluate(x):
            value=validate(fn(x))
            if any(value[k].shape!=reference[k].shape for k in reference) or any(not np.array_equal(value[k],reference[k]) for k in ['caps','scales']):
                raise ValueError('Original population, caps and scales must remain fixed')
            return value
        return evaluate
    exact,smooth=bound(exact),bound(smooth);sample=exact(point);current=measurement(sample);initial=current.copy()
    if hard_margin(sample,rows)<0 or current['witness_peak_m']>ceiling:
        raise ValueError('Seed must preserve all non-witness limits and original objective improvement')
    history=[];reason='restoration_budget'
    for iteration in range(iterations):
        if current['minimum_margin']>=0:reason='numerically_feasible';break
        if np.any(abs(point)+step>1):reason='central_probe_boundary';break
        def progress(n,total):
            if observe:observe(dict(phase='restoration_jacobian',iteration=iteration+1,coordinates=n,total=total))
        model=linearize(exact,smooth,point,step,progress)
        # Reserve is a proposal target, never an acceptance tolerance or proof
        # of rounding error throughout a trust region.
        discrepancy=np.abs(model['base']['margins'][rows]-smooth(point)['margins'][rows])
        reserve=2*discrepancy+reserve_floor
        delta,proposal=direction(model,trust,ceiling,rows,reserve,solver);selected=None;best=current;trials=[]
        if delta is not None:
            for fraction in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
                candidate=point+fraction*delta
                if np.any(abs(candidate)>1):trials.append(dict(fraction=fraction,eligible=False,reason='control bounds'));continue
                try:value=exact(candidate)
                except ValueError as error:
                    if 'outside two-bone reach' not in str(error):raise
                    trials.append(dict(fraction=fraction,eligible=False,reason='outside two-bone reach'));continue
                metric=measurement(value);hard=hard_margin(value,rows)
                eligible=hard>=0 and metric['witness_peak_m']<=ceiling
                trials.append(dict(fraction=fraction,eligible=bool(eligible),hard_minimum_margin=hard,
                    failed_witnesses=int(np.count_nonzero(value['margins'][rows]<0)),**metric))
                if eligible and metric['minimum_margin']>best['minimum_margin']:selected=candidate.copy();best=metric
        row=dict(iteration=iteration+1,point_before=point.tolist(),before=current,proposal=proposal,trials=trials,
            internal_step=selected is not None,point_after=(point if selected is None else selected).tolist(),after=best)
        history.append(row)
        if checkpoint:checkpoint(model,row)
        if observe:observe(dict(phase='witness_restoration',iteration=iteration+1,internal_step=row['internal_step'],**best))
        if selected is None:reason='no_admissible_violation_reduction';break
        point,current=selected,best
    final=measurement(exact(point));feasible=final['minimum_margin']>=0 and final['witness_peak_m']<=ceiling
    if feasible:reason='numerically_feasible'
    return (point.copy() if feasible else None),dict(method='hard_motion_witness_restoration_v1',original=baseline,seed=initial,
        final=final,final_point=point.tolist(),history=history,stop_reason=reason,iterations_limit=iterations,trust=float(trust),
        objective_ceiling_m=float(ceiling),reserve_floor=float(reserve_floor),witness_rows=rows.tolist(),numerically_feasible=bool(feasible),
        mesh_validation_required=True,accepted_for_publication=False,quality_approved=False)
