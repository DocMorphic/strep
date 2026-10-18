"""Separate proposal step radii from immutable original control-vector balls."""
import numpy as np
from conic_pose_minimax import minimax_step


def group_trust_step(margins,jacobian,controls,group_radii,*,protected_rows=None,
                     affine_vectors=None,affine_jacobian=None,affine_radii=None,
                     maximum_bytes=64*1024**2,l1_penalty=1e-5):
    """Solve delta[g] = radius[g] * eta[g], with ||eta[g]|| <= 1.

    The original balls ||controls[g] + delta[g]|| <= 1 remain hard affine
    cones. A zero search radius freezes that group. Search radii never grant
    extra author permission. Acceptance still requires nonlinear observations.
    """
    x,j,m,r=[np.asarray(v) for v in (controls,jacobian,margins,group_radii)]
    if x.ndim!=1 or not 3<=len(x)<=384 or len(x)%3 or j.ndim!=2 or j.shape[1]!=len(x) or not 1<=len(j)<=8192 or m.shape!=(len(j),) or r.shape!=(len(x)//3,):
        raise ValueError('Complete rows, columns and one radius per original three-vector required')
    if any(v.dtype.kind not in 'fiu' or not np.isfinite(v).all() or np.any(abs(v)>1e6) for v in (x,j,m,r)) or np.any(r<0) or np.any(r>2) or np.any(np.linalg.norm(x.reshape(-1,3),axis=1)>1):
        raise ValueError('Finite real model, original control balls and search radii in [0,2] required')
    supplied=[v is not None for v in (affine_vectors,affine_jacobian,affine_radii)]
    if any(supplied) and not all(supplied):raise ValueError('Complete optional affine data required')
    v=np.empty((0,3));t=np.empty((0,3,len(x)));a=np.empty(0)
    if all(supplied):
        v,t,a=[np.asarray(z) for z in (affine_vectors,affine_jacobian,affine_radii)]
        if v.ndim!=2 or v.shape[1]!=3 or not 1<=len(v)<=8192-len(r) or t.shape!=(len(v),3,len(x)) or a.shape!=(len(v),):raise ValueError('Complete affine vectors and every original column required')
        if any(z.dtype.kind not in 'fiu' or not np.isfinite(z).all() or np.any(abs(z)>1e6) for z in (v,t,a)) or np.any(a<1e-12):raise ValueError('Finite bounded affine data and positive radii required')
    # Bound complete transformed allocations before constructing them. The
    # underlying solver applies its own full sparse-model allocation bound.
    allocated=(m.size+j.size+x.size+r.size+v.size+t.size+a.size+3*len(r)*len(x))*8*12
    if type(maximum_bytes) is not int or not 1<=maximum_bytes<=64*1024**2 or allocated>maximum_bytes:raise ValueError('Complete group-trust model budget exceeded; no truncation')
    x,j,m,r=[np.array(z,dtype=float,copy=True) for z in (x,j,m,r)]
    scale=np.repeat(r,3);author_transform=np.eye(len(x)).reshape(len(r),3,len(x))*scale
    vectors=np.r_[x.reshape(-1,3),v];transform=np.concatenate([author_transform,t*scale],axis=0);radii=np.r_[np.ones(len(r)),a]
    eta,report=minimax_step(m,j*scale,np.zeros(len(x)),trust=1.,protected_rows=protected_rows,
        affine_vectors=vectors,affine_jacobian=transform,affine_radii=radii,maximum_bytes=maximum_bytes,l1_penalty=l1_penalty)
    direction=None;author_excess=None;step_excess=None
    if eta is not None:
        proposed=eta*scale;author_excess=float(np.max(np.linalg.norm((x+proposed).reshape(-1,3),axis=1)-1))
        step_excess=float(np.max(np.linalg.norm(proposed.reshape(-1,3),axis=1)-r))
        if author_excess<=0 and step_excess<=0 and np.all(proposed[np.repeat(r==0,3)]==0):direction=proposed.copy()
    report.update(schema='strep-conic-group-trust-v1',usable_direction=direction is not None,group_search_radii=r.tolist(),
        original_author_control_balls=len(r),physical_affine_norm_constraints=len(v),
        maximum_original_control_norm_excess=author_excess,maximum_group_step_norm_excess=step_excess,
        source_budget_rebased=False,movement_penalty_coordinates='normalized group-search variables',
        scope='Complete supplied linear rows, original author control balls, separate group step balls and optional physical affine norms. Zero radius freezes a group. Nonlinear/saved-asset gates remain caller obligations; no physical tolerance added.')
    return direction,report
