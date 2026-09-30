"""Original-bin positional and angular limits on exact sampled edge clocks."""
import numpy as np
from scipy.spatial.transform import Rotation


def features(world,joints):
    world=np.asarray(world,float)[:,joints]
    return dict(positions=world[:,:,:3,3],rotations=world[:,:,:3,:3])


def measures(payload,dt):
    p=np.asarray(payload['positions'],float);r=np.asarray(payload['rotations'],float)
    if p.ndim!=3 or p.shape[-1]!=3 or r.shape!=p.shape[:2]+(3,3) or len(p)<2:
        raise ValueError('At least two matching joint pose samples required')
    if not np.isfinite(p).all() or not np.isfinite(r).all():raise ValueError('Finite joint pose samples required')
    if not np.allclose(r@r.transpose(0,1,3,2),np.eye(3),atol=1e-6,rtol=0) or not np.allclose(np.linalg.det(r),1,atol=1e-6,rtol=0):
        raise ValueError('Proper joint rotations required')
    delta=r[1:]@r[:-1].transpose(0,1,3,2)
    angular=Rotation.from_matrix(delta.reshape(-1,3,3)).as_rotvec().reshape(len(p)-1,p.shape[1],3)/dt
    if np.any(np.linalg.norm(angular,axis=2)*dt>=np.pi-1e-6):raise ValueError('Ambiguous angular step')
    return [np.linalg.norm(np.diff(p,axis=0)/dt,axis=2),np.linalg.norm(np.diff(p,n=2,axis=0)/dt**2,axis=2),
            np.linalg.norm(angular,axis=2),np.linalg.norm(np.diff(angular,axis=0)/dt,axis=2)]


class SampledMotionCaps:
    def __init__(self,source,times,knots,tolerance=1e-5):
        self.times=np.asarray(times,float);knots=np.asarray(knots,float);self.tolerance=float(tolerance)
        if self.times.ndim!=1 or len(self.times)<3 or not np.isfinite(self.times).all() or np.any(np.diff(self.times)<=0) or not np.allclose(np.diff(self.times),self.times[1]-self.times[0],atol=1e-12,rtol=0):
            raise ValueError('Uniform finite increasing source clock required')
        if knots.ndim!=1 or len(knots)<3 or not np.isfinite(knots).all() or np.any(np.diff(knots)<=0) or not np.isfinite(tolerance) or tolerance<0:
            raise ValueError('Increasing source bins and nonnegative tolerance required')
        if len(source['positions'])!=len(self.times):raise ValueError('Source clock mismatch')
        self.dt=float(self.times[1]-self.times[0]);self.caps=[];self.joints=np.asarray(source['positions']).shape[1]
        for metric,(values,order) in enumerate(zip(measures(source,self.dt),[1,2,1,2])):
            stamps=self.times[1:-1] if metric==3 else (self.times[:-order]+self.times[order:])/2
            bins=np.searchsorted(knots[1:-1],stamps,side='right');caps=np.empty_like(values)
            for index in np.unique(bins):caps[bins==index]=values[bins==index].max(axis=0)
            self.caps.append(caps)

    def check(self,payload):
        ids=np.asarray(payload['indices'])
        if ids.ndim!=1 or len(ids)<2 or not np.issubdtype(ids.dtype,np.integer) or np.any(np.diff(ids)!=1) or ids[0]<0 or ids[-1]>=len(self.times):
            raise ValueError('Contiguous matching source sample indices required')
        if np.asarray(payload['positions']).shape!=(len(ids),self.joints,3):raise ValueError('Joint population differs')
        return all(np.all(values<=cap[ids[0]:ids[0]+len(values)]+self.tolerance)
                   for values,cap in zip(measures(payload,self.dt),self.caps))

    def join(self,before,after):
        payload={key:np.concatenate([before[key][-2:],after[key]]) for key in ['indices','positions','rotations']}
        return self.check(payload)
