"""Complete point/Jacobian pullback into a supplied moving rigid frame.

For row vectors local=(world-position)@rotation. Differentiation includes
point, frame translation AND frame rotation derivatives. No frame is fitted,
repaired, reorthogonalized or permission-approved here.
"""
import numpy as np

MAXIMUM_BYTES=64*1024**2


def _real(value,shape,label):
    a=np.asarray(value)
    if a.shape!=shape or a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all():raise ValueError('Complete finite real '+label+' required')
    return a.astype(float,copy=True)


def inverse_rigid_frame_points(points_world,position_world,rotation,*,points_jacobian=None,
                               position_jacobian=None,rotation_jacobian=None,
                               maximum_jacobian_bytes=MAXIMUM_BYTES,
                               maximum_working_bytes=MAXIMUM_BYTES):
    """All supplied points/columns; explicit zeros for every fixed side.

    Rotation maps frame-local coordinates into world coordinates. All three
    derivative arrays or none must be supplied. Rotation derivatives must be
    tangent to SO(3) at the supplied rotation, within a numerical check only.
    Array budgets exclude caller-owned assets and interpreter/process memory.
    """
    if not isinstance(points_world,np.ndarray) or points_world.ndim!=2 or points_world.shape[1]!=3 or not 1<=len(points_world)<=250000:raise ValueError('Explicit complete bounded (N,3) numpy point array required')
    count=len(points_world);columns=0
    for budget in [maximum_jacobian_bytes,maximum_working_bytes]:
        if type(budget) is not int or not 1<=budget<=MAXIMUM_BYTES:raise ValueError('Explicit complete bounded array budgets required')
    supplied=[j is not None for j in [points_jacobian,position_jacobian,rotation_jacobian]]
    if any(supplied) and not all(supplied):raise ValueError('All point/position/rotation Jacobians or none required')
    if all(supplied):
        if not isinstance(points_jacobian,np.ndarray) or points_jacobian.ndim!=3 or points_jacobian.shape[:2]!=(count,3) or not 1<=points_jacobian.shape[2]<=768:raise ValueError('Complete bounded point/xyz/column Jacobian required')
        columns=points_jacobian.shape[2]
        if not isinstance(position_jacobian,np.ndarray) or not isinstance(rotation_jacobian,np.ndarray) or position_jacobian.shape!=(3,columns) or rotation_jacobian.shape!=(3,3,columns):raise ValueError('Complete matching frame translation/rotation columns required')
    jacobian_bytes=8*count*3*columns;workspace=8*(18*count*columns+72*columns+12*count+12)
    if jacobian_bytes>maximum_jacobian_bytes or workspace>maximum_working_bytes:raise ValueError('Complete inverse-frame map exceeds array budget; no points or columns dropped')
    points=_real(points_world,(count,3),'world points');position=_real(position_world,(3,),'frame position');R=_real(rotation,(3,3),'frame rotation')
    if np.max(np.abs(points))>1e6 or np.max(np.abs(position))>1e6:raise ValueError('Represented positions within one million metres required')
    if np.max(np.abs(R.T@R-np.eye(3)))>1e-8 or abs(np.linalg.det(R)-1)>1e-8:raise ValueError('Proper rigid frame rotation required; no scale/reflection or repair')
    delta=points-position;local=delta@R;jac=None
    if columns:
        jp=_real(points_jacobian,(count,3,columns),'world point Jacobian');jt=_real(position_jacobian,(3,columns),'frame position Jacobian');jr=_real(rotation_jacobian,(3,3,columns),'frame rotation Jacobian')
        tangent=np.einsum('ki,kjc->ijc',R,jr);error=np.max(np.abs(tangent+tangent.swapaxes(0,1)),axis=(0,1));limit=1e-7*(1+np.max(np.abs(jr),axis=(0,1)))
        if np.any(error>limit):raise ValueError('Frame rotation Jacobian must be tangent to the supplied rigid rotation')
        jac=np.einsum('vkc,kj->vjc',jp-jt[None,:,:],R)+np.einsum('vk,kjc->vjc',delta,jr)
    if not np.isfinite(local).all() or jac is not None and not np.isfinite(jac).all():raise ValueError('Finite complete inverse-frame output required')
    return local,jac,dict(schema='strep-native-inverse-rigid-frame-v1',points=count,columns=columns,jacobian_bytes=jacobian_bytes,estimated_array_workspace_bytes=workspace,all_points_and_columns_retained=True,point_translation_rotation_derivatives_included=bool(columns),frame_repaired=False,source_permissions_verified=False,collision_certified=False,quality_approved=False,release_approved=False,scope='Supplied proper rigid frame and complete point/position/rotation derivatives only. Caller binds sources, edit permissions and clocks; all original nonlinear saved-motion/full-mesh/contact/quality gates remain separate. No frame fitting or feasibility claim.')
