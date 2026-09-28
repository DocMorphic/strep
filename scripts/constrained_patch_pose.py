"""Experimental isolated-pose solve with explicit surface/contact inequalities."""
import numpy as np
from scipy.optimize import minimize


def constraint_pair(points,jac,contacts,patches,floor_limit,contact_limit,margin=1e-5):
    if not 0 <= margin < min(floor_limit,contact_limit):
        raise ValueError('Interior numerical margin must be smaller than both screens')
    parts=[(points[:,1]+floor_limit-margin)/floor_limit]
    rows=[jac[:,1]/floor_limit]
    radius=contact_limit-margin
    for contact in contacts:
        ids=patches[contact['patch']]['vertices']
        delta=points[ids].mean(0)-contact['target_position_m']
        parts.append(np.array([1-float(delta@delta)/radius**2]))
        rows.append((-2*delta@jac[ids].mean(0)/radius**2)[None])
    return np.concatenate(parts),np.vstack(rows)


def solve(fitter,start,maxiter=120):
    start=np.asarray(start,float)
    if start.shape!=fitter.bounds.shape or not np.isfinite(start).all() or np.any(np.abs(start)>fitter.bounds+1e-12):
        raise ValueError('Finite starting pose within existing bounds required')
    last_x,last=None,None
    zero=np.zeros_like(start)
    def evaluate(x):
        nonlocal last_x,last
        if last_x is None or not np.array_equal(x,last_x):
            residual,rj=fitter.residual_pair(0,x,zero)
            points,jac=fitter.surface_jacobian(0,x)
            c,cj=constraint_pair(points,jac,fitter.active[0],fitter.spec['patches'],
                fitter.spec['screen']['floor_depth_m'],fitter.spec['screen']['contact_error_m'])
            last_x=x.copy();last=(float(residual@residual),2*residual@rj,c,cj)
        return last
    result=minimize(lambda x:evaluate(x)[0],start,jac=lambda x:evaluate(x)[1],method='SLSQP',
        bounds=list(zip(-fitter.bounds,fitter.bounds)),
        constraints=dict(type='ineq',fun=lambda x:evaluate(x)[2],jac=lambda x:evaluate(x)[3]),
        options=dict(maxiter=maxiter,ftol=1e-10))
    return result,dict(minimum_scaled_inequality=float(evaluate(result.x)[2].min()),
        numerical_interior_margin_m=1e-5,max_iterations=maxiter,
        scope='All mesh vertices and declared patch centroids at one pose; no temporal or balance guarantee.')
