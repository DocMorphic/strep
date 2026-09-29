"""Minimum-energy root lift constrained at decoded integer and subframe samples."""
import numpy as np
from scipy.optimize import minimize, LinearConstraint, Bounds


def sample_weights(times, count, fps=30):
    times=np.asarray(times,float)
    if times.ndim!=1 or not np.isfinite(times).all() or np.any(times<0) or np.any(times>count-1):raise ValueError('Finite sample frames within clip required')
    matrix=np.zeros((len(times),count))
    for row,time in enumerate(times):
        left,right=int(np.floor(time)),int(np.ceil(time))
        if left==right:matrix[row,left]=1
        else:
            ta,tb,t=[float(np.float32(f/fps)) for f in [left,right,time]];alpha=(t-ta)/(tb-ta)
            matrix[row,left]=1-alpha;matrix[row,right]=alpha
    return matrix


def solve_lift(times, heights, capacities, free_frames, target_height=.002002, smoothness=12.):
    heights,capacities=np.asarray(heights,float),np.asarray(capacities,float);count=len(capacities);free=np.asarray(free_frames,int)
    if not np.isfinite(heights).all() or not np.isfinite(capacities).all() or np.any(capacities<0) or len(free)!=len(set(free)) or np.any(free<0) or np.any(free>=count):raise ValueError('Finite heights, nonnegative capacities and distinct valid free frames required')
    if not np.isfinite(target_height) or target_height<0 or not np.isfinite(smoothness) or smoothness<0:raise ValueError('Nonnegative finite target and smoothness required')
    weights=sample_weights(times,count)
    if heights.shape!=(len(weights),):raise ValueError('One height per sample required')
    a=weights[:,free];rhs=target_height-heights;influence=a.sum(1)>0
    if np.any(rhs[~influence]>1e-12):raise ValueError('A locked sample needs floor correction')
    scale=.001;a_active=a[influence];b=rhs[influence]/scale;upper=capacities[free]/scale
    if not len(free):return np.zeros(count),dict(success=True,iterations=0,minimum_predicted_height_m=float(heights.min()))
    initial_level=max(0.,float(np.max(b/a_active.sum(1))))
    initial=np.full(len(free),initial_level)
    if np.any(initial>upper):raise ValueError('Uniform feasible initialization exceeds root capacity')
    second=np.diff(np.eye(count),n=2,axis=0)[:,free];hessian=np.eye(len(free))+smoothness*second.T@second
    def objective(x):return .5*float(x@hessian@x),hessian@x
    fit=minimize(objective,initial,jac=True,method='SLSQP',bounds=Bounds(np.zeros(len(free)),upper),
                 constraints=[LinearConstraint(a_active,b,np.inf)],options=dict(maxiter=300,ftol=1e-12))
    delta=np.zeros(count);delta[free]=fit.x*scale;predicted=heights+weights@delta
    if predicted.min()<target_height-1e-10 or np.any(delta< -1e-12) or np.any(delta>capacities+1e-12):raise ValueError('Floor envelope failed exact linear constraints')
    return delta,dict(success=bool(fit.success),message=str(fit.message),iterations=int(fit.nit),minimum_predicted_height_m=float(predicted.min()),maximum_lift_m=float(delta.max()),objective=float(fit.fun))
