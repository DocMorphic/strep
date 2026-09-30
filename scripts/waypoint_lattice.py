"""Finite waypoint path search with explicit parameter-rate bounds.

Costs are supplied by a geometry model. Passing these parameter limits does not
establish mesh clearance or bound the actual character's joint motion.
"""
import numpy as np


def shortest_path(times,states,costs,limits,transition_weight=.1):
    times,states,costs,limits=[np.asarray(v,float) for v in [times,states,costs,limits]]
    if times.ndim!=1 or len(times)<2 or not np.isfinite(times).all() or np.any(np.diff(times)<=0):
        raise ValueError('Strictly increasing finite path times required')
    if states.ndim!=2 or not len(states) or not states.shape[1] or not np.isfinite(states).all():
        raise ValueError('Finite nonempty parameter states required')
    if costs.shape!=(len(times),len(states)) or np.isnan(costs).any() or np.isneginf(costs).any() or np.any(costs<0):
        raise ValueError('Nonnegative node costs or positive infinity required')
    if limits.shape!=(states.shape[1],) or not np.isfinite(limits).all() or np.any(limits<=0):
        raise ValueError('Positive finite parameter rate limits required')
    if not np.isfinite(transition_weight) or transition_weight<0:raise ValueError('Nonnegative finite transition cost required')
    zero=np.flatnonzero(np.all(states==0,axis=1))
    if len(zero)!=1 or len(np.unique(states,axis=0))!=len(states):raise ValueError('Distinct states with one zero boundary state required')
    start=int(zero[0]);values=np.full(len(states),np.inf);values[start]=costs[0,start]
    predecessors=[];delta=states[None,:,:]-states[:,None,:]
    for i,dt in enumerate(np.diff(times),start=1):
        speed=delta/dt;allowed=np.all(np.abs(speed)<=limits+1e-12,axis=2)
        edge=transition_weight*dt*np.sum((speed/limits)**2,axis=2)
        total=np.where(allowed,values[:,None]+edge,np.inf)
        parent=np.argmin(total,axis=0);values=total[parent,np.arange(len(states))]+costs[i]
        predecessors.append(parent)
    if not np.isfinite(values[start]):return None,dict(status='no_feasible_path')
    indices=[start]
    for parent in reversed(predecessors):indices.append(int(parent[indices[-1]]))
    indices=indices[::-1];parameters=states[indices]
    return parameters,dict(status='complete',state_indices=indices,total_cost=float(values[start]),
        maximum_parameter_rates=np.max(np.abs(np.diff(parameters,axis=0)/np.diff(times)[:,None]),axis=0).tolist())


class LinearGuide:
    """A bounded piecewise-linear guide, with zero parameters outside its clock."""
    def __init__(self,times,parameters,limits):
        self.times=np.asarray(times,float);self.parameters=np.asarray(parameters,float);self.limits=np.asarray(limits,float)
        if self.times.ndim!=1 or len(self.times)<2 or not np.isfinite(self.times).all() or np.any(np.diff(self.times)<=0):
            raise ValueError('Increasing guide times required')
        if self.parameters.shape!=(len(self.times),3) or not np.isfinite(self.parameters).all():
            raise ValueError('Finite displacement and two swivel columns required')
        if not np.array_equal(self.parameters[[0,-1]],np.zeros((2,3))):raise ValueError('Zero guide endpoints required')
        if self.limits.shape!=(3,) or not np.isfinite(self.limits).all() or np.any(self.limits<=0):raise ValueError('Three positive guide rates required')
        if np.any(np.abs(np.diff(self.parameters,axis=0)/np.diff(self.times)[:,None])>self.limits+1e-12):
            raise ValueError('Guide exceeds declared parameter rate limits')
        if np.any(self.parameters[:,0]<0) or np.any(self.parameters[:,0]>.06+1e-12) or np.any(np.abs(self.parameters[:,1:])>30+1e-12):
            raise ValueError('Guide exceeds 60mm / 30-degree planning domain')

    def __call__(self,time):
        if not np.isfinite(time):raise ValueError('Finite guide time required')
        return np.array([np.interp(time,self.times,self.parameters[:,i],left=0.,right=0.) for i in range(3)])
