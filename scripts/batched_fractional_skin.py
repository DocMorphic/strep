"""Batch local finite differences, then propagate the exact FK product rule.

Keeps the exported float32-time local SLERP and the original 1e-6 derivative
step. This separate adapter does not change any running solver's implementation.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from fast_path_skin import FastTrajectoryActor
from paired_hand_trajectory import interpolate_rotations


def local_pair(actor,matrix,frame,x):
    low,high=int(np.floor(frame)),int(np.ceil(frame))
    if not 0<=low<high<len(actor.local):raise ValueError('Interior fractional sample required')
    x=np.asarray(x,dtype=float);dim=matrix.shape[1]*actor.dim
    if x.shape!=(dim,) or not np.isfinite(x).all():raise ValueError('Finite control vector required')
    values=matrix@x.reshape(-1,actor.dim)
    left,right=actor.local[low].copy(),actor.local[high].copy()
    for index,local in [(low,left),(high,right)]:
        local[actor.nodes,:3,:3]=local[actor.nodes,:3,:3]@Rotation.from_rotvec(values[index].reshape(-1,3)).as_matrix()
    a,b,t=[float(np.float32(f/30)) for f in [low,high,frame]];alpha=(t-a)/(b-a)
    local=left.copy();local[:,:3,:3]=interpolate_rotations(left[:,:3,:3],right[:,:3,:3],alpha)
    local[:,:3,3]=(1-alpha)*left[:,:3,3]+alpha*right[:,:3,3]
    derivative=np.zeros(local.shape+(dim,));step=1e-6
    columns=np.flatnonzero(np.repeat(np.any(matrix[[low,high]]!=0,axis=0),actor.dim))
    if len(columns):
        # Each control coordinate changes just one edited local rotation. Both
        # adjacent keys must move before their interpolated rotation is formed.
        knots=columns//actor.dim;components=columns%actor.dim;joints=components//3;axes=components%3
        nodes=np.asarray(actor.nodes)[joints];rotations=[]
        for index in [low,high]:
            vectors=np.repeat(values[index].reshape(-1,3)[joints,None,:],2,axis=1)
            rows=np.arange(len(columns));vectors[rows,0,axes]+=step*matrix[index,knots];vectors[rows,1,axes]-=step*matrix[index,knots]
            deltas=Rotation.from_rotvec(vectors.reshape(-1,3)).as_matrix().reshape(-1,2,3,3)
            rotations.append((actor.local[index,nodes,None,:3,:3]@deltas).reshape(-1,3,3))
        sampled=interpolate_rotations(*rotations,alpha).reshape(-1,2,3,3)
        differences=(sampled[:,0]-sampled[:,1])/(2*step)
        for n,col,d in zip(nodes,columns,differences):derivative[n,:3,:3,col]=d
    return local,derivative


class BatchedFractionalActor(FastTrajectoryActor):
    def world_pair(self,frame,x):
        if not np.isfinite(frame) or not 0<=frame<len(self.local):raise ValueError('Sample outside clip')
        if float(frame).is_integer():return super().world_pair(frame,x)
        if self.cache is not None and self.cache[0]==frame and np.array_equal(x,self.cache[1]):return self.cache[2:]
        local,dlocal=local_pair(self.base,self.matrix,frame,x)
        world=np.empty_like(local);jac=np.zeros(local.shape+(self.dim,))
        for node in self.order:
            parent=self.rig.parents[node]
            if parent<0:world[node]=local[node];jac[node]=dlocal[node]
            else:
                world[node]=world[parent]@local[node]
                jac[node]=np.einsum('ijd,jk->ikd',jac[parent],local[node])+np.einsum('ij,jkd->ikd',world[parent],dlocal[node])
        self.cache=(frame,np.array(x,copy=True),world,jac)
        return world,jac
