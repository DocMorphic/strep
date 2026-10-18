"""Complete fixed-direction triangle projection rows for coupled scene guidance.

Projection method: David Eberly, MethodOfSeparatingAxes, sections 2/5/9,
https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf
Independent implementation; no pseudocode copied. These floating rows are not
intersection predicates or certificates. Directions are frozen by the caller;
negative gaps do not prove collision or infeasibility. Full meshes stay separate.
"""
import numpy as np

MAXIMUM_PAIRS=4096
MAXIMUM_BYTES=64*1024**2


def _real(value,shape,label):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.dtype.itemsize>8 or raw.shape!=shape or not np.isfinite(raw).all():raise ValueError('Complete finite numeric '+label+' required')
    return raw.astype(float,copy=False)


def _triangles(left,right):
    raw=np.asarray(left)
    if raw.ndim!=3 or raw.shape[1:]!=(3,3) or not 1<=len(raw)<=MAXIMUM_PAIRS:raise ValueError('Complete bounded triangle pairs required')
    a=_real(raw,raw.shape,'left triangles');b=_real(right,raw.shape,'right triangles')
    if max(float(np.abs(a).max()),float(np.abs(b).max()))>1e6:raise ValueError('Finite represented world positions within one million metres required')
    return a,b


def choose_directions(left,right,*,minimum_axis_norm=1e-12):
    """Choose one oriented candidate projection direction per source pair.

    Candidate axes include world axes, face normals, cross-edge axes, and
    face-normal/edge cross products for coplanar triangles. The largest signed
    gap is only a proposal direction; no floating completeness claim follows.
    This selection is NOT differentiated. Freeze its output for projection_rows.
    """
    a,b=_triangles(left,right)
    if type(minimum_axis_norm) not in (int,float) or not np.isfinite(minimum_axis_norm) or not 1e-16<=minimum_axis_norm<=1e-6:raise ValueError('Bounded positive candidate-axis threshold required')
    normals=[];gaps=[];counts=[]
    for x,y in zip(a,b):
        e=np.roll(x,-1,axis=0)-x;f=np.roll(y,-1,axis=0)-y;u=np.cross(e[0],e[1]);v=np.cross(f[0],f[1])
        axes=np.vstack([np.eye(3),u,v,np.cross(e[:,None,:],f[None,:,:]).reshape(-1,3),np.cross(u,np.vstack([e,f])),np.cross(v,np.vstack([e,f]))])
        lengths=np.linalg.norm(axes,axis=1);axes=axes[lengths>minimum_axis_norm]/lengths[lengths>minimum_axis_norm,None]
        # A common origin reduces cancellation; every vertex is retained.
        px=(x-x[0])@axes.T;py=(y-x[0])@axes.T
        forward=py.min(axis=0)-px.max(axis=0);reverse=px.min(axis=0)-py.max(axis=0);values=np.r_[forward,reverse];index=int(values.argmax());sign=1 if index<len(axes) else -1
        normals.append(sign*axes[index%len(axes)]);gaps.append(values[index]);counts.append(len(axes))
    return np.asarray(normals),dict(projected_gap_m=np.asarray(gaps),candidate_axis_counts=counts,directions_frozen_for_derivatives=True,collision_certified=False,quality_approved=False,release_approved=False)


def projection_rows(left,right,normals,*,left_jacobian=None,right_jacobian=None,minimum_gap_m=0.,length_scale_m=.01,maximum_jacobian_bytes=MAXIMUM_BYTES,maximum_working_bytes=MAXIMUM_BYTES):
    """Nine signed rows per pair: n dot (right[j]-left[i]) - minimum_gap.

    Order: source pair, left vertex, right vertex. All 3x3 vertex combinations
    and every supplied derivative column remain. Both derivative sides are
    required together, including explicit zeros for a fixed side. Positive rows
    imply separation along the supplied direction in real arithmetic only.
    """
    a,b=_triangles(left,right);pairs=len(a);n=_real(normals,(pairs,3),'fixed unit directions')
    if np.any(np.abs(n)>2) or np.any(np.abs(np.linalg.norm(n,axis=1)-1)>1e-8):raise ValueError('One fixed unit direction per complete pair required')
    for value,lo,hi in [(minimum_gap_m,0.,.1),(length_scale_m,1e-9,1.)]:
        if type(value) not in (int,float) or not np.isfinite(value) or not lo<=value<=hi:raise ValueError('Finite physical gap and positive bounded row scale required')
    for budget in [maximum_jacobian_bytes,maximum_working_bytes]:
        if type(budget) is not int or not 1<=budget<=MAXIMUM_BYTES:raise ValueError('Explicit complete bounded array budgets required')
    if (left_jacobian is None)!=(right_jacobian is None):raise ValueError('Both complete side Jacobians or neither required')
    columns=0;ja=jb=None
    if left_jacobian is not None:
        raw=np.asarray(left_jacobian)
        if raw.ndim!=4 or raw.shape[:3]!=a.shape or not 1<=raw.shape[3]<=768:raise ValueError('Complete triangle/xyz/column Jacobian required')
        columns=raw.shape[3];required=pairs*9*columns*8;workspace=8*(pairs*(18*columns+9*columns+6*columns+27+9))
        if required>maximum_jacobian_bytes or workspace>maximum_working_bytes:raise ValueError('Complete triangle pair Jacobians exceed budget; no points, pairs or columns dropped')
        ja=_real(raw,raw.shape,'left Jacobian');jb=_real(right_jacobian,raw.shape,'right Jacobian')
    elif pairs*(27+9)*8>maximum_working_bytes:raise ValueError('Complete value workspace exceeds budget')
    origin=a[:,:1,:];ap=np.einsum('pi,pvi->pv',n,a-origin);bp=np.einsum('pi,pvi->pv',n,b-origin);gaps=bp[:,None,:]-ap[:,:,None]
    rows=((gaps-minimum_gap_m)/length_scale_m).reshape(-1);jac=None
    if columns:
        # Project each side first: avoid a [pairs,3,3,xyz,columns] temporary.
        aj=np.einsum('pi,pvic->pvc',n,ja);bj=np.einsum('pi,pvic->pvc',n,jb)
        jac=((bj[:,None,:,:]-aj[:,:,None,:])/length_scale_m).reshape(-1,columns)
    if not np.isfinite(rows).all() or jac is not None and not np.isfinite(jac).all():raise ValueError('Nonfinite complete projection rows')
    return dict(margins=rows,jacobian=jac,projected_gap_m=gaps.min(axis=(1,2)),report=dict(schema='strep-native-triangle-pair-projection-v1',pairs=pairs,rows=9*pairs,columns=columns,all_vertex_combinations_retained=True,row_order='pair,left-vertex,right-vertex',fixed_directions=True,jacobian_bytes=9*pairs*columns*8,collision_certified=False,quality_approved=False,release_approved=False,scope='Supplied complete triangle pairs and fixed oriented directions only. Caller binds source identities, permissions and clocks. A failed directional gap is not collision or infeasibility; positive floating rows are not exact whole-mesh/continuous/quality approval.'))
