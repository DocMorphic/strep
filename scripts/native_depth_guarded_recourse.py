"""Assemble current observations with original bounds and explicit local depth guards.

Native/contact/floor derivatives may be cached approximations. Surface witnesses
and derivatives can be refreshed independently. No decoded feasibility is implied.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_surface_lift import lift


def assemble(native,native_jac,contacts,contact_jac,floor_gaps,floor_jac,surface_gaps,surface_jac,value,lower,upper,trust,*,
        source_native_caps,source_native_scales,source_contact_caps,source_contact_scales,contact_kinds,
        depth_rows,depth_limits_m,native_headroom=.002,contact_reserve_m=.0005,surface_clearance_m=.0005,maximum_nonzeros=6000000):
    if not isinstance(native,NormRows) or contacts is not None and not isinstance(contacts,NormRows):raise ValueError('Complete native and optional contact norms required')
    value,lower,upper=[np.asarray(v,float) for v in (value,lower,upper)];floor=np.asarray(floor_gaps,float);gaps=np.asarray(surface_gaps,float)
    n=len(native.caps);c=0 if contacts is None else len(contacts.caps);width=len(value) if value.ndim==1 else 0
    if (not width or lower.shape!=value.shape or upper.shape!=value.shape or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
            or floor.ndim!=1 or gaps.ndim!=1 or not len(gaps) or any(not np.isfinite(v).all() for v in (value,lower,upper,floor,gaps))
            or type(trust) not in (int,float) or not np.isfinite(trust) or trust<=0
            or type(maximum_nonzeros) is not int or not 1<=maximum_nonzeros<=6000000):raise ValueError('Complete finite current state, original boxes and bounded matrix required')
    for v,maximum in ((native_headroom,.01),(contact_reserve_m,.005),(surface_clearance_m,.005)):
        if type(v) not in (int,float) or not np.isfinite(v) or not 0<=v<=maximum:raise ValueError('Invalid bounded search reserve or clearance')
    empty=np.empty(0);cv=np.empty((0,3)) if contacts is None else contacts.vectors;cc=empty if contacts is None else contacts.caps;cs=empty if contacts is None else contacts.scales
    for actual,expected in ((native.caps,source_native_caps),(native.scales,source_native_scales),(cc,source_contact_caps),(cs,source_contact_scales)):
        if not np.array_equal(actual,np.asarray(expected,float)):raise ValueError('Original native/contact reference caps or scales changed')
    if (not isinstance(contact_kinds,list) or len(contact_kinds)!=c or any(v not in ('position','relative-speed') for v in contact_kinds)):
        raise ValueError('Explicit complete contact units required')
    if (any(not np.isfinite(v).all() for v in (native.vectors,native.caps,native.scales,cv,cc,cs)) or np.any(native.scales<=0) or np.any(cs<=0)
            or np.any(native.residual()>0) or contacts is not None and np.any(contacts.residual()>0) or np.any(floor<0)):
        raise ValueError('Current native/contact/floor anchor must pass original bounds; no rebasing')
    matrices=[sparse.csr_matrix(j) for j in (native_jac,contact_jac,floor_jac,surface_jac)]
    nj,cj,fj,gj=matrices
    if any(j.shape!=shape or not np.isfinite(j.data).all() for j,shape in zip(matrices,((3*n,width),(3*c,width),(len(floor),width),(len(gaps),width)))):
        raise ValueError('Complete finite native/contact/floor/surface Jacobians required')
    ids=np.asarray(depth_rows);limits=np.asarray(depth_limits_m,float)
    if (ids.ndim!=1 or len(ids) and (ids.dtype.kind not in 'iu' or np.any(ids<0) or np.any(ids>=len(gaps)) or np.any(np.diff(ids.astype(np.int64))<=0))
            or any(isinstance(v,(bool,np.bool_)) for v in np.asarray(depth_rows,dtype=object).flat)
            or limits.shape!=ids.shape or not np.isfinite(limits).all() or np.any(limits<0)):
        raise ValueError('Sorted complete declared depth indices and finite nonnegative limits required')
    ids=ids.astype(int)
    if np.any(gaps[ids]+limits<0):raise ValueError('Declared local depth limits exclude the current anchor')
    responsive=np.diff(nj.indptr).reshape(n,3).sum(1)>0
    margin=np.maximum(0,native.caps-np.linalg.norm(native.vectors,axis=1))
    nr=np.minimum.reduce([native_headroom*native.scales,.01*native.caps,.5*margin]);nr[~responsive]=0
    cr=np.zeros(c);position=np.array([v=='position' for v in contact_kinds],bool)
    cr[position]=np.minimum(contact_reserve_m,.5*np.maximum(0,cc-np.linalg.norm(cv,axis=1)))[position]
    vectors=[native.vectors,cv];caps=[native.caps-nr,cc-cr];scales=[native.scales,cs];jacs=[nj,cj];conversions={}
    for label,scalar,derivative in [('floor',floor,fj),('depth',gaps[ids]+limits,gj[ids])]:
        if not len(scalar):continue
        rows,j,meta=lift(scalar,derivative,value,lower,upper,trust,clearance=0.,scale=.005)
        vectors.append(rows.vectors);caps.append(rows.caps);scales.append(rows.scales);jacs.append(j);conversions[label]=meta
    hard=n+c+len(floor)+len(ids)
    vectors.append(cv);caps.append(cc);scales.append(cs);jacs.append(cj)
    rows,j,meta=lift(gaps,gj,value,lower,upper,trust,clearance=surface_clearance_m,scale=.005)
    vectors.append(rows.vectors);caps.append(rows.caps);scales.append(rows.scales);jacs.append(j);conversions['surface']=meta
    combined=NormRows(np.concatenate(vectors),np.concatenate(caps),np.concatenate(scales));jac=sparse.vstack(jacs,format='csc')
    if jac.nnz>maximum_nonzeros:raise ValueError('Complete guarded matrix exceeds sparse budget; no subset returned')
    if np.any(combined.residual()[:hard]>1e-8):raise ValueError('Lifted full hard anchor fails unchanged affine postcheck')
    info=dict(native_rows=n,contact_rows=c,floor_rows=len(floor),depth_guard_rows=len(ids),hard_rows=hard,contact_objective_rows=c,surface_rows=len(gaps),total_rows=len(combined.caps),controls=width,combined_nonzeros=jac.nnz,
        depth_source_row_indices=ids.tolist(),depth_limits_m=limits.tolist(),conversions=conversions,original_reference_caps_scales_exact=True,anchor_original_bounds_pass=True,
        native_search_reserve_policy='min(declared scaled headroom, one percent original cap, half current original slack); responsive rows only',
        contact_search_reserve_policy='position rows only, at most half current authored slack',original_selected=True,quality_approved=False,release_approved=False,
        scope='Current observed vectors with original native/contact bounds and explicit local material depth limits. Cached derivatives remain approximations. '
            'Fixed surface rows do not certify nearest depth or unqueried vertices; full decoded native/floor/contact/mesh acceptance remains required.')
    return combined,jac,info,dict(native=nr,contacts=cr)
