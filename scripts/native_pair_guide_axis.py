"""Rank a complete finite triangle-derived support-axis family for a skin patch.

All patch vertex pairs remain in the soft objective. An axis is proposal
guidance only; it does not certify a whole mesh or a feasible motion edit.
"""
import numpy as np


def choose_axis(left, left_faces, right, right_faces, baseline_axis, *,
                clearance_m=.0001, scale_m=.03, maximum_axis_tests=8192):
    patches=[];faces=[];edges=[]
    for points,triangles in ((left,left_faces),(right,right_faces)):
        p,f=np.asarray(points),np.asarray(triangles)
        if (p.ndim!=2 or p.shape[1:]!=(3,) or not 3<=len(p)<=256 or p.dtype.kind not in 'fiu'
                or not np.isfinite(p).all() or f.ndim!=2 or f.shape[1:]!=(3,) or not 1<=len(f)<=4096
                or f.dtype.kind not in 'iu' or np.any(f<0) or np.any(f>=len(p))
                or np.any(np.diff(np.sort(f,axis=1),axis=1)==0)):
            raise ValueError('Complete finite patch vertices and explicit indexed triangles required')
        p=p.astype(float);f=f.astype(np.int64);patches.append(p);faces.append(f)
        edges.append(sorted({tuple(sorted((int(a),int(b)))) for t in f for a,b in zip(t,np.roll(t,-1))}))
    if len(patches[0])*len(patches[1])>4096:
        raise ValueError('Complete patch pair population exceeds 4096 rows')
    axis=np.asarray(baseline_axis)
    if (axis.shape!=(3,) or axis.dtype.kind not in 'fiu' or not np.isfinite(axis).all()
            or abs(np.linalg.norm(axis)-1.)>1e-12):
        raise ValueError('Explicit finite unit baseline axis required')
    for name,value,lo,hi in (('clearance',clearance_m,0.,.1),('scale',scale_m,1e-6,1.)):
        if type(value) not in (int,float) or not np.isfinite(value) or not lo<=value<=hi:
            raise ValueError('Bounded finite '+name+' required')
    requested=2*(1+len(faces[0])+len(faces[1])+len(edges[0])*len(edges[1]))
    if type(maximum_axis_tests) is not int or not 1<=maximum_axis_tests<=8192 or requested>maximum_axis_tests:
        raise ValueError('Complete finite axis family exceeds its declared budget; no prefix returned')
    normals=[]
    for p,f in zip(patches,faces):
        n=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
        if not np.isfinite(n).all() or np.any(np.linalg.norm(n,axis=1)==0):
            raise ValueError('Every explicit patch triangle must be nondegenerate')
        normals.append(n)
    a,b=patches;vectors=[axis.astype(float)];identities=[dict(kind='baseline')]
    for side,normals_for_side in enumerate(normals):
        for face,n in enumerate(normals_for_side):vectors.append(n);identities.append(dict(kind='face-normal',side=side,face=face))
    null_crosses=0
    for i,j in edges[0]:
        for k,l in edges[1]:
            n=np.cross(a[j]-a[i],b[l]-b[k])
            if not np.isfinite(n).all():raise ValueError('Finite complete edge-axis family required')
            if np.linalg.norm(n)==0:null_crosses+=1;continue
            vectors.append(n);identities.append(dict(kind='edge-cross',left_edge=[i,j],right_edge=[k,l]))
    tests=[];selected=None;best=None
    for vector,identity in zip(vectors,identities):
        normal=vector/np.linalg.norm(vector)
        for sign in (1,-1):
            candidate=normal*sign;gaps=((b@candidate)[None,:]-(a@candidate)[:,None]).ravel()
            negative=np.minimum((gaps-clearance_m)/scale_m,0.);loss=float(negative@negative);minimum=float(gaps.min())
            if not np.isfinite([loss,minimum]).all():raise ValueError('Finite complete axis scores required')
            score=(loss,-minimum);record=dict(identity=identity,sign=sign,axis_world=candidate.tolist(),
                squared_negative_part=loss,minimum_gap_m=minimum);tests.append(record)
            if best is None or score<best:best=score;selected=len(tests)-1
    assert len(tests)==requested-2*null_crosses
    baseline=tests[0];choice=tests[selected]
    return np.array(choice['axis_world']),dict(schema='strep-native-pair-guide-axis-v1',
        ranking='Lowest complete squared negative pair deficit, then largest minimum pair gap, first stable tie.',
        left_vertices=len(a),right_vertices=len(b),pair_rows=len(a)*len(b),clearance_m=clearance_m,scale_m=scale_m,
        complete_requested_axis_tests=requested,exact_zero_edge_crosses_omitted=null_crosses,tests=tests,selected_index=selected,
        baseline_squared_negative_part=baseline['squared_negative_part'],selected_squared_negative_part=choice['squared_negative_part'],
        changed_direction=not np.array_equal(np.array(choice['axis_world']),np.array(baseline['axis_world'])),
        quality_approved=False,release_approved=False,
        scope='Both signs of baseline, every explicit face normal and every nonzero cross of unique indexed patch edges. '
              'Every selected vertex pair scored at the supplied pose; no prefix truncation, control-feasibility or geometry acceptance. '
              'A floating-point finite-family guide choice is not an optimal separating plane, collision certificate or human-quality result.')
