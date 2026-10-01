"""Rebuild geometry repair from exact accepted internal states with headroom."""
import numpy as np
from hand_norm_proposal import validate, measurement, linearize
from restore_witness_feasibility import hard_margin
from motion_proposal_headroom import solve as repair


def solve(exact, smooth, original, seed, diagnostic, solver, *, witness_start, witness_count,
          iterations=3, observe=None, checkpoint=None):
    original=np.asarray(original,float).copy();point=np.asarray(seed,float).copy()
    if (original.ndim!=1 or not len(original) or point.shape!=original.shape
            or not np.isfinite(original).all() or not np.isfinite(point).all()
            or np.any(abs(original)>1) or np.any(abs(point)>1)
            or type(iterations) is not int or not 1<=iterations<=12):
        raise ValueError('Finite bounded controls and explicit iteration budget required')
    reference={k:v.copy() for k,v in validate(exact(original)).items()};baseline=measurement(reference)
    if (type(witness_start) is not int or type(witness_count) is not int or witness_start<0 or witness_count<1
            or witness_start+witness_count>len(reference['margins'])):
        raise ValueError('Valid geometry witness population required')
    rows=np.arange(witness_start,witness_start+witness_count);ceiling=baseline['witness_peak_m']-1e-9
    if baseline['minimum_margin']<0:raise ValueError('Feasible original required')
    def bound(fn):
        def checked(x):
            value=validate(fn(x))
            if any(value[k].shape!=reference[k].shape for k in reference) or any(
                    not np.array_equal(value[k],reference[k]) for k in ['caps','scales']):
                raise ValueError('Original populations, caps and scales must stay fixed')
            return value
        return checked
    exact,smooth=bound(exact),bound(smooth)
    sample=exact(point);current=measurement(sample);initial=current.copy()
    if hard_margin(sample,rows)<0 or current['witness_peak_m']>ceiling:
        raise ValueError('Hard-feasible improving internal seed required')
    history=[];reason='iteration_budget'
    for iteration in range(1,iterations+1):
        if current['minimum_margin']>=0:reason='numerically_feasible';break
        if np.any(abs(point)+1e-4>1):reason='central_probe_boundary';break
        start=point.copy()
        def progress(n,total):
            if observe:observe(dict(phase='restoration_jacobian',iteration=iteration,coordinates=n,total=total))
        model=linearize(exact,smooth,start,1e-4,progress)
        reserve=2*np.abs(model['base']['margins'][rows]-smooth(start)['margins'][rows])+5e-7
        def event(row):
            if observe:observe(dict(row,iteration=iteration))
        _,report=repair(exact,original,start,model,diagnostic,solver,witness_start=witness_start,
                        witness_count=witness_count,witness_reserve=reserve,observe=event)
        candidate=np.asarray(report['final_point']);value=exact(candidate);metric=measurement(value)
        improved=(np.all(abs(candidate)<=1) and hard_margin(value,rows)>=0
                  and metric['witness_peak_m']<=ceiling and metric['minimum_margin']>current['minimum_margin'])
        row=dict(iteration=iteration,point_before=start.tolist(),before=current,
                 proposal=report['proposal'],trials=report.get('trials',[]),repair=report,
                 internal_step=bool(improved),point_after=(candidate if improved else point).tolist(),
                 after=metric if improved else current)
        history.append(row)
        if checkpoint:checkpoint(model,row)
        if observe:observe(dict(phase='iterated_motion_headroom',iteration=iteration,internal_step=bool(improved),**row['after']))
        if not improved:reason='no_admissible_progress';break
        point,current=candidate.copy(),metric
    final=measurement(exact(point));feasible=final['minimum_margin']>=0
    if feasible:reason='numerically_feasible'
    return (point.copy() if feasible else None),dict(method='iterated_motion_headroom_v1',original=baseline,
        seed=initial,final=final,final_point=point.tolist(),history=history,iterations_limit=iterations,
        stop_reason=reason,numerically_feasible=bool(feasible),mesh_validation_required=True,
        accepted_for_publication=False,quality_approved=False)
