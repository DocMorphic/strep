"""Local Hermite translation and spherical Bezier rotation with endpoint rates."""
import numpy as np
from scipy.spatial.transform import Rotation


def localize(world,parents):
    local=world.copy()
    for n,p in enumerate(parents):
        if p>=0:local[:,n]=np.linalg.inv(world[:,p])@world[:,n]
    return local


def compose(local,parents):
    pending=set(range(len(parents)));done=set();world=np.empty_like(local)
    while pending:
        ready=[n for n in pending if parents[n]<0 or parents[n] in done]
        if not ready:raise ValueError('Acyclic hierarchy required')
        for n in ready:
            p=parents[n];world[:,n]=local[:,n] if p<0 else world[:,p]@local[:,n]
        pending.difference_update(ready);done.update(ready)
    return world


def mix(a,b,u):
    """Shortest-arc geodesic; inputs are batches of proper rotation matrices."""
    delta=Rotation.from_matrix(b@a.swapaxes(-1,-2)).as_rotvec()
    return Rotation.from_rotvec(delta*u).as_matrix()@a


class LocalBridge:
    def __init__(self,a,b,va,vb,wa,wb,duration,maximum_control_degrees):
        if a.ndim!=3 or a.shape[1:]!=(4,4) or b.shape!=a.shape or any(x.shape!=(len(a),3) for x in (va,vb,wa,wb)):
            raise ValueError('Matching local transforms and endpoint rate vectors required')
        if not all(np.isfinite(x).all() for x in (a,b,va,vb,wa,wb)):
            raise ValueError('Finite local transforms and rates required')
        self.a,self.b,self.va,self.vb=a.copy(),b.copy(),va.copy(),vb.copy()
        self.duration=float(duration)
        if not self.duration>0 or not np.isfinite(self.duration):raise ValueError('Positive finite bridge duration required')
        unwrapped=max(float(np.linalg.norm(wa,axis=1).max()),float(np.linalg.norm(wb,axis=1).max()))*self.duration/3
        if not 0<maximum_control_degrees<180 or np.degrees(unwrapped)>maximum_control_degrees:
            raise ValueError('Unwrapped angular tangent exceeds the shortest-arc control budget')
        r0,r3=a[:,:3,:3],b[:,:3,:3]
        self.controls=[r0,Rotation.from_rotvec(wa*self.duration/3).as_matrix()@r0,
            Rotation.from_rotvec(-wb*self.duration/3).as_matrix()@r3,r3]
        steps=[Rotation.from_matrix(y@x.swapaxes(-1,-2)).magnitude() for x,y in zip(self.controls[:-1],self.controls[1:])]
        steps.append(Rotation.from_matrix(r3@r0.swapaxes(-1,-2)).magnitude())
        self.maximum_control_angle_degrees=float(np.degrees(np.concatenate(steps)).max())
        if not 0<maximum_control_degrees<180 or self.maximum_control_angle_degrees>maximum_control_degrees:
            raise ValueError('Spherical controls exceed the authored shortest-arc budget')

    def sample(self,times):
        times=np.asarray(times,float)
        if times.ndim!=1 or not np.isfinite(times).all() or np.any(times<0) or np.any(times>self.duration):
            raise ValueError('Finite times inside the bridge required')
        u=times/self.duration;result=np.tile(self.a,(len(times),1,1,1))
        for i,t in enumerate(u):
            layer=self.controls
            while len(layer)>1:layer=[mix(x,y,t) for x,y in zip(layer[:-1],layer[1:])]
            result[i,:,:3,:3]=layer[0]
        u=u[:,None,None]
        result[:,:,:3,3]=(2*u**3-3*u**2+1)*self.a[None,:,:3,3]+(u**3-2*u**2+u)*self.duration*self.va[None]+(-2*u**3+3*u**2)*self.b[None,:,:3,3]+(u**3-u**2)*self.duration*self.vb[None]
        result[times==0]=self.a;result[times==self.duration]=self.b
        return result


def rates(local,times):
    dt=np.diff(np.asarray(times,float))
    if np.any(dt<=0):raise ValueError('Increasing clocks required')
    velocity=np.diff(local[:,:,:3,3],axis=0)/dt[:,None,None]
    omega=Rotation.from_matrix((local[1:,:,:3,:3]@local[:-1,:,:3,:3].swapaxes(-1,-2)).reshape(-1,3,3)).as_rotvec().reshape(len(dt),local.shape[1],3)/dt[:,None,None]
    return velocity,omega
