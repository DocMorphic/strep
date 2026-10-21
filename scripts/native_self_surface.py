"""Complete unique triangle-pair screening for sampled native self geometry.

Reports transverse crossings and ambiguous overlapping/contacting surfaces.
Shared vertices never suppress a proper crossing. This is not a solid-volume,
exact-arithmetic, continuous-time or collision-free certificate.
"""
from collections import Counter
import hashlib
import numpy as np
from rtree import index
from triangle_crossing import classify

METHOD = 'strep-native-self-surface-screen-v2'


def _shared_boundary_filter(left,right,shared,tolerance):
    """Numerical fast path for nonparallel shared-vertex boundaries only.

    A shared point belongs to both plane intervals. If neither early separation
    nor two-sided straddling can occur, the scalar predicate reports boundary.
    Large roundoff estimates, ill-conditioned faces and threshold cases fall
    back. This is a floating-point filter, not an exact arithmetic certificate.
    Every potentially stored defect still uses the scalar predicate unchanged.
    """
    with np.errstate(over='ignore',invalid='ignore',divide='ignore',under='ignore'):
        a=left-left[:,0,None,:];b=right-left[:,0,None,:]
        na=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);nb=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
        la=np.linalg.norm(na,axis=1);lb=np.linalg.norm(nb,axis=1)
        scale=np.maximum(np.abs(a).max(axis=(1,2)),np.abs(b).max(axis=(1,2)))
        area=np.minimum(la,lb)
        normal_error=4096*np.finfo(float).eps*scale**2/area
        distance_error=normal_error*scale
        na=na/la[:,None];nb=nb/lb[:,None]
        da=np.einsum('nvi,ni->nv',a-b[:,0,None,:],nb)
        db=np.einsum('nvi,ni->nv',b-a[:,0,None,:],na)
        angle=np.linalg.norm(np.cross(na,nb),axis=1)
        # Prove that the shared coordinate will be included in both scalar
        # intervals with room for numerical differences in dot/norm evaluation.
        equal=np.all(a[:,:,None,:]==b[:,None,:,:],axis=3)
        shared_in_band=np.any(equal & (np.abs(da)[:,:,None]<tolerance-distance_error[:,None,None])
            & (np.abs(db)[:,None,:]<tolerance-distance_error[:,None,None]),axis=(1,2))
        not_straddling=((da.min(1)>-tolerance+distance_error)|(da.max(1)<tolerance-distance_error)
            |(db.min(1)>-tolerance+distance_error)|(db.max(1)<tolerance-distance_error))
        interval_error=distance_error/angle
        finite=np.isfinite(np.column_stack([la,lb,normal_error,distance_error,angle,interval_error])).all(1)
        return (shared>0)&finite&(area>tolerance**2+normal_error*scale**2)&(normal_error<1e-6)\
            &(angle>1e-10+normal_error*8)&(distance_error<tolerance/16)\
            &(interval_error<tolerance/16)&shared_in_band&not_straddling


def audit(vertices,faces,*,tolerance_m=1e-7,maximum_pairs=2000000,maximum_records=50000,progress=None,
        accelerate=True,pair_batch_size=512):
    vertices=np.asarray(vertices);faces=np.asarray(faces)
    if (vertices.dtype.kind not in 'fiu' or vertices.ndim!=2 or vertices.shape[1:]!=(3,)
            or not 3<=len(vertices)<=250000 or not np.isfinite(vertices).all()
            or faces.dtype.kind not in 'iu' or faces.ndim!=2 or faces.shape[1:]!=(3,)
            or not 1<=len(faces)<=100000 or faces.min()<0 or faces.max()>=len(vertices)
            or type(tolerance_m) not in (int,float) or not np.isfinite(tolerance_m) or not 1e-10<=tolerance_m<=1e-4
            or type(maximum_pairs) is not int or not 1<=maximum_pairs<=10000000
            or type(maximum_records) is not int or not 1<=maximum_records<=100000
            or type(accelerate) is not bool or type(pair_batch_size) is not int or not 1<=pair_batch_size<=2048):
        raise ValueError('Complete bounded finite mesh, tolerance and explicit pair/record budgets required')
    triangles=vertices[faces].astype(float);lo=triangles.min(axis=1);hi=triangles.max(axis=1)
    degenerate=np.flatnonzero(np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)<=tolerance_m**2)
    properties=index.Property();properties.dimension=3
    tree=index.Index(((i,(*low,*high),None) for i,(low,high) in enumerate(zip(lo,hi))),properties=properties)
    node_sets=[frozenset(face) for face in faces];counts=Counter();records=[];pairs=0;shared_counts=Counter()
    pending=[];filtered=0
    def flush():
        nonlocal filtered
        if not pending:return
        ids=np.asarray(pending,dtype=np.int64)
        mask=(_shared_boundary_filter(triangles[ids[:,0]],triangles[ids[:,1]],ids[:,2],tolerance_m)
            if accelerate else np.zeros(len(ids),dtype=bool))
        for (i,j,shared),fast in zip(pending,mask):
            shared_counts[str(shared)]+=1
            if fast:
                counts['boundary_or_near_contact']+=1;filtered+=1;continue
            value=classify(triangles[i],triangles[j],tolerance_m);kind=value['kind'];counts[kind]+=1
            if (kind in ('proper_crossing','coplanar_or_near_parallel_overlap')
                    or kind=='boundary_or_near_contact' and shared==0):
                if len(records)>=maximum_records:raise ValueError('Self-surface record budget exhausted; no complete result')
                records.append(dict(left_triangle=i,right_triangle=j,shared_vertices=shared,**value))
        pending.clear()
    try:
        for i,triangle in enumerate(triangles):
            bounds=(*(lo[i]-tolerance_m),*(hi[i]+tolerance_m))
            for j in sorted(tree.intersection(bounds)):
                if j<=i:continue
                if pairs>=maximum_pairs:raise ValueError('Self-surface candidate-pair budget exhausted; no complete result')
                pairs+=1;pending.append((i,int(j),len(node_sets[i].intersection(node_sets[j]))))
                if len(pending)>=pair_batch_size:flush()
            if progress and ((i+1)%1000==0 or i+1==len(triangles)):
                flush()
                progress(dict(faces_completed=i+1,total_faces=len(triangles),candidate_pairs=pairs,records=len(records)))
        flush()
    finally:tree.close()
    return dict(schema='strep-native-self-surface-v1',status='complete',vertices=len(vertices),triangles=len(faces),
        method=METHOD,faces_sha256=hashlib.sha256(faces.astype('<i8').tobytes()).hexdigest(),
        boundary_filter=dict(enabled=accelerate,pair_batch_size=pair_batch_size,filtered_pairs=filtered,scalar_pairs=pairs-filtered),
        candidate_pairs=pairs,maximum_pairs=maximum_pairs,maximum_records=maximum_records,tolerance_m=tolerance_m,
        counts=dict(counts),shared_vertex_counts=dict(shared_counts),records=records,degenerate_faces=degenerate.tolist(),
        has_observed_transverse_crossings=bool(counts['proper_crossing']),
        has_ambiguous_surface_records=any(r['kind']!='proper_crossing' for r in records),
        complete_triangle_population=True,self_collision_free_certified=False,quality_approved=False,
        scope='All unique overlapping numerical triangle boxes. Bounded nonparallel shared-boundary filter; all possible defects and uncertain cases use unchanged triangle_crossing.classify. Shared topology never exempts possible crossings. No solid containment, exact geometry, continuous motion, engine or quality certification.')
