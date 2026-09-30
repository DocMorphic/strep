"""Reach a wrist waypoint with rigid bone lengths and retained hand orientation."""
import numpy as np
from scipy.spatial.transform import Rotation
from elbow_swivel import local_transforms,descendants,swivel
from paired_guarded_temporal import world_from_local


def align_vectors(a,b):
    a,b=np.asarray(a,float),np.asarray(b,float)
    if a.shape!=(3,) or b.shape!=(3,) or not np.isfinite([a,b]).all() or min(np.linalg.norm(a),np.linalg.norm(b))<1e-12:
        raise ValueError('Finite nonzero 3D directions required')
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    cross=np.cross(a,b);sine=np.linalg.norm(cross);cosine=float(np.clip(a@b,-1,1))
    if sine<1e-12:
        if cosine>0:return np.eye(3)
        cross=np.cross(a,np.eye(3)[np.argmin(np.abs(a))]);cross/=np.linalg.norm(cross)
        return Rotation.from_rotvec(cross*np.pi).as_matrix()
    return Rotation.from_rotvec(cross/sine*np.arctan2(sine,cosine)).as_matrix()


def reach(world,parents,upper,elbow,wrist,target,radians=0.):
    """Solve the elbow circle; transport its bend plane and apply a swivel.

    Targets outside the exact two-bone reach interval are rejected, not clamped.
    Native local translations and all other local transforms are retained.
    """
    world=np.asarray(world,float);local=local_transforms(world,parents)
    target=np.asarray(target,float)
    # Reuse the chain/angle checks and keep the identical zero-offset behavior.
    swivel(world,parents,upper,elbow,wrist,radians)
    if target.shape!=(3,) or not np.isfinite(target).all():raise ValueError('Finite wrist target required')
    shoulder,old_elbow,old_wrist=world[[upper,elbow,wrist],:3,3]
    if np.array_equal(target,old_wrist):return swivel(world,parents,upper,elbow,wrist,radians)
    upper_vector=old_elbow-shoulder;lower_vector=old_wrist-old_elbow
    length_a=np.linalg.norm(upper_vector);length_b=np.linalg.norm(lower_vector)
    axis=target-shoulder;distance=np.linalg.norm(axis)
    if min(length_a,length_b,distance)<1e-8:raise ValueError('Nondegenerate two-bone reach required')
    if not abs(length_a-length_b)-1e-10<=distance<=length_a+length_b+1e-10:
        raise ValueError('Wrist target outside two-bone reach')
    axis/=distance;old_axis=old_wrist-shoulder;old_axis/=np.linalg.norm(old_axis)
    bend=upper_vector-old_axis*(upper_vector@old_axis)
    if np.linalg.norm(bend)<1e-10:
        bend=np.cross(old_axis,np.eye(3)[np.argmin(np.abs(old_axis))])
    bend/=np.linalg.norm(bend)
    transported=Rotation.from_rotvec(axis*radians).as_matrix()@align_vectors(old_axis,axis)
    along=(length_a**2-length_b**2+distance**2)/(2*distance)
    radius=np.sqrt(max(0.,length_a**2-along**2))
    new_elbow=shoulder+axis*along+transported@bend*radius
    upper_rotation=align_vectors(transported@upper_vector,new_elbow-shoulder)@transported@world[upper,:3,:3]
    elbow_rotation=align_vectors(transported@lower_vector,target-new_elbow)@transported@world[elbow,:3,:3]
    parent=parents[upper]
    local[upper,:3,:3]=(world[parent,:3,:3].T if parent>=0 else np.eye(3))@upper_rotation
    local[elbow,:3,:3]=upper_rotation.T@elbow_rotation
    local[wrist,:3,:3]=elbow_rotation.T@world[wrist,:3,:3]
    result=world_from_local(local[None],parents)[0]
    hand=descendants(parents,wrist);expected=world[hand].copy();expected[:,:3,3]+=target-old_wrist
    np.testing.assert_allclose(result[hand],expected,atol=1e-9,rtol=0)
    np.testing.assert_allclose(result[elbow,:3,3],new_elbow,atol=1e-9,rtol=0)
    return result,local
