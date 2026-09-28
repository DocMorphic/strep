"""Localize an authored pose edit with a C2 envelope; does not enforce contacts."""
import numpy as np
from scipy.spatial.transform import Rotation
from rig_transition import localize,compose


def blend(world,parents,root,editable,frame,target,radius=15):
    world=np.asarray(world,float);target=np.asarray(target,float)
    if (world.ndim!=4 or world.shape[2:]!=(4,4) or target.shape!=world.shape[1:]
            or type(radius)is not int or radius<3 or type(frame)is not int
            or frame-radius<0 or frame+radius>=len(world)
            or not np.isfinite(world).all() or not np.isfinite(target).all()
            or len(parents)!=world.shape[1] or len(set(editable))!=len(editable)
            or any(type(n)is not int or not 0<=n<len(parents) for n in [root,*editable])):
        raise ValueError('Finite matching pose hierarchy and an interior edit window required')
    local=localize(world,parents);goal=localize(target[None],parents)[0]
    distance=np.abs(np.arange(len(world))-frame)
    u=np.clip(1-distance/(radius-1),0,1)
    weights=u**3*(10+u*(-15+6*u))
    for node in editable:
        delta=local[frame,node,:3,:3].T@goal[node,:3,:3]
        vector=Rotation.from_matrix(delta).as_rotvec()
        local[:,node,:3,:3]=local[:,node,:3,:3]@Rotation.from_rotvec(weights[:,None]*vector).as_matrix()
    shift=target[root,:3,3]-world[frame,root,:3,3]
    parent=parents[root]
    basis=np.tile(np.eye(3),(len(world),1,1)) if parent<0 else world[:,parent,:3,:3]
    local[:,root,:3,3]+=np.einsum('fji,fj->fi',basis,weights[:,None]*shift)
    result=compose(local,parents)
    result[weights==0]=world[weights==0]
    return result,weights
