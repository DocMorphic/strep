"""Explicit angular measurement for stored affine joint transforms.

Right-polar orientation is a metric definition, never an asset normalization.
Strict legacy measurement remains available unchanged. Stretch and reconstruction
receipts keep the distinction between measured orientation and stored geometry.
"""
import numpy as np
from sampled_motion_caps import features

MODES=('strict','right-polar-v1')


def extract(world,joints,mode):
    if mode not in MODES:
        raise ValueError('Explicit supported angular orientation metric required')
    payload=features(world,joints)
    if mode=='strict':
        return payload,dict(mode=mode,asset_transforms_modified=False),{}
    linear=payload['rotations']
    if (linear.ndim!=4 or linear.shape[-2:]!=(3,3) or not linear.size
            or not np.isfinite(linear).all() or not np.isfinite(payload['positions']).all()):
        raise ValueError('Finite nonempty affine joint transform population required')
    if np.any(np.linalg.det(linear)<=0):
        raise ValueError('Polar orientation requires positive nonsingular transforms; reflections unsupported')
    u,s,vt=np.linalg.svd(linear)
    if np.any(s[..., -1]<1e-12) or np.any(s[...,0]/s[...,-1]>1e8):
        raise ValueError('Polar orientation requires well-conditioned nonsingular transforms')
    rotation=u@vt
    stretch=vt.swapaxes(-1,-2)@(s[...,None]*vt)
    residual=np.linalg.norm(rotation@stretch-linear,axis=(-2,-1))/np.linalg.norm(linear,axis=(-2,-1))
    orthogonal=np.max(abs(rotation@rotation.swapaxes(-1,-2)-np.eye(3)))
    if residual.max()>1e-10 or orthogonal>1e-12 or np.max(abs(np.linalg.det(rotation)-1))>1e-12:
        raise ValueError('Polar reconstruction or proper-orientation verification failed')
    # Only the measurement payload gets a separate orientation array. Positions,
    # source matrices, rig nodes, inverse binds and exported geometry stay intact.
    payload=dict(positions=payload['positions'],rotations=rotation)
    summary=dict(mode=mode,samples=linear.shape[0],joints=linear.shape[1],
        maximum_relative_reconstruction_error=float(residual.max()),
        maximum_orthogonality_error=float(orthogonal),minimum_singular_value=float(s.min()),
        maximum_singular_value=float(s.max()),maximum_stretch_from_identity=float(abs(stretch-np.eye(3)).max()),
        asset_transforms_modified=False,scope='Right-polar orientation metric; original affine positions and geometry retained. Not a rig repair or release approval.')
    return payload,summary,dict(right_stretch=stretch,singular_values=s)
