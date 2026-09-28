"""Joint two-actor hand-pose correction for one authored high-five event.

Both actors are variables in the same residual. A smooth, bounded edit envelope
applies each fitted local rotation to the surrounding motion. This is not a
whole-body, collision-aware or physically balanced interaction model.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from rig_clearance_fit import right_jacobian
from target_rig_contact import SkinEvaluator


def unit_pair(vector,jacobian):
    length=np.linalg.norm(vector)
    if length<1e-10:raise ValueError('Degenerate hand direction')
    direction=vector/length
    return direction,(np.eye(3)-np.outer(direction,direction))@jacobian/length


def envelope(frames,event,fade=15):
    if type(event)is not int or type(fade)is not int or fade<2 or not fade<=event<frames-fade:
        raise ValueError('Contact needs an interior fade window')
    f=np.arange(frames);distance=np.abs(f-event)/fade
    return np.where(distance<1,np.cos(np.minimum(distance,1)*np.pi/2)**2,0.)


class HandActor:
    def __init__(self,rig,local,hand,palm_vertex,faces,placement):
        if hand not in ('LeftHand','RightHand'):raise ValueError('Choose a mapped hand')
        self.rig=rig;self.local=np.asarray(local);self.hand=hand
        names={n.get('name'):i for i,n in enumerate(rig.document['nodes'])}
        prefix=hand[:-4]
        roles=[prefix+'Shoulder',prefix+'Arm',prefix+'ForeArm',hand]
        if any(r not in names for r in roles):raise ValueError('Arm chain is missing')
        self.nodes=[names[r] for r in roles];self.limits=np.radians([15,25,35,30])
        self.wrist=names[hand];self.knuckles=[names[hand+f+'2'] for f in ['Index','Middle','Ring','Pinky']]
        chains=[]
        for node in range(len(rig.parents)):
            chain=set()
            while node>=0:chain.add(node);node=rig.parents[node]
            chains.append(chain)
        self.descendants={n:np.array([n in c for c in chains]) for n in self.nodes}
        self.order=sorted(range(len(chains)),key=lambda n:len(chains[n]))
        adjacent=np.asarray(faces)[np.any(np.asarray(faces)==palm_vertex,axis=1)]
        if not len(adjacent):raise ValueError('Palm vertex has no triangle neighborhood')
        self.vertices,remap=np.unique(adjacent,return_inverse=True);self.triangles=remap.reshape(-1,3)
        self.palm=int(np.flatnonzero(self.vertices==palm_vertex)[0])
        parts=SkinEvaluator(rig).parts
        if len(parts)!=1:raise ValueError('Initial native-SOMA adapter requires one mesh primitive')
        nodes,points,weights=parts[0]
        self.skin_nodes=nodes[self.vertices];self.skin_points=points[self.vertices];self.weights=weights[self.vertices]
        self.rotation=Rotation.from_quat(placement['rotation_xyzw']).as_matrix();self.translation=np.array(placement['translation_m'])
        self.dim=len(self.nodes)*3

    def pose(self,frame,x):
        local=self.local[frame].copy()
        for node,delta in zip(self.nodes,Rotation.from_rotvec(np.asarray(x).reshape(-1,3)).as_matrix()):
            local[node,:3,:3]=local[node,:3,:3]@delta
        world=np.empty_like(local)
        for n in self.order:
            parent=self.rig.parents[n];world[n]=local[n] if parent<0 else world[parent]@local[n]
        return world

    def point_pair(self,world,axes,node):
        p=world[node,:3,3];j=np.zeros((3,self.dim))
        for i,(edited,axis) in enumerate(zip(self.nodes,axes)):
            if self.descendants[edited][node]:j[:,3*i:3*i+3]=np.cross(axis.T,p-world[edited,:3,3]).T
        return p,j

    def frame_pair(self,frame,x):
        world=self.pose(frame,x)
        axes=[world[n,:3,:3]@right_jacobian(v) for n,v in zip(self.nodes,np.asarray(x).reshape(-1,3))]
        components=np.einsum('vkij,vkj->vki',world[self.skin_nodes,:3,:],self.skin_points)
        points=np.sum(components*self.weights[:,:,None],axis=1);jac=np.zeros((len(points),3,self.dim))
        for i,(node,axis) in enumerate(zip(self.nodes,axes)):
            influence=self.weights*self.descendants[node][self.skin_nodes]
            delta=np.sum((components-world[node,:3,3])*influence[:,:,None],axis=1)
            jac[:,:,i*3:i*3+3]=np.cross(axis.T[None,:,:],delta[:,None,:]).transpose(0,2,1)
        triangles=points[self.triangles];derivatives=jac[self.triangles]
        a,b=triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]
        da,db=derivatives[:,1]-derivatives[:,0],derivatives[:,2]-derivatives[:,0]
        raw_normal=np.cross(a,b).sum(axis=0)
        jnormal=(np.cross(da.transpose(0,2,1),b[:,None,:])+np.cross(a[:,None,:],db.transpose(0,2,1))).sum(axis=0).T
        normal,jnormal=unit_pair(raw_normal,jnormal)
        wrist,jwrist=self.point_pair(world,axes,self.wrist)
        knuckles=[self.point_pair(world,axes,n) for n in self.knuckles]
        direction=np.mean([p for p,j in knuckles],axis=0)-wrist
        jd=np.mean([j for p,j in knuckles],axis=0)-jwrist
        projected=direction-normal*(normal@direction)
        jp=jd-jnormal*(normal@direction)-normal[:,None]*(normal@jd+direction@jnormal)
        tangent,jtangent=unit_pair(projected,jp)
        r=self.rotation
        return (r@points[self.palm]+self.translation,r@normal,r@tangent,
                r@jac[self.palm],r@jnormal,r@jtangent)


class PairFitter:
    def __init__(self,left,right,event,fade=15):
        if len(left.local)!=len(right.local):raise ValueError('Actors need the same clock')
        self.actors=[left,right];self.event=event;self.envelope=envelope(len(left.local),event,fade)
        self.sizes=[a.dim for a in self.actors];self.bounds=np.concatenate([np.repeat(a.limits/np.sqrt(3),3) for a in self.actors])
        # Fixed-axis envelope changes commute, so this bound also bounds the
        # adjacent geodesic edit. Reduce amplitude boxes if the fade is short.
        adjacent=float(np.abs(np.diff(self.envelope)).max())
        self.bounds=np.minimum(self.bounds,np.radians(5)/(np.sqrt(3)*adjacent))

    def objective_pair(self,x):
        n=self.sizes[0];a=self.actors[0].frame_pair(self.event,x[:n]);b=self.actors[1].frame_pair(self.event,x[n:])
        residual=np.r_[(a[0]-b[0])*100,(a[1]+b[1])*2,(a[2]-b[2])*2,x*.2]
        jac=np.vstack([np.c_[a[3],-b[3]]*100,np.c_[a[4],b[4]]*2,np.c_[a[5],-b[5]]*2,np.eye(len(x))*.2])
        return residual,jac

    def solve(self):
        result=least_squares(lambda x:self.objective_pair(x)[0],np.zeros(len(self.bounds)),
            jac=lambda x:self.objective_pair(x)[1],bounds=(-self.bounds,self.bounds),max_nfev=100,ftol=1e-9,xtol=1e-9,gtol=1e-9)
        x=np.clip(result.x,-self.bounds,self.bounds)
        initial=self.objective_pair(np.zeros(len(x)))[0];final=self.objective_pair(x)[0]
        if not np.isfinite(x).all() or final@final>initial@initial:raise ValueError('No finite non-worsening solution')
        return x,dict(success=bool(result.success),status=int(result.status),evaluations=int(result.nfev),
            initial_squared_residual=float(initial@initial),final_squared_residual=float(final@final),
            limits='Local edit angles, not anatomical joint limits. Root, torso and legs fixed; at most 5 degrees adjacent edit under the envelope.',
            quality_approved=False)
