"""Bounded knee-plane freedom within the same native support/source-rate gates."""
from itertools import chain
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from native_support_rates import SupportRateProblem,reach_rotations
from native_leg_smoothing import lifts
from native_leg_floor import export_rotations


class SupportSwivelProblem(SupportRateProblem):
    def __init__(self,rig,reader,rows,tau=.05,mu=.5,*,swivel_limit_degrees=5.):
        if type(swivel_limit_degrees) not in (int,float) or not np.isfinite(swivel_limit_degrees) or not 0<swivel_limit_degrees<=5:
            raise ValueError('Choose positive knee-plane freedom up to 5 degrees')
        super().__init__(rig,reader,rows,tau,mu)
        self.bend_variables=len(self.initial);initial=self.initial.tolist();lower=self.lower.tolist();upper=self.upper.tolist()
        for d in self.data:
            keys=np.arange(1,len(d['clock'])-1);start=len(initial);limit=np.deg2rad(min(swivel_limit_degrees,d['row']['angle']))
            initial.extend(np.zeros(len(keys)));lower.extend(np.full(len(keys),-limit));upper.extend(np.full(len(keys),limit))
            d.update(swivel_keys=keys,swivel_ids=np.arange(start,len(initial)),swivel_limit_radians=limit)
        self.initial,self.lower,self.upper=map(np.asarray,(initial,lower,upper))

    def dependencies(self,d):
        return chain(super().dependencies(d),zip(d['swivel_keys'],d['swivel_ids']))

    def rotations(self,x):
        x=np.asarray(x,float)
        if x.shape!=self.initial.shape or not np.isfinite(x).all() or np.any(x<self.lower) or np.any(x>self.upper):
            raise ValueError('Finite bends and swivels inside authored/search bounds required')
        values={n:self.channels[n][2].astype(float).copy() for n in self.nodes};angles=[]
        for d in self.data:
            bend=d['bend'].copy();bend[d['free']]=x[d['ids']];amount=lifts(d['box'],bend)
            swivel=np.zeros(len(d['clock']));swivel[d['swivel_keys']]=x[d['swivel_ids']];r=d['row'];a,b=r['edit_keys']
            q=reach_rotations(d['worlds'],self.rig.parents,r['chain'],amount,r['up'],d['original'],swivel)
            q[[0,-1]]=d['original'][[0,-1]]
            for j,n in enumerate(r['chain']):values[n][a:b+1]=q[:,j]
            angles.append(np.rad2deg((Rotation.from_quat(d['original'].reshape(-1,4)).inv()*Rotation.from_quat(q.reshape(-1,4))).magnitude()).reshape(-1,3))
        return values,angles


def propose(rig,reader,rows,path,acceleration_time=.05,reference_weight=.5,*,maximum_evaluations=80):
    if type(maximum_evaluations) is not int or not 1<=maximum_evaluations<=2000:raise ValueError('Choose 1–2000 joint-search evaluations')
    problem=SupportSwivelProblem(rig,reader,rows,acceleration_time,reference_weight);initial=problem.residual(problem.initial)
    fit=least_squares(problem.residual,problem.initial,bounds=(problem.lower,problem.upper),jac_sparsity=problem.sparsity(),
        max_nfev=maximum_evaluations,ftol=1e-9,xtol=1e-9,gtol=1e-9,x_scale='jac',diff_step=1e-5)
    values,_=problem.rotations(fit.x);final=problem.residual(fit.x);export_rotations(rig.document,rig.binary,values,path)
    return [dict(method='joint_support_source_rate_swivel_search',variables=len(fit.x),bend_variables=problem.bend_variables,
        maximum_swivel_degrees=float(max(np.rad2deg(np.abs(fit.x[d['swivel_ids']])).max(initial=0) for d in problem.data)),
        swivel_limit_degrees=5.,initial_squared_residual=float(initial@initial),final_squared_residual=float(final@final),
        evaluations=int(fit.nfev),maximum_evaluations=maximum_evaluations,success=bool(fit.success),message=str(fit.message),
        sample_times=len(problem.times),source_rate_tolerance=problem.caps.tolerance,
        scope='Bounded knee bends and knee-plane swivels; native foot tangent/orientation retained. Serialized audits remain separate.')]
