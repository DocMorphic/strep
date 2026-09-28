"""Matched temporal objective with pose/edit priors centered on explicit input."""
import numpy as np
from scipy.optimize import minimize
from constrained_patch_pose import constraint_pair
from rig_periodic_contact import neighbor_constraints
from temporal_patch_frame import coordinate_bounds,pose_budget_pair


def evaluate(fitter,frame,x,neighbors,reference,neighbor_references):
    reference=np.asarray(reference,float)
    if (reference.shape!=x.shape or len(neighbors)!=len(neighbor_references)
        or any(np.asarray(r).shape!=x.shape for r in neighbor_references)
        or not all(np.isfinite(r).all() for r in [reference,*neighbor_references])):
        raise ValueError('Explicit finite pose reference and one reference per neighbor required')
    # Keep contact/floor residuals; replace only the absolute and temporal priors.
    residual,jac=fitter.residual_pair(frame,x,np.zeros_like(x))
    residual=residual[:-2*len(x)];jac=jac[:-2*len(x)]
    objective=fitter.spec['objective']
    prior=np.r_[np.full(3,objective['root_prior']),np.full(len(x)-3,objective['rotation_prior_m_per_radian'])]
    weight=np.r_[np.ones(3),np.full(len(x)-3,objective['rotation_prior_m_per_radian'])]*objective['temporal_weight']
    residual=np.concatenate([residual,(x-reference)*prior,*[((x-reference)-(n-r))*weight for n,r in zip(neighbors,neighbor_references)]])
    jac=np.vstack([jac,np.diag(prior),*[np.diag(weight) for n in neighbors]])
    points,pj=fitter.surface_jacobian(frame,x)
    c,cj=constraint_pair(points,pj,fitter.active[frame],fitter.spec['patches'],
        fitter.spec['screen']['floor_depth_m'],fitter.spec['screen']['contact_error_m'])
    nc,nj=neighbor_constraints(x,neighbors,fitter.spec['limits']['root_step_m'],np.radians(fitter.spec['limits']['joint_step_degrees']))
    pc,pj=pose_budget_pair(fitter,x)
    return float(residual@residual),2*residual@jac,np.r_[c,nc,pc],np.vstack([cj,nj,pj])


def solve(fitter,frame,start,neighbors,reference,neighbor_references,maxiter=80):
    start=np.asarray(start,float);neighbors=[np.asarray(n,float) for n in neighbors]
    if (start.shape!=fitter.bounds.shape or any(n.shape!=start.shape for n in neighbors) or not neighbors
        or not all(np.isfinite(v).all() for v in [start,*neighbors]) or np.any(np.abs(start)>coordinate_bounds(fitter)+1e-10)):
        raise ValueError('Finite in-bound pose and at least one matching neighbor required')
    last_x,last=None,None
    def pair(x):
        nonlocal last_x,last
        if last_x is None or not np.array_equal(last_x,x):
            last_x=x.copy();last=evaluate(fitter,frame,x,neighbors,reference,neighbor_references)
        return last
    result=minimize(lambda x:pair(x)[0],start,jac=lambda x:pair(x)[1],method='SLSQP',
        bounds=list(zip(-coordinate_bounds(fitter),coordinate_bounds(fitter))),
        constraints=dict(type='ineq',fun=lambda x:pair(x)[2],jac=lambda x:pair(x)[3]),
        options=dict(maxiter=maxiter,ftol=1e-10))
    return result,dict(minimum_scaled_inequality=float(pair(result.x)[2].min()),max_iterations=maxiter)
