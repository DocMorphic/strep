"""Actual glTF TRS pose edits and complete affine-chain skin derivatives.

No matrix is projected to a rigid transform. Edited existing quaternion tracks
retain sampled scale/translation; every unedited local matrix stays unchanged.
"""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import local_matrix
from bounded_pose_ik import hierarchy_order


def skew(v):
    x,y,z=v
    return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


def right_jacobian(vector):
    hat=skew(vector);angle=np.linalg.norm(vector)
    if angle<1e-6:return np.eye(3)-.5*hat+hat@hat/6
    return np.eye(3)-(1-np.cos(angle))/angle**2*hat+(angle-np.sin(angle))/angle**3*hat@hat


class AffineKeyPose:
    def __init__(self,actor,time_s,nodes,degrees):
        self.actor=actor;self.rig=actor['rig'];self.skin=actor['skin'];self.nodes=list(nodes)
        self.caps=np.radians(np.asarray(degrees,float));self.size=3*len(self.nodes)
        if (not 1<=len(self.nodes)<=16 or len(set(self.nodes))!=len(self.nodes)
                or self.caps.shape!=(len(self.nodes),) or not np.isfinite(self.caps).all()
                or np.any(self.caps<=0) or np.any(self.caps>np.radians(30))
                or any(type(n) is not int or n not in self.rig.joints for n in self.nodes)):
            raise ValueError('Explicit existing affine pose joints and original bounded rotation caps required')
        sampler=actor['sampler'];entries=copy.deepcopy(self.rig.document['nodes'])
        for node,path,clock,values,mode in sampler.channels:
            entries[node][path]=sampler.value(path,clock,values,mode,float(time_s)).tolist()
        for node in self.nodes:
            tracks=[c for c in sampler.channels if c[:2]==(node,'rotation')]
            if len(tracks)!=1 or tracks[0][4]!='LINEAR' or 'matrix' in entries[node]:
                raise ValueError('Existing LINEAR quaternion channels on TRS nodes required')
        self.local=np.array([local_matrix(n) for n in entries]);self.source=sampler.sample(float(time_s))
        self.order=hierarchy_order(self.rig.parents)
        self.rotations=[Rotation.from_quat(entries[n].get('rotation',[0,0,0,1])).as_matrix() for n in self.nodes]
        self.scales=[np.diag(entries[n].get('scale',[1.,1.,1.])) for n in self.nodes]
        self.affected=np.zeros(len(entries),bool)
        for n in self.order:self.affected[n]=n in self.nodes or (self.rig.parents[n]>=0 and self.affected[self.rig.parents[n]])

    def evaluate(self,value):
        value=np.asarray(value,float)
        if value.shape!=(self.size,) or not np.isfinite(value).all():
            raise ValueError('Complete finite affine pose controls required')
        vectors=value.reshape(-1,3)*self.caps[:,None];local=self.local.copy()
        local_jac=np.zeros((len(local),4,4,self.size))
        for k,(node,v,cap,base,scale) in enumerate(zip(self.nodes,vectors,self.caps,self.rotations,self.scales)):
            rotation=base@Rotation.from_rotvec(v).as_matrix()
            if np.any(v):local[node,:3,:3]=rotation@scale
            jr=right_jacobian(v)
            for c in range(3):local_jac[node,:3,:3,3*k+c]=rotation@skew(jr[:,c]*cap)@scale
        world=self.source.copy();jac=np.zeros_like(local_jac);changed=bool(np.any(value))
        for node in self.order:
            if not self.affected[node]:continue
            parent=self.rig.parents[node]
            if parent<0:
                if changed:world[node]=local[node]
                jac[node]=local_jac[node]
            else:
                if changed:world[node]=world[parent]@local[node]
                jac[node]=np.einsum('ijc,jk->ikc',jac[parent],local[node])+np.einsum('ij,jkc->ikc',world[parent],local_jac[node])
        skin=self.skin
        components=np.einsum('vkij,vkj->vki',world[skin.nodes,:3,:],skin.points)
        vertices=np.einsum('vki,vk->vi',components,skin.weights)
        derivative=np.empty((len(vertices),3,self.size))
        # Bound temporary gathers without discarding any vertex or influence.
        for start in range(0,len(vertices),512):
            ids=slice(start,start+512)
            derivative[ids]=np.einsum('vkijc,vkj,vk->vic',jac[skin.nodes[ids],:3,:,:],skin.points[ids],skin.weights[ids],optimize=True)
        joint_jac=jac[np.asarray(self.rig.joints),:3,3,:]
        return world,vertices,derivative,joint_jac


def rotation_fractions(before_actor,after_actor,times,nodes,caps):
    """Actual sampled local quaternion edits, independent of affine scale."""
    result=[]
    for node,cap in zip(nodes,caps):
        rotations=[]
        for actor in (before_actor,after_actor):
            sampler=actor['sampler'];channel=next(c for c in sampler.channels if c[:2]==(node,'rotation'))
            rotations.append(Rotation.from_quat(np.array([sampler.value('rotation',*channel[2:],float(t)) for t in times])))
        angles=(rotations[0].inv()*rotations[1]).magnitude()
        result.append(float(np.rad2deg(angles).max())/cap)
    return result
