"""Bounded complete selected-point skin map from a supplied world Jacobian.

Every supplied vertex and all eight influence slots are retained. This function
does not infer contact populations, source bindings or edit permissions.
"""
import numpy as np
from native_support_skin import NativeSupportSkin

MAXIMUM_BYTES=64*1024**2


def real(value):
    array=np.asarray(value)
    if array.dtype.kind not in 'fiu' or array.dtype.itemsize>8 or not np.isfinite(array).all():raise ValueError('Complete finite real arrays required')
    return array.astype(float,copy=True)


def skin_frame_map(skin,world,placement,ids,reduction,*,jacobian=None,maximum_jacobian_bytes=MAXIMUM_BYTES,maximum_working_bytes=MAXIMUM_BYTES):
    if not isinstance(skin,NativeSupportSkin) or type(reduction) is not str or reduction not in ('vertices','centroid'):
        raise ValueError('Complete native skin and explicit vertex/centroid reduction required')
    for budget in [maximum_jacobian_bytes,maximum_working_bytes]:
        if type(budget) is not int or not 1<=budget<=MAXIMUM_BYTES:raise ValueError('Explicit complete bounded storage budgets required')
    selected=np.asarray(ids);original=np.asarray(world)
    if (selected.ndim!=1 or not 1<=len(selected)<=65536 or selected.dtype.kind not in 'iu' or len(np.unique(selected))!=len(selected)
            or np.any(selected<0) or np.any(selected>=len(skin.nodes))
            or original.ndim!=3 or not 1<=len(original)<=4096 or original.shape[1:]!=(4,4)):
        raise ValueError('Complete distinct existing vertex IDs and all original hierarchy matrices required')
    world=real(original)
    if not np.array_equal(world[:,3,:],np.broadcast_to([0.,0.,0.,1.],world[:,3,:].shape)):raise ValueError('Affine homogeneous worlds required')
    if not isinstance(placement,(list,tuple)) or len(placement)!=2:raise ValueError('Explicit finite source placement required')
    position,rotation=map(real,placement)
    if position.shape!=(3,) or rotation.shape!=(3,3) or not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-10,rtol=0) or not np.isclose(np.linalg.det(rotation),1,atol=1e-10,rtol=0):
        raise ValueError('Proper original placement rotation required')
    nodes=np.asarray(skin.nodes)[selected];points=real(np.asarray(skin.points)[selected]);weights=real(np.asarray(skin.weights)[selected])
    if (nodes.dtype.kind not in 'iu' or nodes.ndim!=2 or not 1<=nodes.shape[1]<=8 or np.any(nodes<0) or np.any(nodes>=len(world))
            or points.shape!=nodes.shape+(4,) or weights.shape!=nodes.shape or np.any(weights<0)):
        raise ValueError('All finite native skin points/weights/existing influence nodes required')
    columns=0;matrix=None;output_rows=1 if reduction=='centroid' else len(selected)
    if jacobian is not None:
        raw=np.asarray(jacobian)
        if raw.ndim!=4 or raw.shape[:-1]!=world.shape or not 1<=raw.shape[-1]<=768 or raw.size*8>maximum_jacobian_bytes or output_rows*3*raw.shape[-1]*8>maximum_jacobian_bytes:
            raise ValueError('Complete world/input and point/output Jacobians exceed budget; no vertices/columns discarded')
        matrix=real(raw);columns=matrix.shape[-1]
        if np.any(matrix[:,3,:]):raise ValueError('Homogeneous world rows must have zero derivatives')
    per_vertex=nodes.shape[1]*3*4*8*(1+columns)
    batch=maximum_working_bytes//per_vertex
    if batch<1:raise ValueError('One complete vertex and all influence/derivative columns exceed working budget')
    values=np.empty((len(selected),3));derivative=np.zeros((output_rows,3,columns)) if columns else None
    for start in range(0,len(selected),batch):
        stop=min(start+batch,len(selected));index=slice(start,stop)
        values[index]=np.einsum('vkij,vkj,vk->vi',world[nodes[index],:3,:],points[index],weights[index])@rotation.T+position
        if columns:
            block=np.einsum('vkijc,vkj,vk->vic',matrix[nodes[index],:3,:,:],points[index],weights[index],optimize=True)
            block=np.einsum('ij,vjc->vic',rotation,block)
            if reduction=='centroid':derivative+=block.sum(axis=0,keepdims=True)/len(selected)
            else:derivative[index]=block
    if reduction=='centroid':values=values.mean(axis=0,keepdims=True)
    if not np.isfinite(values).all() or derivative is not None and not np.isfinite(derivative).all():raise ValueError('Nonfinite complete point map')
    return values,derivative,dict(schema='strep-native-skin-frame-map-v1',vertices=len(selected),influence_slots=nodes.shape[1],reduction=reduction,
        output_points=output_rows,derivative_columns=columns,working_batch_vertices=min(batch,len(selected)),output_jacobian_bytes=output_rows*3*columns*8,
        maximum_jacobian_bytes=maximum_jacobian_bytes,maximum_working_bytes=maximum_working_bytes,all_declared_vertices_and_influences_retained=True,
        quality_approved=False,release_approved=False,scope='Supplied selected native skin points and complete world derivatives only. Caller binds original source/placement/contacts and complete clocks. No target inference, collision, correction or motion selection.')
