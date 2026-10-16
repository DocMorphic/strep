"""Fail-closed diagnostic of local signed distance, ray parity and winding.

Agreement does not certify a non-self-intersecting mesh or collision freedom.
Disagreement never silently replaces a saved signed-distance measurement.
"""
import numpy as np
import trimesh


def crosscheck(vertices,faces,points,*,surface_tolerance_m=1e-7,winding_tolerance=1e-5):
    vertices=np.asarray(vertices);faces=np.asarray(faces);points=np.asarray(points)
    if (vertices.dtype.kind not in 'fiu' or vertices.ndim!=2 or vertices.shape[1:]!=(3,)
            or not 4<=len(vertices)<=250000 or not np.isfinite(vertices).all()
            or faces.dtype.kind not in 'iu' or faces.ndim!=2 or faces.shape[1:]!=(3,)
            or not 4<=len(faces)<=100000 or faces.min()<0 or faces.max()>=len(vertices)
            or points.dtype.kind not in 'fiu' or points.ndim!=2 or points.shape[1:]!=(3,)
            or not 1<=len(points)<=32 or not np.isfinite(points).all()
            or type(surface_tolerance_m) not in (int,float) or not np.isfinite(surface_tolerance_m)
            or not 1e-10<=surface_tolerance_m<=1e-3 or type(winding_tolerance) not in (int,float)
            or not np.isfinite(winding_tolerance) or not 1e-10<=winding_tolerance<=1e-3):
        raise ValueError('Bounded complete finite mesh, 1-32 points and explicit small tolerances required')
    vertices=vertices.astype(float);points=points.astype(float)
    mesh=trimesh.Trimesh(vertices,faces,process=False)
    if not mesh.is_volume:raise ValueError('Closed consistently wound positive-volume topology required; self intersections remain unchecked')
    closest,distance,triangle=trimesh.proximity.closest_point(mesh,points)
    signed=trimesh.proximity.signed_distance(mesh,points);ray=mesh.contains(points)
    winding=np.zeros(len(points));compensation=np.zeros(len(points))
    # Stream complete faces per point. No point/face population is sampled away.
    for point_id,point in enumerate(points):
        for start in range(0,len(faces),2048):
            v=vertices[faces[start:start+2048]]-point;length=np.linalg.norm(v,axis=2)
            numerator=np.einsum('fi,fi->f',v[:,0],np.cross(v[:,1],v[:,2]))
            denominator=(length.prod(axis=1)+np.einsum('fi,fi->f',v[:,0],v[:,1])*length[:,2]
                +np.einsum('fi,fi->f',v[:,1],v[:,2])*length[:,0]+np.einsum('fi,fi->f',v[:,2],v[:,0])*length[:,1])
            increment=float(np.arctan2(numerator,denominator).sum()/(2*np.pi))-compensation[point_id]
            total=winding[point_id]+increment;compensation[point_id]=(total-winding[point_id])-increment;winding[point_id]=total
    if not all(np.isfinite(v).all() for v in (closest,distance,signed,winding)):
        raise ValueError('Nonfinite containment observation')
    states=[]
    for d,s,r,w in zip(distance,signed,ray,winding):
        if d<=surface_tolerance_m:state='near-surface'
        elif s>surface_tolerance_m and r and abs(w-1)<=winding_tolerance:state='inside'
        elif s< -surface_tolerance_m and not r and abs(w)<=winding_tolerance:state='outside'
        else:state='unresolved'
        states.append(state)
    return dict(states=states,unsigned_distance_m=distance,signed_distance_m=signed,ray_inside=ray,winding=winding,
        nearest_points_m=closest,nearest_triangles=triangle,all_resolved=all(s in ('inside','outside') for s in states),
        complete_query_points=len(points),complete_target_faces=len(faces),surface_tolerance_m=surface_tolerance_m,
        winding_tolerance=winding_tolerance,self_intersection_checked=False,collision_free_certified=False,quality_approved=False,
        scope='Agreement of three floating-point diagnostics only. Near-surface/disagreement is unresolved for acceptance; no complete source population, self-collision, exact arithmetic, motion, engine or quality certification.')
