"""Root/leg temporal blocks retaining the whole-support source's measured guards."""
import numpy as np
from scipy.spatial.transform import Rotation
from root_release_block import RootBlockProblem
from block_release_fit import norm_envelope_pair
from rig_transition import localize


class CoupledBreadthBlock(RootBlockProblem):
    def __init__(self,fitter,initial,evaluator,frames,envelope,target,reference_world):
        self.reference_world=np.asarray(reference_world)
        self.reference_skin=np.asarray([fitter.rig.vertices(w) for w in reference_world])
        self.position_eps=1e-6
        self.radius=.01
        super().__init__(fitter,initial,evaluator,frames,list(range(initial.shape[1])),envelope,target)
        self.augmented_x=None
        # The float32 pose reconstruction must actually match the saved source.
        rebuilt=np.array([evaluator.pose(w) for w in self.world])
        if np.max(np.abs(rebuilt-self.reference_world[::2]))>1e-6:raise ValueError('Parameter reconstruction differs from source export')
        local=localize(self.reference_world[::2],fitter.rig.parents)
        rotations=local[:-1,:,:3,:3].transpose(0,1,3,2)@local[1:,:,:3,:3]
        steps=Rotation.from_matrix(rotations.reshape(-1,3,3)).magnitude().reshape(len(initial)-1,-1)
        self.rotation_peaks=steps.max(0);self.rotation_p95=np.percentile(steps,95,axis=0)

    def evaluate(self,x,quantized=True):
        if quantized and self.augmented_x is not None and np.array_equal(x,self.augmented_x):return self.augmented
        base=super().evaluate(x,quantized);values=base[5];margins=base[2].copy();jac=base[3].copy();index=0
        additions=[];derivatives=[]
        for block,frame in enumerate(self.frames):
            positions,j=self.fitter.surface_jacobian(int(frame),values[frame])
            if quantized:positions=self.fitter.rig.vertices(self.evaluator.pose(self.fitter.pose(int(frame),values[frame])[0]))
            n=len(positions);source=self.reference_skin[2*frame];depth=np.maximum(0.,-source[:,1])
            # Replace the inherited 5mm floor rule with per-vertex source depths.
            margins[index:index+n]=(positions[:,1]+depth+self.position_eps)/.005
            index+=n+sum(self.envelope['active_frames'][frame])
            offset=block*len(self.free)
            for side,ids in enumerate(self.patches):
                name=list(self.fitter.spec['patches'])[side]
                guide=self.fitter.support_guides[name]
                if guide['weights'][frame]<=0:continue
                anchor=np.asarray(guide['anchors_xz_m'][frame]);point=positions[ids].mean(0)[[0,2]]
                old=source[ids].mean(0)[[0,2]];cap=np.linalg.norm(old-anchor)+self.position_eps
                full=np.zeros((2,self.width));full[:,offset:offset+len(self.free)]=j[ids].mean(0)[[0,2]][:,self.free]
                m,d=norm_envelope_pair((point-anchor)[None,:],full[None,:,:],np.array([cap]),.01)
                additions.extend(m);derivatives.extend(d)
            shift=values[frame,:3]-self.initial[frame,:3];full=np.zeros((3,self.width));full[:,offset:offset+3]=np.eye(3)
            m,d=norm_envelope_pair(shift[None,:],full[None,:,:],np.array([self.radius]),.01)
            additions.extend(m);derivatives.extend(d)
        result=(base[0],base[1],np.r_[margins,additions],np.vstack([jac,derivatives]),base[4],base[5])
        if quantized:self.augmented_x=np.asarray(x).copy();self.augmented=result
        return result

    def geometric_guard(self,values):
        world=self.world.copy()
        for frame in self.frames:world[frame]=self.fitter.pose(int(frame),values[frame])[0]
        edges=sorted({end for f in self.frames for end in (f,f+1) if 1<=end<len(values)})
        for end in edges:
            half=self.evaluator.half_pose(world[end-1],world[end],int(end-1))
            depth=np.maximum(0.,-self.fitter.rig.vertices(half)[:,1])
            old=np.maximum(0.,-self.reference_skin[2*end-1,:,1])
            if np.max(depth-old)>self.position_eps:return False
        serialized=np.array([self.evaluator.pose(w) for w in world])
        # A normalized cone residual tolerance does not imply the same physical
        # distance allowance. Match the independent audit in metres before an
        # optimizer step can be retained.
        for frame in self.frames:
            positions=self.fitter.rig.vertices(serialized[frame]);source=self.reference_skin[2*frame]
            for side,patch in self.fitter.spec['patches'].items():
                guide=self.fitter.support_guides[side]
                if guide['weights'][frame]<=0:continue
                ids=patch['vertices'];anchor=np.asarray(guide['anchors_xz_m'][frame])
                before=np.linalg.norm(source[ids].mean(0)[[0,2]]-anchor)
                after=np.linalg.norm(positions[ids].mean(0)[[0,2]]-anchor)
                if after-before>self.position_eps:return False
        local=localize(serialized,self.fitter.rig.parents)
        delta=local[:-1,:,:3,:3].transpose(0,1,3,2)@local[1:,:,:3,:3]
        steps=Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude().reshape(len(world)-1,-1)
        return bool(np.all(steps.max(0)<=self.rotation_peaks+1e-6) and np.all(np.percentile(steps,95,axis=0)<=self.rotation_p95+1e-6))
