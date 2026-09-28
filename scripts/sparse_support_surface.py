"""Exact skin Jacobian, skipping provably zero joint/vertex influences.

No geometry is dropped from the floor or contact objective. Only derivative
entries with zero weighted descendants are skipped. Skin and rig are fixed
for the fitter lifetime, as in the reference implementation.
"""
import numpy as np
from rig_clearance_fit import right_jacobian
from support_reference_fit import SupportReferenceFitter


class SparseSurfaceKernel:
    def __init__(self, fitter):
        self.fitter=fitter
        self.parts=[]
        for nodes,points,weights in fitter.skin.parts:
            root_mass=np.sum(weights*fitter.descendants[fitter.spec['root_node']][nodes],axis=1)
            joints=[]
            for node in fitter.nodes:
                weighted=weights*fitter.descendants[node][nodes]
                ids=np.flatnonzero(np.any(weighted != 0,axis=1))
                joints.append((ids,weighted[ids]))
            self.parts.append((nodes,points,weights,root_mass,joints))

    def evaluate(self, frame, values):
        fitter=self.fitter
        world,_=fitter.pose(frame,values)
        axes=[world[node,:3,:3]@right_jacobian(v)
              for node,v in zip(fitter.nodes,values[3:].reshape(-1,3))]
        positions,rows=[],[]
        for nodes,points,weights,root_mass,joints in self.parts:
            components=np.einsum('vkij,vkj->vki',world[nodes,:3,:],points)
            positions.append(np.sum(components*weights[:,:,None],axis=1))
            jac=np.zeros((len(nodes),3,len(values)))
            for axis in range(3):jac[:,axis,axis]=root_mass
            for j,(node,axis,(ids,weighted)) in enumerate(zip(fitter.nodes,axes,joints)):
                if not len(ids):continue
                delta=np.sum((components[ids]-world[node,:3,3])*weighted[:,:,None],axis=1)
                sl=slice(3+j*3,6+j*3)
                jac[ids,0,sl]=delta[:,2,None]*axis[1]-delta[:,1,None]*axis[2]
                jac[ids,1,sl]=delta[:,0,None]*axis[2]-delta[:,2,None]*axis[0]
                jac[ids,2,sl]=delta[:,1,None]*axis[0]-delta[:,0,None]*axis[1]
            rows.append(jac)
        return np.concatenate(positions),np.concatenate(rows)


class SparseSupportReferenceFitter(SupportReferenceFitter):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.sparse_surface=SparseSurfaceKernel(self)

    def surface_jacobian(self,frame,values):
        return self.sparse_surface.evaluate(frame,values)
