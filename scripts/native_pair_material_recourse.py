"""Recenter a cached pair proposal on decoded observations without resetting limits.

Cached derivatives remain local approximations. Search-only material reserves
tighten copied caps; actual original-bound export/geometry checks still decide.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows


def require(value,message):
    if not value:raise ValueError(message)


def recenter(pair,value,worlds,parent,identity):
    pair.check();value=pair.controls(value);pair.validate_worlds(worlds)
    require(isinstance(parent,NormRows),'Complete cached parent norms required')
    native,contact=pair.norms(value,worlds)
    n=len(native.caps);c=0 if contact is None else len(contact.caps);f=len(pair.times)*len(pair.names)
    guide=pair.guide_gaps(value,worlds);s=len(guide)
    require(all(type(identity.get(k)) is int and identity[k]==v for k,v in dict(native_rows=n,contact_rows=c,floor_rows=f,guide_rows=s,hard_rows=n+c+f,controls=pair.size).items())
        and len(parent.caps)==n+c+f+s,'Complete original parent row layout required')
    require(np.array_equal(parent.caps[:n],pair.native_caps) and np.array_equal(parent.scales[:n],pair.native_scales)
        and np.array_equal(parent.caps[n:n+c],pair.protected_contact_caps)
        and np.array_equal(parent.scales[n:n+c],pair.contact_scales),'Original native/contact caps or scales changed')
    conversion=identity['conversion'];offset=np.asarray(conversion['offset_m'],float)
    require(conversion['clearance_m']==0 and offset.shape==(f+s,) and np.isfinite(offset).all() and np.all(offset>0)
        and np.array_equal(parent.caps[n+c:],offset) and np.all(parent.scales[n+c:]==conversion['scale_m'])
        and np.all(parent.vectors[n+c:,1:]==0),'Original scalar lift offsets/caps/scales required')
    floors={name:pair.models[name].floor(worlds[name])[0] for name in pair.names}
    floor_gaps=np.concatenate([floors[name]-np.minimum(0,pair.source_floor[name]) for name in pair.names])
    gaps=np.r_[floor_gaps,guide];first=offset-gaps
    require(np.isfinite(first).all() and np.all(first>=0),'Decoded gaps outside original scalar lift domain')
    vectors=np.r_[native.vectors,np.empty((0,3)) if contact is None else contact.vectors,np.c_[first,np.zeros((len(first),2))]]
    rows=NormRows(vectors,parent.caps.copy(),parent.scales.copy());pair.check()
    return rows,dict(native_rows=n,contact_rows=c,floor_rows=f,guide_rows=s,hard_rows=n+c+f,
        original_parent_caps_scales_exact=True,actual_decoded_vectors=True,cached_derivatives_recomputed=False,
        floor_no_worsening=bool(np.all(floor_gaps>=0)),native_failures=int((native.residual()>0).sum()),
        authored_contacts_pass=None if contact is None else bool(np.all(contact.residual()<=0)),
        contact_no_worsening=None if contact is None else bool(np.all(np.linalg.norm(contact.vectors,axis=1)<=pair.protected_contact_caps)),
        scope='Actual decoded row recentering only; cached derivatives remain approximate. Original failed physical conditions stay failed.',quality_approved=False,release_approved=False)


def search_reserve(material,jacobian,*,reserve_m=2e-7):
    require(isinstance(material,NormRows),'Complete observed material norms required')
    jacobian=sparse.csr_matrix(jacobian)
    require(jacobian.shape[0]==material.vectors.size and np.isfinite(jacobian.data).all(),'Complete finite material Jacobian required')
    require(type(reserve_m) in (int,float) and np.isfinite(reserve_m) and 0<reserve_m<=1e-5,'Explicit positive bounded material search reserve required')
    excess=np.linalg.norm(material.vectors,axis=1)-material.caps;bad=excess>0
    require(bool(bad.any()),'At least one observed material failure required')
    responsive=np.diff(jacobian.indptr).reshape(-1,3).sum(1)>0
    require(not np.any(bad&~responsive),'Failed fixed material rows cannot consume cached recourse')
    selected=np.flatnonzero(responsive&(excess>=-reserve_m));caps=material.caps.copy();caps[selected]-=reserve_m
    require(np.all(caps>=0),'Positive remaining material search caps required')
    return NormRows(material.vectors.copy(),caps,material.scales.copy()),dict(reserve_m=float(reserve_m),
        originally_failed_rows=np.flatnonzero(bad).tolist(),tightened_rows=selected.tolist(),
        original_acceptance_caps_unchanged=True,scope='Search-only copied caps tighten responsive near-boundary material rows. No original motion or acceptance limit changes.',quality_approved=False,release_approved=False)
