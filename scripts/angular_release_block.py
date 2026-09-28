"""Per-joint rotation-step constraints alongside serialized foot preservation."""
import numpy as np
from scipy.spatial.transform import Rotation
from block_release_fit import BlockProblem, norm_envelope_pair
from rig_clearance_fit import right_jacobian
from rig_transition import localize


def skew(v):
    x,y,z=v
    return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


def chord_cap(radians):
    angle=np.asarray(radians,float)
    if not np.isfinite(angle).all() or np.any((angle<0)|(angle>np.pi)):
        raise ValueError('Rotation caps must be finite angles from zero to pi')
    return 2*np.sin(angle/2)


def rotation_steps(rotations):
    delta=rotations[:-1].swapaxes(-1,-2)@rotations[1:]
    return Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude().reshape(delta.shape[:-2])


class AngularBlockProblem(BlockProblem):
    def __init__(self,base,angular):
        self.__dict__.update(base.__dict__)
        self.root=self.fitter.spec['root_node'];self.angular=angular
        self.edges=self.speed_indices+1
        self.rotation_caps=chord_cap(angular['safety_caps_radians'])
        self.angular_cache_x=None
        if any(i<3 for i in self.free):raise ValueError('Angular follow-up must preserve repaired root')
        matrices=self.fitter.local[:,self.fitter.nodes,:3,:3]
        if np.max(np.abs(matrices.swapaxes(-1,-2)@matrices-np.eye(3)))>1e-8 or np.max(np.abs(np.linalg.det(matrices)-1))>1e-8:
            raise ValueError('Proper local rotations required for chord equivalence')
        self.initial_rotations=np.array([localize(self.evaluator.pose(w)[None],self.fitter.rig.parents)[0,self.fitter.nodes,:3,:3] for w in self.world])

    def angular_pair(self,x,quantized=True):
        values=self.values(x);count=len(self.fitter.nodes)
        rotations=self.initial_rotations.copy() if quantized else np.array([self.fitter.pose(f,v)[1][self.fitter.nodes,:3,:3] for f,v in enumerate(values)])
        jac=np.zeros((*rotations.shape,self.width))
        for i,frame in enumerate(self.frames):
            vectors=values[frame,3:].reshape(-1,3)
            smooth=self.fitter.local[frame,self.fitter.nodes,:3,:3]@Rotation.from_rotvec(vectors).as_matrix()
            if quantized:
                world=self.evaluator.pose(self.fitter.pose(int(frame),values[frame])[0])
                rotations[frame]=localize(world[None],self.fitter.rig.parents)[0,self.fitter.nodes,:3,:3]
            else:rotations[frame]=smooth
            for j,column in enumerate(self.free):
                node,axis=divmod(int(column)-3,3)
                jac[frame,node,:,:,i*len(self.free)+j]=smooth[node]@skew(right_jacobian(vectors[node])[:,axis])
        # Frobenius(R1-R0)/sqrt(2) = 2*sin(relative_angle/2).
        vectors=np.diff(rotations,axis=0).reshape(len(values)-1,count,9)/np.sqrt(2)
        derivative=np.diff(jac,axis=0).reshape(len(values)-1,count,9,self.width)/np.sqrt(2)
        return vectors,derivative

    def evaluate(self,x,quantized=True):
        if quantized and self.angular_cache_x is not None and np.array_equal(x,self.angular_cache_x):return self.angular_cache
        base=super().evaluate(x,quantized);vectors,jac=self.angular_pair(x,quantized)
        indices=self.edges-1
        margins,rows=norm_envelope_pair(vectors[indices],jac[indices],self.rotation_caps[indices],1e-3)
        target=self.angular['target'];v=vectors[target['end_frame']-1,target['joint_index']];j=jac[target['end_frame']-1,target['joint_index']]
        length=np.linalg.norm(v);excess=max(0.,length-float(chord_cap(target['limit_radians'])));scale=(180/np.pi)**2
        objective=float(excess**2*scale);gradient=2*excess*scale*(v@j)/max(length,1e-30)
        result=(objective,gradient,np.r_[base[2],margins],np.vstack([base[3],rows]),base[4],base[5])
        if quantized:self.angular_cache_x=np.asarray(x).copy();self.angular_cache=result
        return result
