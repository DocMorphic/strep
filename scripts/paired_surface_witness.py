"""Local clearance planes whose source point and target triangle both move."""
import numpy as np


def moving_gap(points,triangles,barycentric,normals):
    points,triangles,barycentric,normals=map(lambda x:np.asarray(x,float),[points,triangles,barycentric,normals])
    n=len(points)
    if points.shape!=(n,3) or triangles.shape!=(n,3,3) or barycentric.shape!=(n,3) or normals.shape!=(n,3):
        raise ValueError('Matching source points, target triangles, barycentric weights and normals required')
    if not all(np.isfinite(x).all() for x in [points,triangles,barycentric,normals]):raise ValueError('Finite surface witnesses required')
    if np.any(barycentric<-1e-6) or np.any(barycentric>1+1e-6) or not np.allclose(barycentric.sum(1),1,atol=1e-8,rtol=0):
        raise ValueError('Barycentric weights must describe points on target triangles')
    if not np.allclose(np.linalg.norm(normals,axis=1),1,atol=1e-8,rtol=0):raise ValueError('Unit outward normals required')
    closest=np.einsum('ni,nij->nj',barycentric,triangles)
    return np.einsum('ni,ni->n',points-closest,normals)


def moving_gap_jacobian(source_derivative,target_derivative,barycentric,normals):
    source,target,bary,normals=map(lambda x:np.asarray(x,float),[source_derivative,target_derivative,barycentric,normals])
    n=len(source)
    if source.ndim!=3 or source.shape[:2]!=(n,3) or target.ndim!=4 or target.shape[:3]!=(n,3,3) or bary.shape!=(n,3) or normals.shape!=(n,3):
        raise ValueError('Separate source and target parameter Jacobians required')
    if not all(np.isfinite(x).all() for x in [source,target,bary,normals]):raise ValueError('Finite surface derivatives required')
    left=np.einsum('ni,nid->nd',normals,source)
    right=-np.einsum('ni,nj,njid->nd',normals,bary,target)
    return np.concatenate([left,right],axis=1)
