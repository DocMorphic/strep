"""Coupled material-frame gaps and directions for independent or shared controls."""
import numpy as np
from native_surface_frame import constraints


def pair(left,right,limits,*,shared_controls=False,normal_sign=-1,tangent_sign=1):
    """Default contact intent: opposing normals and aligned tangents.

    Both material origins must meet the pair distance cap. Independent frames
    concatenate their control columns; two hands in one control basis explicitly
    request shared_controls. Geometry/anatomical/engine acceptance stays separate.
    """
    if (type(shared_controls) is not bool or any(type(v) is not int or v not in (-1,1) for v in (normal_sign,tangent_sign))):
        raise ValueError('Explicit control ownership and signed frame relationships required')
    widths=[]
    for frame in (left,right):
        p,n,t=[np.asarray(frame[k],float) for k in ('origin_m','normal_world','tangent_world')]
        if any(v.shape!=(3,) or not np.isfinite(v).all() for v in (p,n,t)) or abs(np.linalg.norm(n)-1)>1e-8 or abs(np.linalg.norm(t)-1)>1e-8 or abs(n@t)>1e-8:
            raise ValueError('Finite orthonormal material frames required')
        jac=[np.asarray(frame[k],float) for k in ('origin_jacobian','normal_jacobian','tangent_jacobian')]
        if (jac[0].ndim!=2 or jac[0].shape[0]!=3 or not 1<=jac[0].shape[1]<=96
                or any(v.shape!=jac[0].shape or not np.isfinite(v).all() for v in jac)):
            raise ValueError('Complete matching finite frame derivative columns required')
        widths.append(jac[0].shape[1])
    target=dict(position_m=np.asarray(right['origin_m']).tolist(),normal_world=(normal_sign*np.asarray(right['normal_world'])).tolist(),tangent_world=(tangent_sign*np.asarray(right['tangent_world'])).tolist())
    rows,left_jac=constraints(left,target,limits)
    right_jac=np.concatenate([-right['origin_jacobian'],-normal_sign*right['normal_jacobian'],-tangent_sign*right['tangent_jacobian']],axis=0)
    if shared_controls:
        if widths[0]!=widths[1]:raise ValueError('Shared frames require the same declared control basis width')
        jacobian=left_jac+right_jac
    else:jacobian=np.c_[left_jac,right_jac]
    return rows,jacobian
