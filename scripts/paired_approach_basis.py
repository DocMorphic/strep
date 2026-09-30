"""Coupled-approach parameterization preserving the retained contact and release."""
import numpy as np
from scipy.spatial.transform import Rotation
from paired_guarded_temporal import GuardedEdit
from paired_temporal_neighbor import rotation_channels


class ApproachActor:
    def __init__(self,document,binary,reference_document,reference_binary,names,frames):
        self.knots=np.array([63.,66.,70.,74.,75.]);self.free=list(range(64,75))
        self.base=GuardedEdit(document,binary,names,self.free,frames,dict(event=[73,77]),5.)
        reference=rotation_channels(reference_document,reference_binary)
        self.reference={};values=[]
        for node in self.base.nodes:
            if document['nodes'][node]['name']!=reference_document['nodes'][node]['name']:raise ValueError('Matching reference rig nodes required')
            np.testing.assert_array_equal(reference[node][1],self.base.channels[node][1])
            self.reference[node]=Rotation.from_quat(reference[node][2][self.free])
            values.append((self.reference[node].inv()*Rotation.from_quat(self.base.channels[node][2][self.free])).as_rotvec())
        self.original_vectors=np.stack(values,axis=1)
        self.matrix=np.stack([np.interp(self.free,self.knots,np.eye(5)[i]) for i in [1,2,3]],axis=1)
        self.size=3*len(names)*3

    def vectors(self,controls):
        controls=np.asarray(controls,float)
        if controls.shape!=(self.size,) or not np.isfinite(controls).all():raise ValueError('Finite matching approach controls required')
        return self.original_vectors+np.einsum('fk,kjc->fjc',self.matrix,controls.reshape(3,len(self.base.nodes),3))

    def parameters(self,controls):
        vectors=self.vectors(controls)
        if not np.any(controls):return np.zeros(self.base.size)
        result=[]
        for j,node in enumerate(self.base.nodes):
            desired=self.reference[node]*Rotation.from_rotvec(vectors[:,j])
            current=Rotation.from_quat(self.base.channels[node][2][self.free])
            result.append((current.inv()*desired).as_rotvec()/self.base.limit)
        return np.stack(result,axis=1).ravel()

    def world(self,controls):return self.base.world(self.parameters(controls))

    def world_pair(self,controls,step=1e-6):
        if not np.isfinite(step) or step<=0:raise ValueError('Positive finite derivative step required')
        controls=np.asarray(controls,float);world=self.world(controls);jacobian=np.empty(world.shape+(self.size,))
        for col in range(self.size):
            delta=np.zeros(self.size);delta[col]=step
            jacobian[...,col]=(self.world(controls+delta)-self.world(controls-delta))/(2*step)
        return world,jacobian

    def export(self,controls,path):self.base.export(self.parameters(controls),path)


class BoundSkin:
    def __init__(self,rig):
        if len(rig.primitives)!=1 or rig.primitives[0]['joints'] is None:raise ValueError('One skinned primitive required')
        primitive=rig.primitives[0];indices=primitive['joints']
        self.nodes=np.asarray(rig.joints)[indices];self.weights=primitive['weights']
        vertices=np.c_[primitive['positions'],np.ones(len(primitive['positions']))]
        self.points=np.einsum('vkij,vj->vki',rig.inverse[indices],vertices)

    def evaluate(self,world,frames,vertices):
        frames=np.asarray(frames,int);vertices=np.asarray(vertices,int)
        if frames.ndim!=1 or frames.shape!=vertices.shape:raise ValueError('Matching frame/vertex rows required')
        result=np.empty((len(vertices),3))
        for start in range(0,len(vertices),128):
            ids=vertices[start:start+128];times=frames[start:start+128];nodes=self.nodes[ids]
            result[start:start+128]=np.einsum('nkij,nkj,nk->ni',world[times[:,None],nodes,:3,:],self.points[ids],self.weights[ids])
        return result

    def derivative(self,jacobian,frames,vertices):
        frames=np.asarray(frames,int);vertices=np.asarray(vertices,int)
        if frames.ndim!=1 or frames.shape!=vertices.shape:raise ValueError('Matching frame/vertex rows required')
        result=np.empty((len(vertices),3,jacobian.shape[-1]))
        for start in range(0,len(vertices),128):
            ids=vertices[start:start+128];times=frames[start:start+128];nodes=self.nodes[ids]
            result[start:start+128]=np.einsum('nkijd,nkj,nk->nid',jacobian[times[:,None],nodes,:3,:,:],self.points[ids],self.weights[ids])
        return result
