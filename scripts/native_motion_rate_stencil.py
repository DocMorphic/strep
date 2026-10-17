"""Complete original sampled-rate rows on bounded two/three-frame stencils.

Values use the existing Studio rate kernel. Positional derivatives are analytic;
angular derivatives differentiate its exact matrix-to-rotation decoder in bounded
column batches. Callers bind source caps, original clocks, joints and parameters.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from sampled_motion_caps import features,measures

METRICS=('linear_speed','linear_acceleration','angular_speed','angular_acceleration')
MAXIMUM_COLUMNS=768
MAXIMUM_JOINTS=256
MAXIMUM_JACOBIAN_BYTES=64*1024**2


def _array(value):
    array=np.asarray(value)
    if array.dtype.kind not in 'fiu' or array.dtype.itemsize>8 or not np.isfinite(array).all():
        raise ValueError('Finite real Float64-representable arrays required')
    return array.astype(float,copy=True)


def motion_rate_stencil(metric,world,caps,dt,*,jacobian=None,tolerance=1e-5,
                        angular_step=1e-6,maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
    if type(metric) is not str or metric not in METRICS:raise ValueError('Explicit original sampled-rate metric required')
    index=METRICS.index(metric);frames=3 if index in (1,3) else 2
    for value,low,high in [(dt,1e-6,1.),(tolerance,0.,1.),(angular_step,1e-8,1e-4)]:
        if type(value) not in (int,float) or not np.isfinite(value) or not low<=value<=high:
            raise ValueError('Finite bounded sample step, source tolerance and decoder difference step required')
    if type(maximum_jacobian_bytes) is not int or not 1<=maximum_jacobian_bytes<=MAXIMUM_JACOBIAN_BYTES:
        raise ValueError('Explicit complete bounded Jacobian budget required')
    original=np.asarray(world)
    if original.ndim!=4 or original.shape[0]!=frames or not 1<=original.shape[1]<=MAXIMUM_JOINTS or original.shape[2:]!=(4,4):
        raise ValueError('Complete matching two/three-frame joint world stencil required')
    world=_array(original);caps=_array(caps);joints=world.shape[1]
    if caps.shape!=(joints,) or np.any(caps<0) or np.any(caps>1e9):raise ValueError('Complete original nonnegative per-joint rate caps required')
    if not np.array_equal(world[:,:,3,:],np.broadcast_to([0.,0.,0.,1.],world[:,:,3,:].shape)):
        raise ValueError('Complete affine homogeneous world matrices required')
    payload=features(world,list(range(joints)));rates=measures(payload,dt)
    values=(rates[index][0]-caps-tolerance)/np.maximum(caps,.001)
    columns=0;derivative=None
    if jacobian is not None:
        supplied=np.asarray(jacobian)
        if (supplied.ndim!=5 or supplied.shape[:-1]!=world.shape or not 1<=supplied.shape[-1]<=MAXIMUM_COLUMNS
                or supplied.size*8>maximum_jacobian_bytes or joints*supplied.shape[-1]*8>maximum_jacobian_bytes):
            raise ValueError('Complete matching finite world Jacobian and every column must fit the budget')
        derivative=_array(supplied);columns=derivative.shape[-1]
        if np.any(derivative[:,:,3,:]):raise ValueError('Homogeneous matrix rows must have zero derivatives')
        if index in (0,1):
            order=index+1;vectors=np.diff(payload['positions'],n=order,axis=0)[0]/dt**order
            vector_jac=np.diff(derivative[:,:,:3,3,:],n=order,axis=0)[0]/dt**order
        else:
            rotations=payload['rotations'];relative=rotations[1:]@rotations[:-1].transpose(0,1,3,2)
            vector=Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec().reshape(frames-1,joints,3)
            vectors=vector[0]/dt if index==2 else np.diff(vector,axis=0)[0]/dt**2
            vector_jac=np.empty((joints,3,columns))
            # Decoder perturbations are derivative probes, never exported poses.
            # Keep its actual projection behavior for near-orthogonal source rigs.
            for first in range(0,columns,16):
                last=min(first+16,columns);dr=derivative[:,:,:3,:3,first:last]
                drelative=(np.einsum('fjikc,fjlk->fjilc',dr[1:],rotations[:-1])
                           +np.einsum('fjik,fjlkc->fjilc',rotations[1:],dr[:-1]))
                sides=[]
                for sign in (1.,-1.):
                    matrix=relative[...,None]+sign*angular_step*drelative
                    decoded=Rotation.from_matrix(np.moveaxis(matrix,-1,-3).reshape(-1,3,3)).as_rotvec()
                    decoded=decoded.reshape(frames-1,joints,last-first,3).transpose(0,1,3,2)
                    if np.any(np.linalg.norm(decoded,axis=2)>=np.pi-1e-6):raise ValueError('Ambiguous perturbed angular branch')
                    sides.append(decoded)
                if np.any(np.linalg.norm(sides[0]-sides[1],axis=2)>=np.pi):raise ValueError('Decoder derivative probe crosses an angular branch')
                dvector=(sides[0]-sides[1])/(2*angular_step)
                vector_jac[:,:,first:last]=dvector[0]/dt if index==2 else np.diff(dvector,axis=0)[0]/dt**2
        norms=np.linalg.norm(vectors,axis=1);unit=np.divide(vectors,norms[:,None],out=np.zeros_like(vectors),where=norms[:,None]>0)
        derivative=np.einsum('ji,jic->jc',unit,vector_jac)/np.maximum(caps,.001)[:,None]
    if not np.isfinite(values).all() or derivative is not None and not np.isfinite(derivative).all():
        raise ValueError('Nonfinite complete rate rows or derivative')
    report=dict(schema='strep-native-motion-rate-stencil-v1',metric=metric,frames=frames,joints=joints,rows=joints,
                derivative_columns=columns,output_jacobian_bytes=joints*columns*8,maximum_jacobian_bytes=maximum_jacobian_bytes,
                tolerance=tolerance,angular_step=angular_step,zero_norm_derivative='zero symmetric subgradient; not a fixed-condition proof',
                derivative='analytic positions; central difference of the unchanged angular matrix decoder',
                original_scalar_sign='positive is a violation',quality_approved=False,release_approved=False,
                scope='Every supplied stencil joint and derivative column only; caller binds full original source caps/clock and row partition. No source rebasing, whole-clip coverage, optimization or motion approval.')
    return values,derivative,report
