"""Joint arm/finger contact refinement with a palm-coincidence constraint.

Budgets constrain edits to the source animation, not anatomical joint angles.
All candidates require independent skin and temporal validation.
"""
import numpy as np
from scipy.optimize import minimize
from paired_hand_fit import HandActor
from paired_hand_clearance import SurfaceObjective,correspondences


class FingerHandActor(HandActor):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        names={n.get('name'):i for i,n in enumerate(self.rig.document['nodes'])}
        roles=[];limits=[]
        for finger in ['Thumb','Index','Middle','Ring','Pinky']:
            for joint in range(1,4 if finger=='Thumb' else 5):
                roles.append(self.hand+finger+str(joint))
                limits.append((8 if finger=='Thumb' else 5) if joint==1 else 12)
        if any(r not in names for r in roles):raise ValueError('Native finger chain is missing')
        self.nodes.extend(names[r] for r in roles);self.limits=np.r_[self.limits,np.radians(limits)]
        for edited in self.nodes:
            descendants=[]
            for node in range(len(self.rig.parents)):
                while node>=0 and node!=edited:node=self.rig.parents[node]
                descendants.append(node==edited)
            self.descendants[edited]=np.array(descendants)
        self.dim=len(self.nodes)*3


def expand_arm_seed(values,actors):
    values=np.asarray(values)
    if values.shape!=(24,):raise ValueError('Expected original two-arm seed')
    return np.concatenate([np.r_[values[i*12:(i+1)*12],np.zeros(a.dim-12)] for i,a in enumerate(actors)])


def contact_pair(fitter,x):
    r,j=fitter.objective_pair(x)
    return r[:3]/100.,j[:3]/100.


def refine(fitter,initial,faces,progress=None,iterations=4):
    x=np.asarray(initial,dtype=float).copy();history=[]
    if x.shape!=fitter.bounds.shape or not np.isfinite(x).all() or np.any(np.abs(x)>fitter.bounds+1e-10):raise ValueError('Invalid initial correction')
    records,diagnostics=correspondences(fitter.actors,fitter.event,x,faces)
    history.append(dict(iteration=0,collision=diagnostics,parameters=x.tolist()))
    if progress:progress(history)
    for iteration in range(1,iterations+1):
        objective=SurfaceObjective(fitter,records)
        def energy(v):
            r,j=objective.pair(v)
            return .5*float(r@r),j.T@r
        lower=np.maximum(-fitter.bounds,x-np.radians(5));upper=np.minimum(fitter.bounds,x+np.radians(5))
        result=minimize(energy,x,method='SLSQP',jac=True,bounds=list(zip(lower,upper)),
            constraints=[dict(type='eq',fun=lambda v:contact_pair(fitter,v)[0],jac=lambda v:contact_pair(fitter,v)[1])],
            options=dict(maxiter=100,ftol=1e-9))
        candidate=np.clip(result.x,lower,upper)
        if not np.isfinite(candidate).all():raise ValueError('Nonfinite candidate')
        records,diagnostics=correspondences(fitter.actors,fitter.event,candidate,faces)
        a=fitter.actors[0].frame_pair(fitter.event,candidate[:fitter.sizes[0]])
        b=fitter.actors[1].frame_pair(fitter.event,candidate[fitter.sizes[0]:])
        history.append(dict(iteration=iteration,collision=diagnostics,parameters=candidate.tolist(),evaluations=int(result.nfev),
            solver_iterations=int(result.nit),solver_success=bool(result.success),solver_message=str(result.message),
            palm_gap_m=float(np.linalg.norm(a[0]-b[0])),palm_equality_verified=bool(np.linalg.norm(a[0]-b[0])<=1e-5),
            opposing_normal_degrees=float(np.degrees(np.arccos(np.clip(-a[1]@b[1],-1,1)))),
            tangent_difference_degrees=float(np.degrees(np.arccos(np.clip(a[2]@b[2],-1,1))))))
        if progress:progress(history)
        x=candidate
    return x,history
