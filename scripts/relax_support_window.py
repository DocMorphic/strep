"""Matched-budget local continuation, preserving all parameters outside a window."""
import numpy as np
from scipy.optimize import least_squares, minimize
from rig_periodic_contact import clip_step, neighbor_constraints


def relax(fitter, initial, first, sweeps=6, progress=None):
    values=np.asarray(initial,dtype=float).copy()
    if values.shape!=(len(fitter.local),len(fitter.bounds)) or not np.isfinite(values).all():
        raise ValueError('Finite full-clip parameter initialization required')
    if not 0<first<len(values) or sweeps<1:
        raise ValueError('Nonempty tail window with a fixed preceding frame required')
    root_step=fitter.spec['limits']['root_step_m']
    joint_step=np.radians(fitter.spec['limits']['joint_step_degrees'])
    if np.any(np.abs(values)>fitter.bounds+1e-8):
        raise ValueError('Initial absolute edit limit exceeded')
    for frame in range(len(values)-1):
        if neighbor_constraints(values[frame],[values[frame+1]],root_step,joint_step)[0].min() < -1e-7:
            raise ValueError('Initial adjacent edit limit exceeded')
    records=[];changes=[]
    for sweep in range(sweeps):
        start=values.copy()
        order=range(first,len(values)) if sweep%2==0 else range(len(values)-1,first-1,-1)
        for frame in order:
            neighbors=[values[n].copy() for n in [frame-1,frame+1] if 0<=n<len(values)]
            old=values[frame].copy();bounds=fitter.bounds;cache=None;cached=None
            def pair(x):
                nonlocal cache,cached
                if cache is None or not np.array_equal(cache,x):
                    cache=x.copy();cached=fitter.objective_pair(frame,x,neighbors)
                return cached
            def objective(x):
                r,j=pair(x);return float(r@r)
            fit=least_squares(lambda x:pair(x)[0],np.clip(old,-bounds+1e-12,bounds-1e-12),
                jac=lambda x:pair(x)[1],bounds=(-bounds,bounds),max_nfev=fitter.spec['max_nfev'],ftol=1e-5,xtol=1e-5,gtol=1e-5)
            projected=clip_step(old,fit.x,neighbors,root_step,joint_step)
            fallback=np.linalg.norm(projected-old)<.95*np.linalg.norm(fit.x-old)
            initial_nfev=int(fit.nfev)
            if fallback:
                fit=minimize(objective,projected,jac=lambda x:2*pair(x)[1].T@pair(x)[0],method='SLSQP',
                    bounds=list(zip(-bounds,bounds)),constraints=dict(type='ineq',
                    fun=lambda x:neighbor_constraints(x,neighbors,root_step,joint_step)[0],
                    jac=lambda x:neighbor_constraints(x,neighbors,root_step,joint_step)[1]),
                    options=dict(maxiter=fitter.spec['max_nfev'],ftol=1e-9))
            candidate=clip_step(old,np.clip(fit.x,-bounds,bounds),neighbors,root_step,joint_step)
            if not np.isfinite(candidate).all():
                raise ValueError('Nonfinite local optimizer proposal')
            before=objective(old);after=before
            for backtrack in range(20):
                trial=old+(candidate-old)*(.5**backtrack);cost=objective(trial)
                if cost<=before:
                    values[frame]=trial;after=cost;break
            records.append(dict(sweep=sweep,frame=frame,success=bool(fit.success),status=int(fit.status),
                nfev=int(fit.nfev),initial_nfev=initial_nfev,constrained_fallback=bool(fallback),cost_before=before,cost_after=after))
        if not np.array_equal(values[:first],np.asarray(initial)[:first]):
            raise ValueError('Parameters before editable window changed')
        changes.append(float(np.abs(values-start).max()))
        if progress:progress(sweep+1,changes[-1])
    return values,records,dict(sweeps=sweeps,changes=changes,stationarity_proven=False,first_editable_frame=first)
