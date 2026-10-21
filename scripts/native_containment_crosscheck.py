"""Fail-closed diagnostic of local signed distance, ray parity and winding.

Agreement does not certify a non-self-intersecting mesh or collision freedom.
Disagreement never silently replaces a saved signed-distance measurement.
"""
import numpy as np
import trimesh
from trimesh.ray.ray_triangle import RayMeshIntersector

METHOD = 'strep-containment-consensus-v2'

# Fixed, non-axis-aligned directions. Each is tested in BOTH directions;
# agreement is required across all six parities, never a majority vote.
RAY_DIRECTIONS = ((.4395064455,.617598629942,.652231566745),
                  (-.723,.413,.554),(.311,-.827,.469))


def _ray_consensus(intersector,points):
    counts=np.zeros((len(points),len(RAY_DIRECTIONS),2),dtype=np.int64)
    if not len(points):return np.zeros(0,dtype=bool),np.zeros(0,dtype=bool),counts
    origins=np.vstack((points,points))
    # One direction pair at a time keeps the existing 64-ray query bound.
    for column,direction in enumerate(RAY_DIRECTIONS):
        direction=np.asarray(direction,float);direction/=np.linalg.norm(direction)
        directions=np.tile(direction,(len(points),1))
        _,indices,_=intersector.intersects_location(origins,np.vstack((directions,-directions)),multiple_hits=True)
        counts[:,column,:]=np.bincount(indices,minlength=2*len(points)).reshape(2,-1).T
    parity=counts%2==1
    resolved=np.all(parity==parity[:,0,0,None,None],axis=(1,2))
    return resolved & parity[:,0,0],resolved,counts


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
    if np.any(mesh.area_faces<=surface_tolerance_m**2/2):
        raise ValueError('Nondegenerate target triangles required for containment')
    closest,distance,triangle=trimesh.proximity.closest_point(mesh,points)
    # Bind only this mesh's ray intersector. The nearest-normal calculation
    # stays unchanged; its off-triangle ray branch must also be deterministic.
    # False is a placeholder for unresolved rays, NOT an outside decision:
    # the independently retained resolved mask gates every final state below.
    mesh.ray=RayMeshIntersector(mesh)
    mesh.ray.contains_points=lambda values:_ray_consensus(mesh.ray,values)[0]
    ray,ray_resolved,ray_counts=_ray_consensus(mesh.ray,points)
    signed=trimesh.proximity.signed_distance(mesh,points)
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
    for d,s,r,w,resolved in zip(distance,signed,ray,winding,ray_resolved):
        if d<=surface_tolerance_m:state='near-surface'
        elif not resolved:state='unresolved'
        elif s>surface_tolerance_m and r and abs(w-1)<=winding_tolerance:state='inside'
        elif s< -surface_tolerance_m and not r and abs(w)<=winding_tolerance:state='outside'
        else:state='unresolved'
        states.append(state)
    return dict(states=states,unsigned_distance_m=distance,signed_distance_m=signed,ray_inside=ray,winding=winding,
        ray_resolved=ray_resolved,ray_hit_counts=ray_counts,
        nearest_points_m=closest,nearest_triangles=triangle,all_resolved=all(s in ('inside','outside') for s in states),
        complete_query_points=len(points),complete_target_faces=len(faces),surface_tolerance_m=surface_tolerance_m,
        winding_tolerance=winding_tolerance,self_intersection_checked=False,collision_free_certified=False,quality_approved=False,
        scope='Agreement of nearest-normal/fixed-ray signed distance, six fixed ray parities and winding only. Any ray parity disagreement is unresolved; no random retry. Near-surface/disagreement is unresolved for acceptance; no complete source population, self-collision, exact arithmetic, motion, engine or quality certification.')


def penetration(source_vertices,target_vertices,target_faces,tolerance_m=.005,*,query_batch_size=32,
        surface_tolerance_m=1e-7):
    """Bounded native-scene query; never return a depth for unresolved points.

    Overlapping/nested shells have no inferred union semantics. Only winding
    zero/outside or one/inside agreeing with parity and signed distance resolve.
    Agreement remains a diagnostic, not proof of valid self geometry.
    """
    from convex_partner_surface import candidates
    if type(query_batch_size) is not int or not 1<=query_batch_size<=32:
        raise ValueError('Integer query batch size between 1 and 32 required')
    if type(tolerance_m) not in (int,float) or not np.isfinite(tolerance_m) or tolerance_m<=0:
        raise ValueError('Positive finite depth tolerance required')
    if (type(surface_tolerance_m) not in (int,float) or not np.isfinite(surface_tolerance_m)
            or not 1e-10<=surface_tolerance_m<=1e-3):
        raise ValueError('Explicit small surface tolerance required')
    source=np.asarray(source_vertices,dtype=float);target=np.asarray(target_vertices,dtype=float)
    # Keep the whole near-surface band, even when the policy tolerance is
    # larger than the broadphase's minimum numerical expansion.
    selected,broadphase=candidates(source,target,padding=max(1e-7,surface_tolerance_m))
    # Validate target and tolerance even when broadphase excludes every point.
    # A far point is a complete bounded validation query, not a sampled surface.
    probe=target.max(axis=0)+np.maximum(np.ptp(target,axis=0),1.)
    crosscheck(target,target_faces,probe[None],surface_tolerance_m=surface_tolerance_m)
    result=dict(available=True,containment_method=METHOD,vertices_checked=len(source),
        broadphase_candidates=broadphase['aabb_candidates'],convex_broadphase=broadphase,
        queried_vertices=len(selected),unresolved_vertices=[],self_intersection_checked=False)
    maximum=0.;count=0;deepest=None
    for start in range(0,len(selected),query_batch_size):
        ids=selected[start:start+query_batch_size]
        checked=crosscheck(target,target_faces,source[ids],surface_tolerance_m=surface_tolerance_m)
        for offset,state in enumerate(checked['states']):
            vertex=int(ids[offset])
            if state not in ('inside','outside'):
                result['unresolved_vertices'].append(dict(vertex=vertex,state=state,
                    signed_distance_m=float(checked['signed_distance_m'][offset]),
                    unsigned_distance_m=float(checked['unsigned_distance_m'][offset]),
                    ray_inside=bool(checked['ray_inside'][offset]),ray_resolved=bool(checked['ray_resolved'][offset]),
                    ray_hit_counts=checked['ray_hit_counts'][offset].tolist(),winding=float(checked['winding'][offset])))
                continue
            depth=float(checked['signed_distance_m'][offset]) if state=='inside' else 0.
            count+=int(depth>tolerance_m)
            if depth>maximum:maximum=depth;deepest=vertex
    result['available']=not result['unresolved_vertices']
    if result['available']:
        result.update(max_depth_m=maximum,vertices_over_tolerance=count,deepest_vertex=deepest)
    return result
