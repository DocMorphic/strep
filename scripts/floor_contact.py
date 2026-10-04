"""Conservative SOMA floor collision cleanup, not a dynamics/contact solver.

No action names are inspected. Root, finger articulation and clip timing are
preserved. Wrist pitch and two-bone IK are bounded; unreachable floor targets
remain visible failures. All surface calculations retain eight skin weights.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from inspect_motion import validate_motion

CONFIG = dict(fps=30, clearance_m=.002, wrist_limit_degrees=65,
              hand_lift_limit_m=.07, foot_lift_limit_m=.025,
              wrist_smoothing_frames=2, lift_smoothness=12, iterations=3)


class Surface:
    def __init__(self, skin):
        self.names = list(map(str, skin['rig_joint_names']))
        self.indices = skin['lbs_indices']
        self.weights = skin['lbs_weights']
        self.points = np.c_[skin['bind_vertices'], np.ones(len(self.weights))]
        self.inverse = np.linalg.inv(skin['bind_rig_transform'])
        dominant = self.indices[np.arange(len(self.indices)), self.weights.argmax(1)]
        self.regions = {}
        for side in ('Left', 'Right'):
            for part, prefixes in [('Hand', ('Hand',)), ('Foot', ('Foot', 'Toe'))]:
                bones = [i for i,n in enumerate(self.names) if any(n.startswith(side+p) for p in prefixes)]
                self.regions[side+part] = np.flatnonzero(np.isin(dominant, bones))

    def vertices(self, rotation, position, vertices=None):
        idx = slice(None) if vertices is None else vertices
        transform = np.broadcast_to(np.eye(4), (77,4,4)).copy()
        transform[:,:3,:3] = rotation
        transform[:,:3,3] = position
        transform = transform @ self.inverse
        return np.sum(np.einsum('vwij,vj->vwi', transform[self.indices[idx],:3], self.points[idx]) * self.weights[idx,:,None], axis=1)

    def heights(self, motion, region):
        return np.array([self.vertices(r,p,self.regions[region])[:,1].min()
                         for r,p in zip(motion['global_rot_mats'],motion['posed_joints'])])


def reconstruct(source, local, parents):
    """FK from source local offsets, retaining the supplied rig's bone lengths."""
    # Repeated IK compositions must not amplify source float32 orthogonality
    # drift. Project onto SO(3) before FK and quaternion export.
    local[:]=Rotation.from_matrix(local.reshape(-1,3,3)).as_matrix().reshape(local.shape)
    p0=source['posed_joints'].astype(float); r0=source['global_rot_mats'].astype(float)
    positions=np.empty_like(p0); rotations=np.empty_like(r0)
    for j,parent in enumerate(parents):
        if parent<0:
            positions[:,j]=source['root_positions']; rotations[:,j]=local[:,j]
        else:
            offsets=np.einsum('fji,fj->fi',r0[:,parent],p0[:,j]-p0[:,parent])
            rotations[:,j]=rotations[:,parent]@local[:,j]
            positions[:,j]=positions[:,parent]+np.einsum('fij,fj->fi',rotations[:,parent],offsets)
    result={k:v.copy() for k,v in source.items()}
    result.update(local_rot_mats=local.astype(np.float32),global_rot_mats=rotations.astype(np.float32),posed_joints=positions.astype(np.float32))
    return result


def smooth_lift(required, limit):
    """Nonperiodic minimum-change smooth envelope, bounded by the edit budget."""
    lower=np.clip(required,0,limit)
    if not np.any(lower):return lower
    def objective(x):
        second=np.diff(x,n=2); grad=2*x
        v=2*CONFIG['lift_smoothness']*second
        grad[:-2]+=v;grad[1:-1]-=2*v;grad[2:]+=v
        return float(x@x+CONFIG['lift_smoothness']*(second@second)),grad
    fit=minimize(objective,lower,jac=True,bounds=list(zip(lower,np.full(len(lower),limit))),method='L-BFGS-B',options={'ftol':1e-13,'gtol':1e-9,'maxiter':500})
    if not fit.success:raise RuntimeError('Lift smoothing did not converge: '+fit.message)
    return fit.x


