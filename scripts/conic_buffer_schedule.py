"""Fixed proposal-buffer schedule; actual serialized acceptance is unchanged."""
import numpy as np
from conic_root_descent import direction


def solve(p,steps,trusts,progress,buffers,schedule):
    x=p.initial[np.ix_(p.frames,p.free)].ravel();initial=x.copy();before=p.evaluate(x);history=[]
    if before[2].min()<-1e-8 or not p.geometric_guard(before[5]):raise ValueError('Strictly feasible source required')
    for iteration in range(steps):
        current=p.evaluate(x)
        if current[0]==0.:break
        attempts=[];accepted=False
        for entry in schedule:
            trust=entry['trust'];chosen={k:v*entry['buffer_scale'] for k,v in buffers.items()}
            delta,record=direction(p,x,trust,chosen);record['trials']=[];record['buffer_scale']=entry['buffer_scale']
            if delta is not None and record['predicted_objective_change']<0:
                record['proposed_delta']=delta.tolist()
                for index in range(8):
                    alpha=.5**index;trial=p.evaluate(x+alpha*delta)
                    feasible=bool(np.isfinite(trial[0]) and np.isfinite(trial[2]).all() and trial[2].min()>=-1e-8)
                    geometry=p.geometric_guard(trial[5]) if feasible else False;good=bool(feasible and geometry and trial[0]<current[0]-1e-9)
                    record['trials'].append(dict(fraction=alpha,objective=trial[0],minimum_constraint=float(trial[2].min()),geometry=geometry,accepted=good))
                    if good:x+=alpha*delta;accepted=True;break
            attempts.append(record)
            if accepted:break
        history.append(dict(iteration=iteration+1,objective_before=current[0],attempts=attempts,accepted=accepted))
        if progress:progress(dict(iteration=iteration+1,accepted=accepted,objective=p.evaluate(x)[0]))
        if not accepted:break
    final=p.evaluate(x)
    return p.values(x),dict(method='scheduled_conic_descent',steps_limit=steps,trusts=list(trusts),proposal_buffers=buffers or {},history=history,
        starting_coordinates=initial.tolist(),final_coordinates=x.tolist(),variable_frames=p.frames.tolist(),free_columns=p.free.tolist(),
        objective_before=before[0],objective_after=final[0],minimum_constraint=float(final[2].min()),target_satisfied=final[0]==0.,quality_approved=False)
