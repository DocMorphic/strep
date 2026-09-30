"""Rigid two-bone swivel poses that retain the complete wrist transform.

This is a kinematic planning primitive, not a joint-limit or naturalness model.
Only upper-arm and wrist local rotations change. Bone lengths stay fixed.
"""
import numpy as np
from scipy.spatial.transform import Rotation


def descendants(parents, root):
    parents = np.asarray(parents)
    if (parents.ndim != 1 or parents.dtype.kind not in 'iu' or
            np.any(parents < -1) or np.any(parents >= len(parents))):
        raise ValueError('Valid parent indices required')
    if type(root) not in [int, np.int64, np.int32] or not 0 <= root < len(parents):
        raise ValueError('Valid subtree root required')
    mask = np.zeros(len(parents), bool)
    for i in range(len(parents)):
        seen = set(); node = i
        while node >= 0:
            if node in seen: raise ValueError('Cyclic hierarchy')
            seen.add(node)
            if node == root: mask[i] = True
            node = int(parents[node])
    return mask


def local_transforms(world, parents):
    world = np.asarray(world, float); parents = np.asarray(parents)
    if world.shape != (len(parents),4,4) or not np.isfinite(world).all():
        raise ValueError('Finite world matrices matching hierarchy required')
    descendants(parents, 0)
    rotations = world[:,:3,:3]
    if (not np.allclose(world[:,3,:], [0,0,0,1], atol=1e-9, rtol=0) or
            not np.allclose(rotations.transpose(0,2,1)@rotations,np.eye(3),atol=1e-7,rtol=0) or
            not np.allclose(np.linalg.det(rotations),1,atol=1e-7,rtol=0)):
        raise ValueError('Rigid proper transforms required; scale/shear unsupported')
    local = world.copy()
    for node,parent in enumerate(parents):
        if parent >= 0: local[node] = np.linalg.inv(world[parent])@world[node]
    return local


def swivel(world, parents, upper, elbow, wrist, radians):
    source = np.asarray(world,float); local = local_transforms(source,parents)
    if any(type(n) not in [int,np.int64,np.int32] or not 0 <= n < len(source) for n in [upper,elbow,wrist]):
        raise ValueError('Valid distinct arm nodes required')
    if len({upper,elbow,wrist}) != 3 or parents[elbow] != upper or parents[wrist] != elbow:
        raise ValueError('Direct upper-arm, elbow, wrist chain required')
    if not np.isfinite(radians) or abs(radians) > np.pi: raise ValueError('Finite swivel within +/- pi required')
    shoulder, end = source[[upper,wrist],:3,3]; axis = end-shoulder
    if np.linalg.norm(axis) < 1e-8: raise ValueError('Shoulder and wrist coincide')
    if radians == 0: return source.copy(), local
    rotation = Rotation.from_rotvec(axis/np.linalg.norm(axis)*radians).as_matrix()
    moving = descendants(parents,upper) & ~descendants(parents,wrist)
    result = source.copy()
    result[moving,:3,:3] = rotation@source[moving,:3,:3]
    result[moving,:3,3] = (source[moving,:3,3]-shoulder)@rotation.T+shoulder
    changed = local_transforms(result,parents)
    frozen = np.ones(len(source),bool); frozen[[upper,wrist]] = False
    np.testing.assert_allclose(changed[frozen],local[frozen],atol=1e-10,rtol=0)
    np.testing.assert_allclose(changed[:,:3,3],local[:,:3,3],atol=1e-10,rtol=0)
    # Use the original local translations and frozen transforms exactly. This
    # is what a native exporter must serialize, not a world-position override.
    local[upper,:3,:3] = changed[upper,:3,:3]
    local[wrist,:3,:3] = changed[wrist,:3,:3]
    return result, local


def segment_distance(a,b,c,d):
    """Exact finite-segment closest distance via interior and edge candidates."""
    points = np.asarray([a,b,c,d],float)
    if points.shape != (4,3) or not np.isfinite(points).all(): raise ValueError('Four finite 3D endpoints required')
    a,b,c,d = points; u=b-a; v=d-c; w=a-c
    uu=u@u; vv=v@v
    candidates=[]
    for s in [0.,1.]:
        t=np.clip(v@(w+s*u)/vv,0,1) if vv else 0.
        candidates.append(np.linalg.norm(w+s*u-t*v))
    for t in [0.,1.]:
        s=np.clip(u@(t*v-w)/uu,0,1) if uu else 0.
        candidates.append(np.linalg.norm(w+s*u-t*v))
    matrix=np.array([[uu,-u@v],[-u@v,vv]])
    if np.linalg.det(matrix) > 1e-14*uu*vv:
        s,t=np.linalg.solve(matrix,[-u@w,v@w])
        if 0 <= s <= 1 and 0 <= t <= 1: candidates.append(np.linalg.norm(w+s*u-t*v))
    return float(min(candidates))


def capsule_radius(points,a,b):
    points,a,b = np.asarray(points,float),np.asarray(a,float),np.asarray(b,float)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or a.shape != (3,) or b.shape != (3,):
        raise ValueError('Nonempty points and two endpoints required')
    if not all(np.isfinite(v).all() for v in [points,a,b]): raise ValueError('Finite capsule geometry required')
    axis=b-a; squared=axis@axis
    t=np.clip((points-a)@axis/squared,0,1) if squared else np.zeros(len(points))
    return float(np.linalg.norm(points-(a+t[:,None]*axis),axis=1).max())
