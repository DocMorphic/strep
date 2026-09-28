"""Temporal root/leg correction with frozen root and foot acceleration bounds."""
import numpy as np
from block_release_fit import BlockProblem, norm_envelope_pair


def root_pair(world, frames, free, root, width):
    positions = world[:,root,:3,3].copy()
    jac = np.zeros((*positions.shape,width))
    for i,frame in enumerate(frames):
        for j,column in enumerate(free):
            if column < 3: jac[frame,column,i*len(free)+j] = 1.
    return positions,jac


class RootBlockProblem(BlockProblem):
    def __init__(self,fitter,initial,evaluator,frames,free,envelope,target):
        dummy = dict(centers=target['centers'],side_index=0,limit_m_s2=0.)
        super().__init__(fitter,initial,evaluator,frames,free,envelope,envelope['safety_caps_m_s2'],dummy)
        self.root_target=target;self.root=fitter.spec['root_node']
        ancestor=fitter.rig.parents[self.root]
        while ancestor >= 0:
            if ancestor in fitter.nodes: raise ValueError('Edited ancestor would invalidate translation-only root derivative')
            ancestor=fitter.rig.parents[ancestor]
        self.root_cache_x=None

    def evaluate(self,x,quantized=True):
        if quantized and self.root_cache_x is not None and np.array_equal(x,self.root_cache_x):return self.root_cache
        self.cached_x=None
        base=super().evaluate(x,quantized)
        world=np.array([self.evaluator.pose(w) for w in self.world]) if quantized else self.world.copy()
        for f in self.frames:
            w=self.fitter.pose(int(f),base[5][f])[0];world[f]=self.evaluator.pose(w) if quantized else w
        positions,jac=root_pair(world,self.frames,self.free,self.root,self.width)
        acceleration=np.diff(positions,n=2,axis=0)*self.fps**2
        derivative=np.diff(jac,n=2,axis=0)*self.fps**2
        indices=self.acceleration_indices;caps=np.asarray(self.envelope['root_safety_caps_m_s2'])
        margins,rows=norm_envelope_pair(acceleration[indices,None,:],derivative[indices,None,:,:],caps[indices,None],1.)
        target=np.asarray(self.root_target['centers'])-1;vectors=acceleration[target];magnitude=np.linalg.norm(vectors,axis=1)
        excess=np.maximum(magnitude-self.root_target['limit_m_s2'],0.);direction=vectors/np.maximum(magnitude[:,None],1e-30)
        objective=float(excess@excess);gradient=2*np.einsum('s,si,sip->p',excess,direction,derivative[target])
        result=(objective,gradient,np.r_[base[2],margins],np.vstack([base[3],rows]),base[4],base[5])
        if quantized:self.root_cache_x=np.asarray(x).copy();self.root_cache=result
        return result
