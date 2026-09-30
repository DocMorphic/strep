"""Conservative local distance rows to moving barycentric surface points.

For a penetrating point, distance to any point on the target mesh bounds its
nearest-surface depth from above. The affine kinematics still need independent
nonlinear export validation. Initially outside witnesses keep their gap rows.
"""
import numpy as np


def separation_rows(points, triangles, barycentric, source_jacobian, target_jacobian, source_actor):
    points, triangles, bary, source, target = map(lambda v:np.asarray(v,float),
        [points, triangles, barycentric, source_jacobian, target_jacobian])
    n = len(points)
    if points.shape != (n,3) or triangles.shape != (n,3,3) or bary.shape != (n,3) or source.ndim != 3 or source.shape[:2] != (n,3) or target.ndim != 4 or target.shape[:3] != (n,3,3):
        raise ValueError('Matching source and triangle vector rows required')
    if source_actor not in [0,1] or not all(np.isfinite(v).all() for v in [points,triangles,bary,source,target]):
        raise ValueError('Finite data and an explicit actor order required')
    if np.any(bary < -1e-6) or np.any(bary > 1+1e-6) or not np.allclose(bary.sum(1),1,atol=1e-8,rtol=0):
        raise ValueError('Barycentric point must lie on the target triangle')
    # Exact convex weights are needed for the distance upper-bound argument.
    # Extraction may have sub-ulp negative weights at a triangle edge.
    bary = np.maximum(bary,0)
    bary /= bary.sum(1)[:,None]
    vector = points-np.einsum('ni,nij->nj',bary,triangles)
    right = -np.einsum('ni,nijd->njd',bary,target)
    jacobian = np.concatenate([source,right] if source_actor==0 else [right,source],axis=2)
    return vector,jacobian


def penetrating_rows(vectors,jacobians,gaps,caps):
    vectors,jacobians,gaps,caps = map(lambda v:np.asarray(v,float),[vectors,jacobians,gaps,caps])
    if vectors.ndim!=2 or vectors.shape[1:]!=(3,) or jacobians.ndim!=3 or jacobians.shape[:2]!=vectors.shape or gaps.shape!=(len(vectors),) or caps.shape!=gaps.shape:
        raise ValueError('Matching surface constraint rows required')
    if not all(np.isfinite(v).all() for v in [vectors,jacobians,gaps,caps]) or np.any(caps<0):
        raise ValueError('Finite vectors and nonnegative caps required')
    ids=np.flatnonzero(gaps<0)
    return dict(vectors=vectors[ids],jacobians=jacobians[ids],radii=caps[ids],witness_indices=ids)
