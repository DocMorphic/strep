"""Small linearized descent proposals with unchanged nonlinear safeguards."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix


def direction(x,gradient,constraints,jacobian,bounds,trust,margin=1e-6):
    x,g,c,j,b=map(lambda v:np.asarray(v,float),(x,gradient,constraints,jacobian,bounds))
    if x.ndim!=1 or g.shape!=x.shape or b.shape!=x.shape or c.ndim!=1 or j.shape!=(len(c),len(x)):
        raise ValueError('Matching finite coordinate and constraint arrays required')
    if not all(np.isfinite(v).all() for v in [x,g,c,j,b]) or not np.isfinite([trust,margin]).all() or trust<=0 or margin<0 or np.any(b<=0):
        raise ValueError('Finite inputs and positive bounds/trust required')
    if np.any(np.abs(x)>b+1e-12):raise ValueError('Initial box bound exceeded')
    if np.max(np.abs(g))==0:return None,dict(success=False,reason='Zero objective gradient')
    scaled=j*trust;movable=np.max(np.abs(scaled),axis=1)>1e-12
    if np.any(c[~movable]<-1e-8):return None,dict(success=False,reason='Violated locally constant constraint')
    lower=np.maximum(-1.,(-b-x)/trust);upper=np.minimum(1.,(b-x)/trust)
    fit=linprog(g/np.max(np.abs(g)),A_ub=-csr_matrix(scaled[movable]),b_ub=c[movable]-margin,
        bounds=list(zip(lower,upper)),method='highs',options=dict(primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9,threads=1))
    record=dict(success=bool(fit.success),status=int(fit.status),message=str(fit.message),trust=trust,margin=margin,
        movable_constraints=int(movable.sum()),constant_constraints=int((~movable).sum()))
    if not fit.success:return None,record
    delta=fit.x*trust;record.update(predicted_objective_change=float(g@delta),predicted_minimum_constraint=float((c+j@delta).min()))
    return delta,record


def solve(problem,steps=12,trusts=(1e-4,1e-5,1e-6),margin=1e-6,progress=None):
    x=problem.initial[np.ix_(problem.frames,problem.free)].ravel();initial=x.copy();history=[]
    bounds=np.tile(problem.fitter.bounds[problem.free],len(problem.frames));before=problem.evaluate(x)
    if before[2].min()<-1e-8 or not problem.geometric_guard(before[5]):raise ValueError('Strictly feasible initial motion required')
    for iteration in range(steps):
        current=problem.evaluate(x)
        if current[0]==0.:break
        accepted=False;attempts=[]
        for trust in trusts:
            delta,record=direction(x,current[1],current[2],current[3],bounds,trust,margin);record['trials']=[]
            if delta is not None and record['predicted_objective_change']<0:
                record['proposed_delta']=delta.tolist()
                for i in range(8):
                    alpha=.5**i;trial=problem.evaluate(x+alpha*delta);finite=np.isfinite(trial[0]) and np.isfinite(trial[2]).all()
                    feasible=bool(finite and trial[2].min()>=-1e-8);geometry=problem.geometric_guard(trial[5]) if feasible else False
                    good=bool(feasible and geometry and trial[0]<current[0]-1e-9)
                    record['trials'].append(dict(fraction=alpha,objective=trial[0],minimum_constraint=float(trial[2].min()),geometry=geometry,accepted=good))
                    if good:x+=alpha*delta;accepted=True;break
            attempts.append(record)
            if accepted:break
        history.append(dict(iteration=iteration+1,objective_before=current[0],attempts=attempts,accepted=accepted))
        if progress:progress(dict(iteration=iteration+1,accepted=accepted,objective=problem.evaluate(x)[0]))
        if not accepted:break
    final=problem.evaluate(x)
    return problem.values(x),dict(method='feasible_linear_descent',steps_limit=steps,trusts=list(trusts),margin=margin,history=history,
        starting_coordinates=initial.tolist(),final_coordinates=x.tolist(),variable_frames=problem.frames.tolist(),free_columns=problem.free.tolist(),
        objective_before=before[0],objective_after=final[0],minimum_constraint=float(final[2].min()),target_satisfied=final[0]==0.,quality_approved=False)
