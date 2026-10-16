"""Complete unique triangle-pair screening for sampled native self geometry.

Reports transverse crossings and ambiguous overlapping/contacting surfaces.
Shared vertices never suppress a proper crossing. This is not a solid-volume,
exact-arithmetic, continuous-time or collision-free certificate.
"""
from collections import Counter
import numpy as np
from rtree import index
from triangle_crossing import classify


def audit(vertices,faces,*,tolerance_m=1e-7,maximum_pairs=2000000,maximum_records=50000,progress=None):
    vertices=np.asarray(vertices);faces=np.asarray(faces)
    if (vertices.dtype.kind not in 'fiu' or vertices.ndim!=2 or vertices.shape[1:]!=(3,)
            or not 3<=len(vertices)<=250000 or not np.isfinite(vertices).all()
            or faces.dtype.kind not in 'iu' or faces.ndim!=2 or faces.shape[1:]!=(3,)
            or not 1<=len(faces)<=100000 or faces.min()<0 or faces.max()>=len(vertices)
            or type(tolerance_m) not in (int,float) or not np.isfinite(tolerance_m) or not 1e-10<=tolerance_m<=1e-4
            or type(maximum_pairs) is not int or not 1<=maximum_pairs<=10000000
            or type(maximum_records) is not int or not 1<=maximum_records<=100000):
        raise ValueError('Complete bounded finite mesh, tolerance and explicit pair/record budgets required')
    triangles=vertices[faces].astype(float);lo=triangles.min(axis=1);hi=triangles.max(axis=1)
    degenerate=np.flatnonzero(np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)<=tolerance_m**2)
    properties=index.Property();properties.dimension=3
    tree=index.Index(((i,(*low,*high),None) for i,(low,high) in enumerate(zip(lo,hi))),properties=properties)
    node_sets=[frozenset(face) for face in faces];counts=Counter();records=[];pairs=0;shared_counts=Counter()
    try:
        for i,triangle in enumerate(triangles):
            bounds=(*(lo[i]-tolerance_m),*(hi[i]+tolerance_m))
            for j in sorted(tree.intersection(bounds)):
                if j<=i:continue
                if pairs>=maximum_pairs:raise ValueError('Self-surface candidate-pair budget exhausted; no complete result')
                pairs+=1;value=classify(triangle,triangles[j],tolerance_m);kind=value['kind'];counts[kind]+=1
                shared=len(node_sets[i].intersection(node_sets[j]));shared_counts[str(shared)]+=1
                if (kind in ('proper_crossing','coplanar_or_near_parallel_overlap')
                        or kind=='boundary_or_near_contact' and shared==0):
                    if len(records)>=maximum_records:raise ValueError('Self-surface record budget exhausted; no complete result')
                    records.append(dict(left_triangle=i,right_triangle=int(j),shared_vertices=shared,**value))
            if progress and ((i+1)%1000==0 or i+1==len(triangles)):
                progress(dict(faces_completed=i+1,total_faces=len(triangles),candidate_pairs=pairs,records=len(records)))
    finally:tree.close()
    return dict(schema='strep-native-self-surface-v1',status='complete',vertices=len(vertices),triangles=len(faces),
        candidate_pairs=pairs,maximum_pairs=maximum_pairs,maximum_records=maximum_records,tolerance_m=tolerance_m,
        counts=dict(counts),shared_vertex_counts=dict(shared_counts),records=records,degenerate_faces=degenerate.tolist(),
        has_observed_transverse_crossings=bool(counts['proper_crossing']),
        has_ambiguous_surface_records=any(r['kind']!='proper_crossing' for r in records),
        complete_triangle_population=True,self_collision_free_certified=False,quality_approved=False,
        scope='All unique overlapping numerical triangle boxes, then unchanged triangle_crossing.classify. Shared topology is recorded, never used to hide transverse crossings. Ordinary shared-vertex boundaries are counted, not stored as defects. No solid containment, exact geometry, continuous motion, engine or quality certification.')
