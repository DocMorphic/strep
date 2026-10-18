"""Evaluate original-clock frames without exponentiating every source frame.

Whole-clock edit bounds are still checked. Selection does not create a new
clock, change permissions or establish motion/scene acceptance.
"""
import torch
from articulated_track import ArticulatedTrack


class SampledArticulatedTrack(ArticulatedTrack):
    def at_frames(self,controls,frame_indices):
        if (not isinstance(frame_indices,(list,tuple)) or not 1<=len(frame_indices)<=self.frames
                or any(type(f) is not int or not 0<=f<self.frames for f in frame_indices)
                or len(set(frame_indices))!=len(frame_indices)):
            raise ValueError('Distinct original integer frame indices required')
        values=self.vectors(controls)
        if torch.any(torch.linalg.vector_norm(values,dim=-1)>1):
            raise ValueError('Whole original clock exceeds declared edit budget; no clipping')
        ids=torch.tensor(frame_indices,dtype=torch.long,device=values.device)
        selected=values[ids];vector=selected[:,:len(self.joints)]*self._limits[None,:,None]
        x,y,z=vector.unbind(-1);zero=torch.zeros_like(x)
        skew=torch.stack([zero,-z,y,z,zero,-x,-y,x,zero],-1).reshape(*vector.shape[:-1],3,3)
        delta=torch.matrix_exp(skew)
        local=torch.stack([self._local[ids,j] if j not in self._lookup else self._local[ids,j]@delta[:,self._lookup[j]] for j in range(self._local.shape[1])],1)
        local=torch.where(self._fixed[ids,None,None,None],self._local[ids],local)
        roots=self._root[ids] if self.maximum_root_translation_m==0 else self._root[ids]+selected[:,-1]*self.maximum_root_translation_m
        roots=torch.where(self._root_fixed[ids,None],self._root[ids],roots)
        return local,roots
