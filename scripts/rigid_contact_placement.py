"""Bounded point/normal placement with an explicit, unrestricted axial twist.

This is a rigid surface diagnostic, not skeletal IK. The reference normal
avoids an antiparallel source/target singularity as finger shape changes.
"""
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from grasp_orientation import align_direction, unit
from support_contact_v8 import rodrigues


def placement_frame(reference_normal, desired_normal):
    reference, target = unit(reference_normal), unit(desired_normal)
    tangent = unit(np.cross(target, np.eye(3)[np.argmin(np.abs(target))]))
    return reference, target, np.c_[tangent, np.cross(target, tangent)], align_direction(reference, target)


def bounded(raw, limit):
    return limit*raw/torch.sqrt(1+torch.sum(raw*raw, dim=-1, keepdim=True))


def align_near(source, reference):
    """Differentiable alignment on the declared local normal chart."""
    cosine = source@reference
    if float(cosine.detach()) <= -.99:
        raise ValueError('Shape normal outside the local alignment chart')
    cross = torch.linalg.cross(source, reference); zero = cross[0]*0
    skew = torch.stack([zero,-cross[2],cross[1],cross[2],zero,-cross[0],-cross[1],cross[0],zero]).reshape(3,3)
    return torch.eye(3,dtype=source.dtype,device=source.device)+skew+skew@skew/(1+cosine)


def place(raw, offsets, normal, reference, target_normal, basis, base_alignment, target, point_limit, angle_limit):
    if raw.shape != (6,):raise ValueError('Six rigid placement coordinates required')
    rotation = (rodrigues((basis@bounded(raw[3:5],angle_limit))[None])[0]
                @rodrigues((target_normal*raw[5])[None])[0]
                @base_alignment@align_near(normal,reference))
    point = target+bounded(raw[:3],point_limit)
    return offsets@rotation.T+point, point, rotation


def replay(raw, offsets, normal, reference, target_normal, basis, base_alignment, target, point_limit, angle_limit):
    """Independent NumPy/SciPy replay, including shape-normal realignment."""
    raw=np.asarray(raw,dtype=float)
    if raw.shape!=(6,) or not np.isfinite(raw).all():raise ValueError('Finite placement coordinates required')
    delta=point_limit*raw[:3]/np.sqrt(1+raw[:3]@raw[:3])
    tilt=angle_limit*raw[3:5]/np.sqrt(1+raw[3:5]@raw[3:5])
    matrix=(Rotation.from_rotvec(basis@tilt).as_matrix()
            @Rotation.from_rotvec(target_normal*raw[5]).as_matrix()
            @base_alignment@align_direction(normal,reference))
    point=target+delta
    return offsets@matrix.T+point,point,matrix
