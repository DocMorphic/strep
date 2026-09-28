"""Scaled minimax step for frozen linear surface clearances and exact edit balls."""
import numpy as np
from scipy.optimize import minimize


class MinimaxStep:
    def __init__(self, base, gaps, jacobian, locked, bounds, hard_pair,
                 trust_radians, distance_scale=.005, regularizer=1e-4):
        self.base=np.asarray(base,float);self.gaps=np.asarray(gaps,float);self.jac=np.asarray(jacobian,float)
        self.locked=np.asarray(locked,bool);self.bounds=np.asarray(bounds,float);self.hard_pair=hard_pair
        self.trust=float(trust_radians);self.scale=float(distance_scale);self.regularizer=float(regularizer)
        n=len(self.base)
        if n%3 or self.base.ndim!=1 or self.jac.shape!=(len(self.gaps),n) or self.locked.shape!=(n,) or self.bounds.shape!=(n,):
            raise ValueError('Matching vector, witness and control dimensions required')
        if not len(self.gaps) or not np.isfinite(np.r_[self.base,self.gaps,self.jac.ravel(),self.bounds,self.trust,self.scale,self.regularizer]).all():
            raise ValueError('Nonempty finite problem required')
        if min(self.trust,self.scale,self.regularizer)<=0 or np.any(self.bounds<=0):
            raise ValueError('Positive trust, scales and bounds required')
        if np.any(np.abs(self.base)>self.bounds+1e-10) or self.hard_pair(self.base)[0].min() < -1e-8:
            raise ValueError('Hard-feasible starting controls required')
        self.free=np.flatnonzero(~self.locked)
        if not len(self.free):raise ValueError('At least one free control required')
        self.surface_matrix=self.jac[:,self.free]*self.trust/self.scale
        self.lower=np.r_[np.maximum(-1.,(-self.bounds[self.free]-self.base[self.free])/self.trust),0.]
        self.upper=np.r_[np.minimum(1.,(self.bounds[self.free]-self.base[self.free])/self.trust),np.inf]

    def controls(self, values):
        x=self.base.copy();x[self.free]+=self.trust*values[:-1]
        return x

    def objective(self, values):
        return float(values[-1]+self.regularizer*(values[:-1]@values[:-1])),np.r_[2*self.regularizer*values[:-1],1.]

    def constraints(self, values):
        delta=np.zeros_like(self.base);delta[self.free]=values[:-1]
        vectors=delta.reshape(-1,3)
        trust=1-np.sum(vectors*vectors,axis=1)
        trust_jac=np.zeros((len(vectors),len(values)))
        for column, coordinate in enumerate(self.free):trust_jac[coordinate//3,column]=-2*delta[coordinate]
        hard, hard_jac=self.hard_pair(self.controls(values))
        surface=self.gaps/self.scale+self.surface_matrix@values[:-1]+values[-1]
        derivative=np.vstack([np.c_[self.surface_matrix,np.ones(len(surface))],
                              np.c_[hard_jac[:,self.free]*self.trust,np.zeros(len(hard))],trust_jac])
        return np.r_[surface,hard,trust],derivative

    def solve(self, maxiter=120):
        initial=np.r_[np.zeros(len(self.free)),max(0.,float((-self.gaps/self.scale).max()))+1e-6]
        if self.constraints(initial)[0].min() < -1e-8:raise ValueError('Constructed minimax seed is infeasible')
        result=minimize(lambda y:self.objective(y)[0],initial,jac=lambda y:self.objective(y)[1],method='SLSQP',
                        bounds=list(zip(self.lower,self.upper)),constraints=dict(type='ineq',
                        fun=lambda y:self.constraints(y)[0],jac=lambda y:self.constraints(y)[1]),
                        options=dict(maxiter=maxiter,ftol=1e-10))
        x=self.controls(result.x)
        record=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),
                    predicted_peak_depth_m=float(max(0.,(-self.gaps-self.jac@(x-self.base)).max())),
                    initial_peak_depth_m=float(max(0.,(-self.gaps).max())),
                    minimum_constraint_slack=float(self.constraints(result.x)[0].min()),
                    epigraph_m=float(result.x[-1]*self.scale),objective=float(result.fun),
                    maximum_control_step_radians=float(np.linalg.norm((x-self.base).reshape(-1,3),axis=1).max()),
                    locked_controls_exact=bool(np.array_equal(x[self.locked],self.base[self.locked])))
        return x,record
