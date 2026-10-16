"""Complete staged native derivatives at current absolute original-source controls.

Only native rotation/displacement/rate rows are differentiated. Contacts, floors
and geometry need their own coupled observations and independent acceptance.
"""
import numpy as np
from scipy import sparse
from native_contact_actor_validation import native_rows


def linearize(model,value,*,source_caps,source_scales,worlds=None,step=.0001,maximum_nonzeros=3000000):
    raw=np.asarray(value);point=np.asarray(value,float)
    if (raw.dtype.kind not in 'fi' or point.shape!=(model.size,) or not np.isfinite(point).all()
            or any(isinstance(v,(bool,np.bool_)) for v in np.asarray(value,dtype=object).flat)
            or type(step) not in (int,float) or not np.isfinite(step) or not 1e-6<=step<=.01
            or type(maximum_nonzeros) is not int or not 1<=maximum_nonzeros<=3000000
            or not 1<=model.size<=768 or np.any(model.seed)):
        raise ValueError('Complete current controls, zero original seed and bounded difference/budget required')
    model.controls(point);model.check()
    original=native_rows(model,model.initial,model.source_world)
    if not np.array_equal(original.caps,np.asarray(source_caps,float)) or not np.array_equal(original.scales,np.asarray(source_scales,float)):
        raise ValueError('Complete original native reference caps/scales changed')
    supplied=worlds is not None
    if worlds is None:worlds=model.worlds(point)
    base=native_rows(model,point,worlds)
    def continuous(p):
        rows=native_rows(model,p,model.worlds(p,quantized=False))
        if not np.array_equal(rows.caps,original.caps) or not np.array_equal(rows.scales,original.scales):raise ValueError('Original native derivative bounds changed')
        return rows.vectors
    smooth=continuous(point);data=[];indices=[];pointers=[0];schemes=[];steps=[]
    for column in range(model.size):
        left=point[column]-model.lower[column];right=model.upper[column]-point[column]
        if min(left,right)>=step:
            h=step;plus=point.copy();minus=point.copy();plus[column]+=h;minus[column]-=h
            derivative=(continuous(plus)-continuous(minus))/(2*h);scheme='central'
        else:
            sign=1 if right>=left else -1;room=right if sign>0 else left;h=sign*min(step,room/2)
            if h==0:raise ValueError('No bounded finite-difference room')
            one=point.copy();two=point.copy();one[column]+=h;two[column]+=2*h
            derivative=(-3*smooth+4*continuous(one)-continuous(two))/(2*h);scheme='one-sided-second-order'
        flat=derivative.ravel()
        if not np.isfinite(flat).all():raise ValueError('Nonfinite complete native derivative')
        ids=np.flatnonzero(flat)
        if pointers[-1]+len(ids)>maximum_nonzeros:raise ValueError('Complete native Jacobian exceeds budget; no entries discarded')
        data.append(flat[ids].copy());indices.append(ids);pointers.append(pointers[-1]+len(ids));schemes.append(scheme);steps.append(float(h))
    jac=sparse.csc_matrix((np.concatenate(data),np.concatenate(indices),pointers),shape=(base.vectors.size,model.size))
    model.check()
    return base,jac,dict(actor=model.name,native_rows=len(base.caps),controls=model.size,nonzero_entries=jac.nnz,
        difference_step=step,actual_difference_steps=steps,difference_schemes=schemes,all_control_columns_evaluated=True,
        original_reference_caps_scales_exact=True,original_source_epoch=True,caller_provided_worlds=supplied,
        anchor_original_native_pass=bool(np.all(base.residual()<=0)),maximum_smooth_observed_vector_difference=float(np.linalg.norm(base.vectors-smooth,axis=1).max()),
        original_selected=True,quality_approved=False,release_approved=False,
        scope='Complete actor native rows and current-point continuous finite differences with original caps/scales. '
            'No derivative accuracy certificate, nonlinear feasibility, coupled contact, floor, mesh, export, engine or quality approval.')