def correct(source, skin):
    from correct_stance import swing, knee_target
    names,parents,_=validate_motion(source,30)
    if names!=list(map(str,skin['rig_joint_names'])):raise ValueError('SOMA77 skin/rig mismatch')
    surface=Surface(skin); local=source['local_rot_mats'].astype(float).copy()
    orientation={}; clamps={}; lifts={}
    for side in ('Left','Right'):
        hand=names.index(side+'Hand'); end=names.index(side+'HandMiddleEnd')
        edits=[]
        for r,p in zip(source['global_rot_mats'],source['posed_joints']):
            points=surface.vertices(r,p,surface.regions[side+'Hand'])
            direction=p[end]-p[hand]; flat=direction.copy();flat[1]=0
            delta=np.zeros(3)
            if points[:,1].min()<0 and p[hand,1]<.18 and direction[1]<0 and np.linalg.norm(flat)>1e-6:
                full=Rotation.from_matrix(swing(direction,flat)).as_rotvec()
                angle=np.linalg.norm(full); full*=min(1,np.deg2rad(CONFIG['wrist_limit_degrees'])/angle)
                # Minimum pitch needed to clear a rigid hand patch; blended skin
                # is checked again after FK. Never invent a planted-hand label.
                def height(a):return ((points-p[hand])@Rotation.from_rotvec(full*a).as_matrix().T+p[hand])[:,1].min()
                lo,hi=0.,1.
                if height(hi)>CONFIG['clearance_m']:
                    for _ in range(20):
                        mid=(lo+hi)/2
                        if height(mid)<CONFIG['clearance_m']:lo=mid
                        else:hi=mid
                delta=full*hi
            edits.append(delta)
        edits=gaussian_filter1d(np.array(edits),CONFIG['wrist_smoothing_frames'],axis=0,mode='nearest',truncate=3)
        desired=Rotation.from_rotvec(edits).as_matrix()@source['global_rot_mats'][:,hand]
        local[:,hand]=source['global_rot_mats'][:,parents[hand]].transpose(0,2,1)@desired
        orientation[side]=np.degrees(np.linalg.norm(edits,axis=1)).tolist()
    result=reconstruct(source,local,parents)
    for iteration in range(CONFIG['iterations']):
        for region in surface.regions:
            is_hand=region.endswith('Hand');side=region[:-4]
            end=names.index(region);middle=parents[end];start=parents[middle]
            limit=CONFIG['hand_lift_limit_m'] if is_hand else CONFIG['foot_lift_limit_m']
            used=np.array(lifts.get(region,np.zeros(len(local))))
            required=np.maximum(0,CONFIG['clearance_m']-surface.heights(result,region))
            total=smooth_lift(used+required,limit); shifts=total-used
            clamps.setdefault(region,0.)
            for f,shift in enumerate(shifts):
                if shift<1e-8:continue
                p=result['posed_joints'][f]; r=result['global_rot_mats'][f]
                a,b,c=p[[start,middle,end]].astype(float)
                new_b,new_c,clamp=knee_target(a,b,c,c+[0,shift,0])
                clamps[region]=max(clamps[region],float(clamp))
                ra=swing(b-a,new_b-a)@r[start]
                rb=swing(c-b,new_c-new_b)@r[middle]
                local[f,start]=r[parents[start]].T@ra
                local[f,middle]=ra.T@rb
                local[f,end]=rb.T@r[end]
            lifts[region]=total.tolist()
            result=reconstruct(source,local,parents)
    return result,dict(config=CONFIG,wrist_pitch_degrees=orientation,lift_requested_m=lifts,unreachable_clamp_m=clamps,
                       scope='Bounded floor collision cleanup. No contact locking, hand support inference, joint-limit model, object/self collision or dynamics. Root and finger articulation unchanged.')
