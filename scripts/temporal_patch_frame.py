"""Hard per-frame patch/skin constraints plus neighboring edit limits."""
import numpy as np
from scipy.optimize import minimize
from constrained_patch_pose import constraint_pair
from rig_periodic_contact import neighbor_constraints


def coordinate_bounds(fitter):
    limits=fitter.spec['limits']
    return np.r_[[limits['root_horizontal_m'],limits['root_vertical_m'],limits['root_horizontal_m']],np.repeat(fitter.angles,3)]


def pose_budget_pair(fitter,x):
    limits=fitter.spec['limits'];rows=[];parts=[]
    for indices,radius in [(np.array([0,2]),limits['root_horizontal_m']),(np.array([1]),limits['root_vertical_m'])]+[(np.arange(3+i*3,6+i*3),a) for i,a in enumerate(fitter.angles)]:
        delta=x[indices];row=np.zeros(len(x));row[indices]=-2*delta/radius**2
        parts.append(1-float(delta@delta)/radius**2);rows.append(row)
    return np.array(parts),np.array(rows)


def evaluate(fitter,frame,x,neighbors):
    # Strip the legacy one-sided temporal prior and add every declared neighbor.
    residual,jac=fitter.residual_pair(frame,x,np.zeros_like(x))
    residual=residual[:-len(x)];jac=jac[:-len(x)]
    weight=np.r_[np.ones(3),np.full(len(x)-3,fitter.spec['objective']['rotation_prior_m_per_radian'])]*fitter.spec['objective']['temporal_weight']
    residual=np.concatenate([residual,*[(x-n)*weight for n in neighbors]])
    jac=np.vstack([jac,*[np.diag(weight) for n in neighbors]])
    points,pj=fitter.surface_jacobian(frame,x)
    c,cj=constraint_pair(points,pj,fitter.active[frame],fitter.spec['patches'],
        fitter.spec['screen']['floor_depth_m'],fitter.spec['screen']['contact_error_m'])
    nc,nj=neighbor_constraints(x,neighbors,fitter.spec['limits']['root_step_m'],np.radians(fitter.spec['limits']['joint_step_degrees']))
    pc,pj=pose_budget_pair(fitter,x)
    return float(residual@residual),2*residual@jac,np.r_[c,nc,pc],np.vstack([cj,nj,pj])


def solve(fitter,frame,start,neighbors,maxiter=80):
    start=np.asarray(start,float);neighbors=[np.asarray(n,float) for n in neighbors]
    if (start.shape!=fitter.bounds.shape or any(n.shape!=start.shape for n in neighbors) or not neighbors
        or not all(np.isfinite(v).all() for v in [start,*neighbors]) or np.any(np.abs(start)>coordinate_bounds(fitter)+1e-10)):
        raise ValueError('Finite in-bound pose and at least one matching neighbor required')
    last_x,last=None,None
    def pair(x):
        nonlocal last_x,last
        if last_x is None or not np.array_equal(last_x,x):last_x=x.copy();last=evaluate(fitter,frame,x,neighbors)
        return last
    result=minimize(lambda x:pair(x)[0],start,jac=lambda x:pair(x)[1],method='SLSQP',
        bounds=list(zip(-coordinate_bounds(fitter),coordinate_bounds(fitter))),
        constraints=dict(type='ineq',fun=lambda x:pair(x)[2],jac=lambda x:pair(x)[3]),
        options=dict(maxiter=maxiter,ftol=1e-10))
    return result,dict(minimum_scaled_inequality=float(pair(result.x)[2].min()),max_iterations=maxiter)
