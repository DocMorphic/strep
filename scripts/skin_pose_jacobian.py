"""Complete affine-pose LBS values and derivatives, streamed over vertices."""
import numpy as np


class SkinPoseJacobian:
    def __init__(self,indices,weights,bind_points,joint_count,*,maximum_bytes=64*1024**2):
        ids,w,b=[np.asarray(v) for v in (indices,weights,bind_points)]
        if (ids.dtype.kind not in 'iu' or ids.ndim!=2 or not 1<=len(ids)<=1000000 or not 1<=ids.shape[1]<=32
                or w.shape!=ids.shape or b.shape!=ids.shape+(3,) or type(joint_count) is not int or not 1<=joint_count<=256
                or ids.min()<0 or ids.max()>=joint_count):raise ValueError('Complete bounded skin indices, weights, bind points and joint count required')
        if any(v.dtype.kind not in 'fiu' or not np.isfinite(v).all() or np.any(abs(v)>1e6) for v in (w,b)):raise ValueError('Finite real original skin coefficients required')
        storage=(ids.size+w.size+b.size)*8
        if type(maximum_bytes) is not int or not 1<=maximum_bytes<=64*1024**2 or 4*storage>maximum_bytes:raise ValueError('Complete skin allocation budget exceeded; no influence truncation')
        self._ids=np.array(ids,dtype=np.int64,copy=True);self._weights=np.array(w,dtype=float,copy=True);self._bind=np.array(b,dtype=float,copy=True)
        self.joint_count=joint_count;self.maximum_bytes=maximum_bytes;self._storage=storage

    def frame(self,rotations,positions,rotation_jacobian,position_jacobian,*,chunk_vertices=128):
        r,p,dr,dp=[np.asarray(v) for v in (rotations,positions,rotation_jacobian,position_jacobian)];j=self.joint_count
        if r.shape!=(j,3,3) or p.shape!=(j,3) or dr.ndim!=4 or dr.shape[:3]!=(j,3,3) or not 1<=dr.shape[3]<=384 or dp.shape!=(j,3,dr.shape[3]):raise ValueError('Complete matching pose and every control derivative column required')
        if any(v.dtype.kind not in 'fiu' or not np.isfinite(v).all() or np.any(abs(v)>1e6) for v in (r,p,dr,dp)):raise ValueError('Finite bounded real pose and derivative data required')
        if type(chunk_vertices) is not int or not 1<=chunk_vertices<=4096:raise ValueError('Explicit bounded vertex chunk required')
        vertices=len(self._ids);columns=dr.shape[3];chunk=min(vertices,chunk_vertices);width=self._ids.shape[1]
        estimate=4*(self._storage+sum(v.size*8 for v in (r,p,dr,dp)))+2*vertices*3*(1+columns)*8+4*chunk*width*3*(columns+4)*8
        if estimate>self.maximum_bytes:raise ValueError('Complete pose-Jacobian allocation budget exceeded; no vertex/column truncation')
        r,p,dr,dp=[np.array(v,dtype=float,copy=True) for v in (r,p,dr,dp)];value=np.empty((vertices,3));jac=np.empty((vertices,3,columns))
        for first in range(0,vertices,chunk_vertices):
            last=min(first+chunk_vertices,vertices);ids=self._ids[first:last];bind=self._bind[first:last];weight=self._weights[first:last]
            value[first:last]=np.sum(weight[:,:,None]*(np.einsum('vwij,vwj->vwi',r[ids],bind)+p[ids]),axis=1)
            jac[first:last]=np.sum(weight[:,:,None,None]*(np.einsum('vwijc,vwj->vwic',dr[ids],bind)+dp[ids]),axis=1)
        return value,jac
