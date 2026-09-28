"""Conservative expanded-hull rejection for fitting correspondences.

The target mesh lies inside its hull. A point outside any hull plane expanded
by the contact margin cannot be within that margin of a target triangle.
Remaining points retain the original signed-distance query and 32-point cap.
"""
import numpy as np
import trimesh
from convex_partner_surface import candidates


def query(vertices, faces, margin=.002, stats=None):
    if not np.isfinite(margin) or margin < 0:
        raise ValueError('Finite nonnegative contact margin required')
    records=[];diagnostics=[]
    for source,target in [(0,1),(1,0)]:
        points=vertices[source];mesh=trimesh.Trimesh(vertices[target],faces,process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Closed wound target required')
        ids,broadphase=candidates(points,vertices[target],padding=max(1e-7,float(margin)))
        if stats is not None:stats.append(dict(source=source,target=target,**broadphase))
        active=[];max_depth=0.;over=0
        for start in range(0,len(ids),32):
            chunk=ids[start:start+32];signed=trimesh.proximity.signed_distance(mesh,points[chunk])
            if not np.isfinite(signed).all():raise ValueError('Nonfinite signed distance')
            max_depth=max(max_depth,float(np.maximum(signed,0).max()));over+=int((signed>.005).sum())
            near=signed>=-margin
            if not near.any():continue
            selected=chunk[near];distance=signed[near]
            closest,_,triangles=trimesh.proximity.closest_point(mesh,points[selected])
            delta=closest-points[selected];length=np.linalg.norm(delta,axis=1)
            normal=np.where((distance>=0)[:,None],1.,-1.)*delta/np.maximum(length[:,None],1e-12)
            normal[length<1e-8]=mesh.face_normals[triangles[length<1e-8]]
            bary=trimesh.triangles.points_to_barycentric(mesh.triangles[triangles],closest)
            if not np.isfinite(bary).all():raise ValueError('Degenerate contact triangle')
            active.extend(zip(selected.tolist(),np.asarray(faces)[triangles].tolist(),bary.tolist(),normal.tolist()))
        records.append(dict(source=source,target=target,points=active))
        diagnostics.append(dict(source=source,target=target,vertices_checked=len(points),max_depth_m=max_depth,vertices_over_5mm=over,active_constraints=len(active)))
    return records,diagnostics


def correspondences(actors,frame,x,faces,margin=.002,stats=None):
    sizes=[a.dim for a in actors];parts=np.split(x,[sizes[0]])
    vertices=[a.rig.vertices(a.pose(frame,v))@a.rotation.T+a.translation for a,v in zip(actors,parts)]
    return query(vertices,faces,margin,stats)
