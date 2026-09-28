"""Select every fresh frame-cap violation without weakening the seed budget."""
import copy
import numpy as np


def select(records,actual_depths,seed_depths,cap,violation_tolerance=1e-9):
    count=sum(len(r['points']) for r in records)
    actual=np.asarray(actual_depths,float);seed=np.asarray(seed_depths,float)
    if actual.shape!=(count,) or seed.shape!=(count,) or not np.isfinite(np.r_[actual,seed,cap,violation_tolerance]).all():
        raise ValueError('Finite matching depth arrays and cap required')
    if cap<0 or violation_tolerance<0:raise ValueError('Nonnegative cap and tolerance required')
    selected=[];infeasible=[];summaries=[];offset=0
    for r in records:
        out=copy.deepcopy(r);out['points']=[]
        for point in r['points']:
            if actual[offset]>cap+violation_tolerance:
                out['points'].append(copy.deepcopy(point))
                row=dict(source=r['source'],target=r['target'],vertex=point[0],actual_depth_m=float(actual[offset]),
                    seed_projected_depth_m=float(seed[offset]),frame_cap_m=float(cap))
                summaries.append(row)
                # Same scaled 1e-8 seed tolerance as the existing restoration
                # solver: metre-valued surface rows are divided by .03.
                if seed[offset]>cap+3e-10:infeasible.append(row)
            offset+=1
        selected.append(out)
    return selected,dict(selected_rows=len(summaries),seed_feasible=not infeasible,rows=summaries,infeasible_seed_rows=infeasible)
