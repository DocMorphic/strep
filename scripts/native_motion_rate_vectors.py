"""Complete sampled rate vectors for local affine norm constraints.

Canonical scalar values retain the original Studio arithmetic. Vector/Jacobian
guidance keeps transverse components that a scalar norm tangent can lose.
Neither the affine vector model nor a cone solve certifies nonlinear motion.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from sampled_motion_caps import features,measures
from native_motion_rate_stencil import METRICS,MAXIMUM_COLUMNS,MAXIMUM_JOINTS,_array

MAXIMUM_JACOBIAN_BYTES=64*1024**2


def motion_rate_vectors(metric,world,caps,dt,*,jacobian=None,tolerance=1e-5,
                        angular_step=1e-6,maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
    """Return all physical vectors, their full Jacobian and original violations.

    Radii are the supplied physical caps plus their supplied source tolerance.
    Canonical scalar arithmetic remains authoritative at floating boundaries.
    Caller-owned original clocks, row identities, joints and permissions are
    never inferred from the supplied stencil.
    """
    if type(metric) is not str or metric not in METRICS:raise ValueError('Explicit original sampled-rate metric required')
    index=METRICS.index(metric);frames=3 if index in (1,3) else 2
    for value,low,high in [(dt,1e-6,1.),(tolerance,0.,1.),(angular_step,1e-8,1e-4)]:
        if type(value) not in (int,float) or not np.isfinite(value) or not low<=value<=high:
            raise ValueError('Finite bounded sample step, original source tolerance and decoder step required')
    if type(maximum_jacobian_bytes) is not int or not 1<=maximum_jacobian_bytes<=MAXIMUM_JACOBIAN_BYTES:
        raise ValueError('Explicit bounded complete Jacobian budget required')
    raw=np.asarray(world)
    if raw.ndim!=4 or raw.shape[0]!=frames or not 1<=raw.shape[1]<=MAXIMUM_JOINTS or raw.shape[2:]!=(4,4):
        raise ValueError('Complete matching two/three-frame joint world stencil required')
    world=_array(raw);caps=_array(caps);joints=world.shape[1]
    if caps.shape!=(joints,) or np.any(caps<0) or np.any(caps>1e9):raise ValueError('Complete original nonnegative per-joint caps required')
    if not np.array_equal(world[:,:,3,:],np.broadcast_to([0.,0.,0.,1.],world[:,:,3,:].shape)):
        raise ValueError('Affine homogeneous world matrices required')
    payload=features(world,list(range(joints)));canonical_rate=measures(payload,dt)[index][0]
    normalizers=np.maximum(caps,.001);values=(canonical_rate-caps-tolerance)/normalizers
    relative=None;rotvec=None
    if index in (0,1):vectors=np.diff(payload['positions'],n=index+1,axis=0)[0]/dt**(index+1)
    else:
        rotations=payload['rotations'];relative=rotations[1:]@rotations[:-1].transpose(0,1,3,2)
        rotvec=Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec().reshape(frames-1,joints,3)
        angular=rotvec/dt;vectors=angular[0] if index==2 else np.diff(angular,axis=0)[0]/dt
    norms=np.linalg.norm(vectors,axis=1)
    if norms.tobytes()!=canonical_rate.tobytes():raise ValueError('Vector norms must retain the canonical rate arithmetic exactly')
    matrix=None;columns=0;input_bytes=output_bytes=0
    if jacobian is not None:
        supplied=np.asarray(jacobian)
        if supplied.ndim!=5 or supplied.shape[:-1]!=world.shape or not 1<=supplied.shape[-1]<=MAXIMUM_COLUMNS:
            raise ValueError('Complete matching world Jacobian and every supplied column required')
        columns=supplied.shape[-1];input_bytes=supplied.size*8;output_bytes=joints*3*columns*8
        if input_bytes+output_bytes>maximum_jacobian_bytes:
            raise ValueError('Complete input plus vector Jacobian exceeds budget; no joints or columns dropped')
        derivative=_array(supplied)
        if np.any(derivative[:,:,3,:]):raise ValueError('Homogeneous matrix rows must have zero derivatives')
        if index in (0,1):matrix=np.diff(derivative[:,:,:3,3,:],n=index+1,axis=0)[0]/dt**(index+1)
        else:
            matrix=np.empty((joints,3,columns))
            for first in range(0,columns,16):
                last=min(first+16,columns);dr=derivative[:,:,:3,:3,first:last]
                drelative=(np.einsum('fjikc,fjlk->fjilc',dr[1:],rotations[:-1])
                           +np.einsum('fjik,fjlkc->fjilc',rotations[1:],dr[:-1]))
                sides=[]
                for sign in (1.,-1.):
                    perturbed=relative[...,None]+sign*angular_step*drelative
                    decoded=Rotation.from_matrix(np.moveaxis(perturbed,-1,-3).reshape(-1,3,3)).as_rotvec()
                    decoded=decoded.reshape(frames-1,joints,last-first,3).transpose(0,1,3,2)
                    if np.any(np.linalg.norm(decoded,axis=2)>=np.pi-1e-6):raise ValueError('Ambiguous perturbed angular branch')
                    sides.append(decoded)
                if np.any(np.linalg.norm(sides[0]-sides[1],axis=2)>=np.pi):raise ValueError('Decoder derivative probe crosses an angular branch')
                angular_jac=(sides[0]-sides[1])/(2*angular_step)/dt
                matrix[:,:,first:last]=angular_jac[0] if index==2 else np.diff(angular_jac,axis=0)[0]/dt
    radii=caps+tolerance
    if not all(np.isfinite(a).all() for a in [vectors,norms,radii,values]) or matrix is not None and not np.isfinite(matrix).all():
        raise ValueError('Nonfinite complete rate vectors or derivatives')
    return dict(vectors=vectors,jacobian=matrix,radii=radii,normalizers=normalizers,canonical_violations=values,
        report=dict(schema='strep-native-motion-rate-vectors-v1',metric=metric,frames=frames,joints=joints,rows=joints,
            units=('m/s','m/s^2','rad/s','rad/s^2')[index],derivative_columns=columns,input_jacobian_bytes=input_bytes,
            output_jacobian_bytes=output_bytes,maximum_jacobian_bytes=maximum_jacobian_bytes,tolerance=tolerance,angular_step=angular_step,
            canonical_vector_norms_byte_identical=True,all_joints_and_columns_retained=True,physical_margin_tolerance_added=0.,
            local_constraint='norm(v + J delta) <= original cap + original source tolerance',
            canonical_scalar_arithmetic_authoritative=True,quality_approved=False,release_approved=False,
            scope='Complete supplied sampled-rate vectors and every derivative column only. Angular derivatives differentiate the existing matrix decoder in bounded column batches, never exported perturbations. '
                  'Affine norm constraints retain vector curvature but do not certify nonlinear rotations, forward kinematics, Float32 files, whole-clip/continuous motion, geometry, engines or human acceptance.'))
