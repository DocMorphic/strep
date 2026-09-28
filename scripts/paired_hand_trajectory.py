"""Bounded timed arm corrections with export-compatible fractional sampling.

Finite differences differentiate the actual interpolated local rotations. The
source motion, not an interpolated world-space skeleton, defines each sample.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from paired_hand_fit import PairFitter
from paired_palm_region import RegionFitter
from target_rig_contact import SkinEvaluator


def basis(envelope,knots):
    knots=np.asarray(knots,dtype=float)
    if knots.ndim!=1 or len(knots)<2 or not np.isfinite(knots).all() or np.any(np.diff(knots)<=0):raise ValueError('Ordered finite knots required')
    frames=np.arange(len(envelope));matrix=np.stack([np.interp(frames,knots,np.eye(len(knots))[k]) for k in range(len(knots))],axis=1)
    return matrix*np.asarray(envelope)[:,None]


def interpolate_rotations(left,right,alpha):
    a=Rotation.from_matrix(left).as_quat();b=Rotation.from_matrix(right).as_quat()
    dot=np.sum(a*b,axis=1);b=np.where((dot<0)[:,None],-b,b);dot=np.abs(dot).clip(0,1)
    angle=np.arccos(dot);sine=np.sin(angle);near=sine<1e-7
    weight_a=np.full(len(a),1-alpha);weight_b=np.full(len(a),alpha)
    np.divide(np.sin((1-alpha)*angle),sine,out=weight_a,where=~near)
    np.divide(np.sin(alpha*angle),sine,out=weight_b,where=~near)
    q=weight_a[:,None]*a+weight_b[:,None]*b
    return Rotation.from_quat(q).as_matrix()


class TrajectoryActor:
    def __init__(self,actor,matrix):
        self.base=actor;self.matrix=matrix;self.dim=matrix.shape[1]*actor.dim;self.cache=None
        self.skin_nodes,self.skin_points,self.weights=SkinEvaluator(actor.rig).parts[0]

    def __getattr__(self,name):return getattr(self.base,name)

    def values(self,x):return self.matrix@np.asarray(x).reshape(-1,self.base.dim)

    def pose(self,frame,x):
        if not np.isfinite(frame) or not 0<=frame<=len(self.local)-1:raise ValueError('Sample outside clip')
        low=int(np.floor(frame));high=int(np.ceil(frame));values=self.values(x)
        locals=[]
        for index in [low,high]:
            local=self.local[index].copy()
            local[self.nodes,:3,:3]=local[self.nodes,:3,:3]@Rotation.from_rotvec(values[index].reshape(-1,3)).as_matrix()
            locals.append(local)
        local=locals[0]
        if high!=low:
            # glTF stores float32 key times and decodes the same requested time.
            a,b,t=[float(np.float32(f/30)) for f in [low,high,frame]];alpha=(t-a)/(b-a)
            local=local.copy();local[:,:3,:3]=interpolate_rotations(locals[0][:,:3,:3],locals[1][:,:3,:3],alpha)
            local[:,:3,3]=(1-alpha)*locals[0][:,:3,3]+alpha*locals[1][:,:3,3]
        world=np.empty_like(local)
        for node in self.order:
            parent=self.rig.parents[node];world[node]=local[node] if parent<0 else world[parent]@local[node]
        return world

    def world_pair(self,frame,x):
        if self.cache is not None and self.cache[0]==frame and np.array_equal(x,self.cache[1]):return self.cache[2:]
        world=self.pose(frame,x);jac=np.zeros(world.shape+(self.dim,));step=1e-6
        active=np.repeat(np.any(self.matrix[[int(np.floor(frame)),int(np.ceil(frame))]]!=0,axis=0),self.base.dim)
        for col in np.flatnonzero(active):
            d=np.zeros(self.dim);d[col]=step
            jac[...,col]=(self.pose(frame,x+d)-self.pose(frame,x-d))/(2*step)
        self.cache=(frame,np.array(x,copy=True),world,jac)
        return world,jac

    def skin_pair(self,frame,x,vertices):
        world,jac=self.world_pair(frame,x);nodes=self.skin_nodes[vertices];weights=self.weights[vertices];points=self.skin_points[vertices]
        p=np.einsum('vkij,vkj,vk->vi',world[nodes,:3,:],points,weights)
        j=np.einsum('vkijd,vkj,vk->vid',jac[nodes,:3,:,:],points,weights)
        return p@self.rotation.T+self.translation,np.einsum('ij,vjd->vid',self.rotation,j)


class TrajectoryFitter:
    def __init__(self,actors,event=75,fade=15,knots=(65,75,85)):
        self.base=RegionFitter(*actors,event=event,fade=fade);self.event=event
        self.matrix=basis(self.base.envelope,knots);self.knots=list(knots)
        self.actors=[TrajectoryActor(a,self.matrix) for a in actors];self.sizes=[a.dim for a in self.actors]
        self.bounds=np.concatenate([np.tile(self.base.bounds[i*actors[0].dim:(i+1)*actors[0].dim],len(knots)) for i in range(2)])
        self.maps=[np.kron(self.matrix,np.eye(a.dim)) for a in actors]
        self.event_map=np.zeros((sum(a.dim for a in actors),sum(self.sizes)))
        offset=0;out=0
        for a,m,size in zip(actors,self.maps,self.sizes):
            self.event_map[out:out+a.dim,offset:offset+size]=m[event*a.dim:(event+1)*a.dim]
            offset+=size;out+=a.dim

    def expand(self,values):
        parts=np.split(np.asarray(values),[self.base.sizes[0]])
        return np.concatenate([np.tile(v,len(self.knots)) for v in parts])

    def values(self,x):
        parts=np.split(np.asarray(x),[self.sizes[0]])
        return np.concatenate([a.values(v) for a,v in zip(self.actors,parts)],axis=1)

    def step_pair(self,x):
        values=self.values(x);delta=np.diff(values,axis=0).reshape(len(values)-1,-1,3);radius=np.radians(5)
        residual=1-np.sum(delta**2,axis=2)/radius**2
        jac=np.zeros(residual.shape+(len(x),));offset=0;joint=0
        for a,m,size in zip(self.base.actors,self.maps,self.sizes):
            dm=np.diff(m.reshape(len(values),a.dim,size),axis=0).reshape(len(values)-1,-1,3,size)
            jac[:,joint:joint+a.dim//3,offset:offset+size]=-2*np.einsum('fji,fjid->fjd',delta[:,joint:joint+a.dim//3],dm)/radius**2
            offset+=size;joint+=a.dim//3
        return residual.ravel(),jac.reshape(-1,len(x))


class TemporalSurface:
    def __init__(self,fitter,frame,records):self.fitter=fitter;self.frame=frame;self.records=records

    def clearance(self,x,margin=.001):
        f=self.fitter;n=f.sizes[0];parts=[x[:n],x[n:]];offset=[0,n];gaps=[];derivatives=[]
        for record in self.records:
            if not record['points']:continue
            source,target=record['source'],record['target'];ids,triangles,bary,normals=map(np.asarray,zip(*record['points']))
            p,jp=f.actors[source].skin_pair(self.frame,parts[source],ids.astype(int))
            q,jq=f.actors[target].skin_pair(self.frame,parts[target],triangles.astype(int).ravel())
            q=np.einsum('ni,nij->nj',bary,q.reshape(-1,3,3));jq=np.einsum('ni,nijd->njd',bary,jq.reshape(-1,3,3,f.sizes[target]))
            gaps.append(np.einsum('ni,ni->n',p-q,normals)-margin);j=np.zeros((len(ids),len(x)))
            j[:,offset[source]:offset[source]+f.sizes[source]]=np.einsum('ni,nid->nd',normals,jp)
            j[:,offset[target]:offset[target]+f.sizes[target]]=-np.einsum('ni,nid->nd',normals,jq);derivatives.append(j)
        return (np.concatenate(gaps),np.vstack(derivatives)) if gaps else (np.empty(0),np.empty((0,len(x))))
