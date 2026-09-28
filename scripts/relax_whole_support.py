"""Whole-clip bounded fitting with the verified root-curvature coordinate term."""
import numpy as np
from scipy.optimize import least_squares, minimize
from rig_periodic_contact import clip_step, neighbor_constraints
from support_curvature import root_curvature_pair,root_curvature_energy


def relax(fitter, initial, curvature_weight=10., sweeps=6, progress=None):
    values=np.asarray(initial,dtype=float).copy()
    first,last=0,len(values)-1
    if values.shape!=(len(fitter.local),len(fitter.bounds)) or not np.isfinite(values).all():
        raise ValueError('Finite full-clip parameter initialization required')
    if len(values)<3 or sweeps<1 or not np.isfinite(curvature_weight) or curvature_weight<0:
        raise ValueError('At least three frames, positive sweeps and nonnegative finite curvature weight required')
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
        order=range(first,last+1) if sweep%2==0 else range(last,first-1,-1)
        for frame in order:
            neighbors=[values[n].copy() for n in [frame-1,frame+1] if 0<=n<len(values)]
            old=values[frame].copy();bounds=fitter.bounds;cache=None;cached=None
            def pair(x):
                nonlocal cache,cached
                if cache is None or not np.array_equal(cache,x):
                    cache=x.copy();r,j=fitter.objective_pair(frame,x,neighbors)
                    cr,cj=root_curvature_pair(values,frame,x,curvature_weight)
                    cached=(np.r_[r,cr],np.vstack([j,cj]))
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
        changes.append(float(np.abs(values-start).max()))
        if progress:progress(sweep+1,changes[-1])
    return values,records,dict(sweeps=sweeps,changes=changes,stationarity_proven=False,first_editable_frame=first,last_editable_frame=last,root_curvature_weight=curvature_weight,root_curvature_energy_before=root_curvature_energy(initial,curvature_weight),root_curvature_energy_after=root_curvature_energy(values,curvature_weight))
