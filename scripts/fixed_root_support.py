"""Refit leg corrections with one exactly fixed world-space root offset.

This preserves the source root velocity/acceleration by construction. It
does not assert that the source root motion or resulting foot motion is good.
"""
import numpy as np
from scipy.optimize import least_squares, minimize
from rig_periodic_contact import clip_step, neighbor_constraints


def constant_root_initial(parameters, bounds):
    parameters=np.asarray(parameters,float);bounds=np.asarray(bounds,float)
    if parameters.ndim!=2 or parameters.shape[1]<6 or (parameters.shape[1]-3)%3 or bounds.shape!=(parameters.shape[1],) or not len(parameters):
        raise ValueError('Full root/joint parameter track and matching bounds required')
    if not np.isfinite(parameters).all() or not np.isfinite(bounds).all() or np.any(bounds<=0) or np.any(np.abs(parameters)>bounds+1e-8):
        raise ValueError('Finite bounded source parameters required')
    result=parameters.copy();result[:,:3]=np.median(parameters[:,:3],axis=0)
    return result


def relax_fixed_root(fitter, initial, sweeps=6, progress=None):
    values=np.asarray(initial,float).copy()
    if values.shape!=(len(fitter.local),len(fitter.bounds)) or len(values)<3 or not np.isfinite(values).all():
        raise ValueError('Finite full-clip initialization required')
    if type(sweeps) is not int or sweeps<1 or np.any(np.abs(values)>fitter.bounds+1e-8):
        raise ValueError('Positive sweep budget and bounded initial parameters required')
    root=values[0,:3].copy()
    if not np.array_equal(values[:,:3],np.broadcast_to(root,values[:,:3].shape)):
        raise ValueError('One exactly constant root offset required')
    root_step=fitter.spec['limits']['root_step_m'];joint_step=np.radians(fitter.spec['limits']['joint_step_degrees'])
    for frame in range(len(values)-1):
        if neighbor_constraints(values[frame],[values[frame+1]],root_step,joint_step)[0].min() < -1e-7:
            raise ValueError('Initial adjacent edit limits exceeded')
    expand=lambda free:np.r_[root,free]
    records=[];changes=[]
    for sweep in range(sweeps):
        start=values.copy()
        for frame in (range(len(values)) if sweep%2==0 else range(len(values)-1,-1,-1)):
            neighbors=[values[n].copy() for n in (frame-1,frame+1) if 0<=n<len(values)]
            old=values[frame].copy();bounds=fitter.bounds[3:];cache=None;cached=None
            def pair(free):
                nonlocal cache,cached
                if cache is None or not np.array_equal(cache,free):
                    cache=free.copy();r,j=fitter.objective_pair(frame,expand(free),neighbors)
                    cached=r,j[:,3:]
                return cached
            def objective(free):
                r,_=pair(free);return float(r@r)
            fit=least_squares(lambda x:pair(x)[0],np.clip(old[3:],-bounds+1e-12,bounds-1e-12),
                jac=lambda x:pair(x)[1],bounds=(-bounds,bounds),max_nfev=fitter.spec['max_nfev'],ftol=1e-5,xtol=1e-5,gtol=1e-5)
            projected=clip_step(old,expand(fit.x),neighbors,root_step,joint_step)
            fallback=np.linalg.norm(projected-old)<.95*np.linalg.norm(expand(fit.x)-old)
            initial_nfev=int(fit.nfev)
            if fallback:
                fit=minimize(objective,projected[3:],jac=lambda x:2*pair(x)[1].T@pair(x)[0],method='SLSQP',
                    bounds=list(zip(-bounds,bounds)),constraints=dict(type='ineq',
                    fun=lambda x:neighbor_constraints(expand(x),neighbors,root_step,joint_step)[0],
                    jac=lambda x:neighbor_constraints(expand(x),neighbors,root_step,joint_step)[1][:,3:]),
                    options=dict(maxiter=fitter.spec['max_nfev'],ftol=1e-9))
            candidate=clip_step(old,expand(np.clip(fit.x,-bounds,bounds)),neighbors,root_step,joint_step)
            if not np.isfinite(candidate).all():raise ValueError('Nonfinite optimizer proposal')
            before=objective(old[3:]);after=before
            for backtrack in range(20):
                trial=old+(candidate-old)*(.5**backtrack);cost=objective(trial[3:])
                if cost<=before:
                    values[frame]=trial;after=cost;break
            if not np.array_equal(values[frame,:3],root):raise ValueError('Fixed root drifted')
            records.append(dict(sweep=sweep,frame=frame,success=bool(fit.success),status=int(fit.status),
                nfev=int(fit.nfev),initial_nfev=initial_nfev,constrained_fallback=bool(fallback),cost_before=before,cost_after=after))
        changes.append(float(np.abs(values-start).max()))
        if progress:progress(sweep+1,changes[-1])
    return values,records,dict(sweeps=sweeps,changes=changes,stationarity_proven=False,
        fixed_root_offset_m=root.tolist(),root_parameter_variation_m=float(np.ptp(values[:,:3],axis=0).max()),
        root_curvature_energy=0.,initialization='Retained leg edits plus componentwise median of retained root offsets')
