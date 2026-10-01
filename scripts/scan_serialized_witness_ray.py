"""Replay a saved proposal on a fixed grid using unchanged real constraints."""
import numpy as np
from hand_norm_proposal import validate, measurement
from restore_witness_feasibility import hard_margin


def scan(exact,original,seed,delta,*,witness_start,witness_count,divisions=256,observe=None):
    original=np.asarray(original,float);seed=np.asarray(seed,float);delta=np.asarray(delta,float)
    if (original.ndim!=1 or not len(original) or seed.shape!=original.shape or delta.shape!=seed.shape
            or not all(np.isfinite(v).all() for v in [original,seed,delta]) or np.any(abs(original)>1) or np.any(abs(seed)>1)
            or type(divisions) is not int or not 8<=divisions<=1024):raise ValueError('Finite controls, matching ray and bounded grid required')
    reference={k:v.copy() for k,v in validate(exact(original)).items()};baseline=measurement(reference)
    if (type(witness_start) is not int or type(witness_count) is not int or witness_start<0 or witness_count<1
            or witness_start+witness_count>len(reference['margins'])):raise ValueError('Valid witness rows required')
    rows=np.arange(witness_start,witness_start+witness_count);ceiling=baseline['witness_peak_m']-1e-9
    if baseline['minimum_margin']<0:raise ValueError('Feasible original required')
    def checked(x):
        value=validate(exact(x))
        if any(value[k].shape!=reference[k].shape for k in reference) or any(not np.array_equal(value[k],reference[k]) for k in ['caps','scales']):
            raise ValueError('Original population, caps and scales must remain fixed')
        return value
    initial=checked(seed);before=measurement(initial)
    if hard_margin(initial,rows)<0 or before['witness_peak_m']>ceiling:raise ValueError('Motion-feasible improving seed required')
    best=before;point=seed.copy();trials=[]
    for numerator in range(1,divisions+1):
        fraction=numerator/divisions;candidate=seed+fraction*delta
        if np.any(abs(candidate)>1):row=dict(fraction=fraction,eligible=False,reason='control bounds')
        else:
            try:value=checked(candidate)
            except ValueError as error:
                if 'outside two-bone reach' not in str(error):raise
                row=dict(fraction=fraction,eligible=False,reason='outside two-bone reach')
            else:
                metric=measurement(value);hard=hard_margin(value,rows);eligible=hard>=0 and metric['witness_peak_m']<=ceiling
                row=dict(fraction=fraction,eligible=bool(eligible),hard_minimum_margin=hard,
                    failed_witnesses=int(np.count_nonzero(value['margins'][rows]<0)),**metric)
                if eligible and metric['minimum_margin']>best['minimum_margin']:point=candidate.copy();best=metric
        trials.append(row)
        if observe and (numerator%16==0 or numerator==divisions):observe(dict(phase='serialized_ray',completed=numerator,total=divisions,**best))
    feasible=best['minimum_margin']>=0
    return (point.copy() if feasible else None),dict(method='serialized_witness_ray_v1',original=baseline,seed=before,
        final=best,final_point=point.tolist(),delta=delta.tolist(),divisions=divisions,trials=trials,
        numerically_feasible=bool(feasible),objective_ceiling_m=float(ceiling),mesh_validation_required=True,
        accepted_for_publication=False,quality_approved=False)
