"""Conservative hull rejection before the existing bounded skin-depth query.

Every target triangle lies within the convex hull of its vertices. Points
strictly outside an expanded hull cannot penetrate that triangle mesh. This
only reduces query work; retained points use the same signed distance and the
same 32-point batch bound. It does not turn a vertex test into a certificate.
"""
import numpy as np
import trimesh
from scipy.spatial import ConvexHull, QhullError


def candidates(source, target, padding=1e-7):
    source=np.asarray(source,dtype=float);target=np.asarray(target,dtype=float)
    if source.ndim!=2 or target.ndim!=2 or source.shape[1:]!=(3,) or target.shape[1:]!=(3,):
        raise ValueError('Expected vertex arrays with shape N by 3')
    if not len(target) or not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError('Finite source and nonempty finite target required')
    if not np.isfinite(padding) or padding<1e-7:raise ValueError('Conservative padding must be at least 1e-7 m')
    ids=np.flatnonzero(np.all((source>=target.min(0)-padding)&(source<=target.max(0)+padding),axis=1))
    count=len(ids)
    if not count:return ids,dict(aabb_candidates=0,hull_candidates=0,hull_fallback=False)
    try:hull=ConvexHull(target)
    except QhullError:return ids,dict(aabb_candidates=count,hull_candidates=count,hull_fallback=True)
    normals=hull.equations[:,:3];offset=hull.equations[:,3]
    # Expand each numerical plane enough to include every original vertex.
    # Bounded chunks avoid an unbounded vertices-by-facets allocation.
    excess=np.zeros(len(normals))
    for start in range(0,len(target),128):
        excess=np.maximum(excess,(target[start:start+128]@normals.T+offset).max(axis=0))
    ceiling=excess+padding;keep=[]
    for start in range(0,len(ids),128):
        part=ids[start:start+128]
        keep.extend(part[np.all(source[part]@normals.T+offset<=ceiling,axis=1)].tolist())
    retained=np.asarray(keep,dtype=int)
    return retained,dict(aabb_candidates=count,hull_candidates=len(retained),hull_fallback=False)


def penetration(source_vertices,target_vertices,target_faces,tolerance_m=.005):
    source=np.asarray(source_vertices,dtype=float);target=np.asarray(target_vertices,dtype=float)
    if not np.isfinite(tolerance_m) or tolerance_m<=0:raise ValueError('Positive finite tolerance required')
    selected,broadphase=candidates(source,target)
    mesh=trimesh.Trimesh(target,target_faces,process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Closed wound target required')
    result=dict(vertices_checked=len(source),broadphase_candidates=broadphase['aabb_candidates'],
                convex_broadphase=broadphase,max_depth_m=0.,vertices_over_tolerance=0,deepest_vertex=None)
    for start in range(0,len(selected),32):
        chunk=selected[start:start+32]
        depths=np.maximum(0,trimesh.proximity.signed_distance(mesh,source[chunk]))
        if not np.isfinite(depths).all():raise ValueError('Nonfinite signed distance')
        i=int(depths.argmax());value=float(depths[i]);result['vertices_over_tolerance']+=int((depths>tolerance_m).sum())
        if value>result['max_depth_m']:result['max_depth_m']=value;result['deepest_vertex']=int(chunk[i])
    return result
