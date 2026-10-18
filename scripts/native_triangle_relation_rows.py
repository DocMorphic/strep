"""Every original triangle vertex comparison in a shared fixed-normal context.

Only repeated occurrences of the same directed vertex relation are coalesced.
Their smallest original-arithmetic margin is retained. Original pair margins
remain separate and unchanged; nonlinear/saved/full-mesh checks stay mandatory.
"""
import hashlib
import numpy as np
from native_support_gap import triangle_support_gaps,MAXIMUM_PAIRS

MAXIMUM_BYTES=64*1024**2
MAXIMUM_COLUMNS=768


def triangle_relation_rows(left,right,left_triangles,right_triangles,normal,*,left_jacobian=None,right_jacobian=None,
                           minimum_gap_m=2e-5,length_scale_m=.01,maximum_array_bytes=MAXIMUM_BYTES):
    if type(maximum_array_bytes) is not int or not 1<=maximum_array_bytes<=MAXIMUM_BYTES:raise ValueError('Complete bounded array budget required')
    for value,low,high in [(minimum_gap_m,0.,.1),(length_scale_m,1e-6,1.)]:
        if type(value) not in (int,float) or not np.isfinite(value) or not low<=value<=high:raise ValueError('Original finite bounded gap and scale required')
    points=[np.asarray(v) for v in (left,right)];triangles=[np.asarray(v) for v in (left_triangles,right_triangles)];n=np.asarray(normal)
    if any(p.ndim!=2 or p.shape[1:]!=(3,) or not 1<=len(p)<=65536 for p in points):raise ValueError('Complete bounded point populations required')
    if (triangles[0].ndim!=2 or triangles[0].shape[1:]!=(3,) or not 1<=len(triangles[0])<=MAXIMUM_PAIRS or triangles[1].shape!=triangles[0].shape
            or any(t.dtype.kind not in 'iu' or np.any(t<0) or np.any(t>=len(p)) for t,p in zip(triangles,points)) or n.shape!=(3,)):
        raise ValueError('Every original paired triangle and existing vertex identity required')
    matrices=[None if j is None else np.asarray(j) for j in (left_jacobian,right_jacobian)];columns=0
    for j,p in zip(matrices,points):
        if j is None:continue
        if j.ndim!=3 or j.shape[:2]!=p.shape or not 1<=j.shape[-1]<=MAXIMUM_COLUMNS or columns and j.shape[-1]!=columns:
            raise ValueError('Complete identical shared derivative columns required')
        columns=j.shape[-1]
    input_bytes=8*(sum(p.size for p in points)+sum(t.size for t in triangles)+sum(j.size for j in matrices if j is not None)+3)
    if input_bytes>maximum_array_bytes:raise ValueError('Complete input exceeds budget; no truncation')
    for value in points+[n]+[j for j in matrices if j is not None]:
        if value.dtype.kind not in 'fiu' or value.dtype.itemsize>8 or not np.isfinite(value).all():raise ValueError('Complete finite real inputs required')
    points=[p.astype(float,copy=False) for p in points];n=n.astype(float,copy=False);matrices=[None if j is None else j.astype(float,copy=False) for j in matrices]
    triangles=[t.astype(np.int64,copy=False) for t in triangles];count=len(triangles[0])
    # Lexicographic directed relation IDs; every one of9P occurrences is mapped.
    left_ids=np.broadcast_to(triangles[0][:,:,None],(count,3,3));right_ids=np.broadcast_to(triangles[1][:,None,:],(count,3,3))
    keys=np.column_stack([left_ids.ravel(),right_ids.ravel()]);edges,inverse=np.unique(keys,axis=0,return_inverse=True);rows=len(edges)
    estimate=8*(256*count+6*sum(len(p) for p in points)+3*sum(j.size for j in matrices if j is not None)+2*rows*columns+6*min(rows,256)*columns+6*rows)
    if estimate>maximum_array_bytes:raise ValueError('Complete relation workspace/output budget exceeded; no rows or columns dropped')
    a=points[0][triangles[0]];b=points[1][triangles[1]];normals=np.tile(n,(count,1))
    legacy=triangle_support_gaps(a,b,normals);canonical=(legacy['projected_gap_m']-minimum_gap_m)/length_scale_m
    origin=a[:,:1,:];ap=np.einsum('pi,pvi->pv',normals,a-origin);bp=np.einsum('pi,pvi->pv',normals,b-origin)
    occurrence=(bp[:,None,:]-ap[:,:,None]-minimum_gap_m)/length_scale_m
    if not np.array_equal(np.min(occurrence,axis=(1,2)),canonical):raise ValueError('Original occurrence arithmetic differs from pair margins')
    margins=np.full(rows,np.inf);np.minimum.at(margins,inverse,occurrence.ravel())
    mapping=inverse.reshape(count,3,3);reconstructed=margins[mapping].min(axis=(1,2))
    if not np.all(reconstructed<=canonical):raise ValueError('Coalesced relations must not weaken any original pair')
    jacobian=None
    if columns:
        jacobian=np.empty((rows,columns))
        for first in range(0,rows,256):
            last=min(first+256,rows);block=np.zeros((last-first,columns))
            if matrices[0] is not None:block-=np.einsum('i,ric->rc',n,matrices[0][edges[first:last,0]])
            if matrices[1] is not None:block+=np.einsum('i,ric->rc',n,matrices[1][edges[first:last,1]])
            jacobian[first:last]=block/length_scale_m
    if not np.isfinite(margins).all() or jacobian is not None and not np.isfinite(jacobian).all():raise ValueError('Finite complete relation outputs required')
    digest=hashlib.sha256(triangles[0].astype('<i8').tobytes()+triangles[1].astype('<i8').tobytes()).hexdigest()
    return dict(margins=margins,jacobian=jacobian,edges=edges,occurrence_to_relation=mapping,canonical_pair_margins=canonical,
        report=dict(schema='strep-native-triangle-relation-rows-v1',original_pairs=count,comparison_occurrences=9*count,distinct_relations=rows,columns=columns,
            repeated_occurrences_coalesced=9*count-rows,original_topology_sha256=digest,all_occurrences_mapped=True,canonical_pair_arithmetic_unchanged=True,
            largest_conservative_reconstruction_difference=float(np.max(canonical-reconstructed)),estimated_array_bytes=estimate,maximum_array_bytes=maximum_array_bytes,
            normal_is_fixed=True,physical_margin_tolerance_added=0.,quality_approved=False,release_approved=False,
            scope='All directed vertex comparisons of supplied triangles at one fixed-normal/gap/time context. Duplicate anchors take the smallest original margin, never a weaker average. '
                  'Shared-column derivatives are local affine guidance; original nonlinear/saved pair and full-mesh checks remain required.'))
