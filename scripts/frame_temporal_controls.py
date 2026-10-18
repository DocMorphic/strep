"""Lift frame-local derivatives into complete convex temporal control columns.

This is a coordinate map, not a motion generator or acceptance test. Interval,
contact and global-peak derivatives must be recomputed through their full clocks.
"""
import numpy as np


class FrameTemporalControls:
    def __init__(self,weights,*,blocks,groups,constant_groups=()):
        w=np.asarray(weights)
        if (w.ndim!=2 or not 3<=len(w)<=300 or not 1<=w.shape[1]<=8 or w.dtype.kind not in 'fiu'
                or not np.isfinite(w).all() or np.any(w<0) or np.any(w>1) or np.any(w.sum(1)!=1)):
            raise ValueError('Complete finite nonnegative temporal partition of exactly one required; no normalization')
        if (type(blocks) is not int or not 1<=blocks<=8 or type(groups) is not int or not 1<=groups<=17
                or blocks*groups*3*w.shape[1]>384):raise ValueError('Complete bounded three-vector control blocks required')
        if (not isinstance(constant_groups,(list,tuple)) or any(type(g) is not int or not 0<=g<groups for g in constant_groups)
                or len(set(constant_groups))!=len(constant_groups)):raise ValueError('Distinct explicit constant groups in each block required')
        self._weights=np.array(w,dtype=float,copy=True);self._blocks=blocks;self._groups=groups;self._constant=tuple(constant_groups)

    @property
    def source_columns(self):return self._blocks*self._groups*3

    @property
    def expanded_columns(self):return self.source_columns*self._weights.shape[1]

    @property
    def weights(self):return self._weights.copy()

    def _controls(self,value,expanded):
        x=np.asarray(value);size=self.expanded_columns if expanded else self.source_columns
        if (x.shape!=(size,) or x.dtype.kind not in 'fiu' or not np.isfinite(x).all()
                or np.any(np.linalg.norm(x.reshape(-1,3),axis=1)>1)):
            raise ValueError('Every finite original bounded control-vector ball required')
        return np.array(x,dtype=float,copy=True)

    def embed(self,controls):
        """Duplicate source knots, ordered block/knot/group/component."""
        x=self._controls(controls,False).reshape(self._blocks,1,self._groups,3)
        return np.repeat(x,self._weights.shape[1],axis=1).ravel()

    def at_frames(self,controls,frames):
        """Normalized local controls before the caller's original edit envelope."""
        x=self._controls(controls,True).reshape(self._blocks,self._weights.shape[1],self._groups,3);ids=self._frames(frames)
        result=np.einsum('fk,bkgc->fbgc',self._weights[ids],x)
        for g in self._constant:result[:,:,g]=x[:,:,g].mean(axis=1)[None]
        if np.any(np.linalg.norm(result,axis=-1)>1):raise ValueError('Floating frame evaluation exceeds original ball; no clipping')
        return result.reshape(len(ids),self.source_columns)

    def _frames(self,frames):
        ids=np.asarray(frames)
        if ids.ndim!=1 or not 1<=len(ids)<=8192 or ids.dtype.kind not in 'iu' or np.any(ids<0) or np.any(ids>=len(self._weights)):
            raise ValueError('An explicit original frame for every complete local row required')
        return ids.astype(int,copy=True)

    def lift(self,jacobian,frames,*,chunk_rows=128,maximum_bytes=64*1024**2):
        """Return every row and expanded column; never use for interval rows."""
        j=np.asarray(jacobian);ids=self._frames(frames)
        if (j.shape!=(len(ids),self.source_columns) or j.dtype.kind not in 'fiu' or not np.isfinite(j).all() or np.any(abs(j)>1e6)):
            raise ValueError('Complete finite frame-local rows and source columns required')
        if type(chunk_rows) is not int or not 1<=chunk_rows<=4096 or type(maximum_bytes) is not int or not 1<=maximum_bytes<=64*1024**2:
            raise ValueError('Explicit bounded complete allocation policy required')
        estimate=(j.size+len(j)*self.expanded_columns+2*min(chunk_rows,len(j))*self.source_columns+self._weights.size)*8+ids.nbytes
        if estimate>maximum_bytes:raise ValueError('Complete temporal lift allocation budget exceeded; no rows or columns truncated')
        result=np.empty((len(j),self.expanded_columns));view=result.reshape(len(j),self._blocks,self._weights.shape[1],self._groups,3);source=j.reshape(len(j),self._blocks,self._groups,3)
        for first in range(0,len(j),chunk_rows):
            last=min(first+chunk_rows,len(j));frames_at=ids[first:last]
            for k in range(self._weights.shape[1]):
                factor=np.broadcast_to(self._weights[frames_at,k,None],(last-first,self._groups)).copy()
                if self._constant:factor[:,self._constant]=1/self._weights.shape[1]
                view[first:last,:,k]=source[first:last]*factor[:,None,:,None]
        return result
