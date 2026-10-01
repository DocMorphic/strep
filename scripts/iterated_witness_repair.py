"""Relinearize serialized witness repair, with bounded exact-ray fallback."""
import numpy as np
from hand_norm_proposal import validate, measurement
from restore_witness_feasibility import restore, hard_margin
from scan_serialized_witness_ray import scan


def solve(exact,smooth,original,seed,solver,*,witness_start,witness_count,iterations=3,
          trust=.001,divisions=256,observe=None,checkpoint=None):
    original=np.asarray(original,float).copy();point=np.asarray(seed,float).copy()
    if (original.ndim!=1 or not len(original) or point.shape!=original.shape or not np.isfinite(original).all()
            or not np.isfinite(point).all() or np.any(abs(original)>1) or np.any(abs(point)>1)
            or type(iterations) is not int or not 1<=iterations<=12 or type(divisions) is not int or not 8<=divisions<=1024
            or not np.isfinite(trust) or not 0<trust<=1):raise ValueError('Finite bounded controls and explicit search budget required')
    reference={k:v.copy() for k,v in validate(exact(original)).items()};baseline=measurement(reference)
    if (type(witness_start) is not int or type(witness_count) is not int or witness_start<0 or witness_count<1
            or witness_start+witness_count>len(reference['margins'])):raise ValueError('Valid witness range required')
    rows=np.arange(witness_start,witness_start+witness_count);ceiling=baseline['witness_peak_m']-1e-9
    if baseline['minimum_margin']<0:raise ValueError('Feasible original required')
    def bound(fn):
        def checked(x):
            value=validate(fn(x))
            if any(value[k].shape!=reference[k].shape for k in reference) or any(not np.array_equal(value[k],reference[k]) for k in ['caps','scales']):
                raise ValueError('Original population, caps and scales must remain fixed across iterations')
            return value
        return checked
    exact,smooth=bound(exact),bound(smooth);initial_sample=exact(point);current=measurement(initial_sample);initial=current.copy()
    if hard_margin(initial_sample,rows)<0 or current['witness_peak_m']>ceiling:raise ValueError('Motion-feasible improving seed required')
    history=[];reason='iteration_budget'
    for iteration in range(1,iterations+1):
        if current['minimum_margin']>=0:reason='numerically_feasible';break
        start=point.copy()
        def progress(row):
            if observe:observe(dict(row,iteration=iteration))
        def save_model(model,row):
            if checkpoint:checkpoint(model,dict(row,iteration=iteration))
        _,local=restore(exact,smooth,original,start,solver,witness_start=witness_start,witness_count=witness_count,
            iterations=1,trust=trust,observe=progress,checkpoint=save_model)
        chosen=local;ray=None
        if local['final']['minimum_margin']<=current['minimum_margin'] and local['history']:
            proposal=local['history'][0]['proposal']
            if 'delta' in proposal:
                _,ray=scan(exact,original,start,proposal['delta'],witness_start=witness_start,witness_count=witness_count,
                    divisions=divisions,observe=progress)
                if ray['final']['minimum_margin']>chosen['final']['minimum_margin']:chosen=ray
        candidate=np.asarray(chosen['final_point']);value=exact(candidate);metric=measurement(value)
        # Independently enforce the hard groups even across solver/replay stages.
        admissible=(np.all(abs(candidate)<=1) and hard_margin(value,rows)>=0 and metric['witness_peak_m']<=ceiling)
        improved=admissible and metric['minimum_margin']>current['minimum_margin']
        history.append(dict(iteration=iteration,point_before=start.tolist(),before=current,local=local,ray=ray,
            internal_step=bool(improved),point_after=(candidate if improved else point).tolist(),after=metric if improved else current))
        if observe:observe(dict(phase='continued_witness_repair',iteration=iteration,internal_step=bool(improved),**(metric if improved else current)))
        if not improved:reason='no_admissible_progress';break
        point,current=candidate.copy(),metric
    final=measurement(exact(point));feasible=final['minimum_margin']>=0
    if feasible:reason='numerically_feasible'
    return (point.copy() if feasible else None),dict(method='iterated_serialized_witness_repair_v1',original=baseline,seed=initial,
        final=final,final_point=point.tolist(),history=history,iterations_limit=iterations,trust=float(trust),divisions=divisions,
        stop_reason=reason,numerically_feasible=bool(feasible),mesh_validation_required=True,accepted_for_publication=False,quality_approved=False)
