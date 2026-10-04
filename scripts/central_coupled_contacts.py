"""Symmetric full-row proposal derivatives; saved-curve audits decide retention.

Keep the earlier forward model immutable for reproducible comparisons. Exact
zeros alone are omitted from sparse storage, never small measured derivatives.
"""
import numpy as np
from scipy import sparse
from coupled_native_contacts import CoupledContactModel
from native_scene_norms import NormRows,linearize as native_linearize
from native_surface_lift import lift
from native_contact_norms import protect_rows


def contact_linearize(contact,value,decoded_worlds,trust,*,step=.001,maximum_elements=60_000_000):
    problem=contact.problem;value=problem.edits.controls(value)
    if (type(step) not in (int,float) or not np.isfinite(step) or not 1e-6<=step<=.01
            or type(trust) not in (int,float) or not np.isfinite(trust) or trust<=0
            or type(maximum_elements) is not int or maximum_elements<=0):
        raise ValueError('Bounded contact difference step, trust and nonzero budget required')
    lower,upper=np.asarray(problem.lower,float),np.asarray(problem.upper,float)
    if (lower.shape!=value.shape or upper.shape!=value.shape
            or not np.isfinite(np.r_[lower,upper]).all() or np.any(lower>=upper)
            or np.any(value<lower) or np.any(value>upper)):
        raise ValueError('Contact difference point needs finite authored control boxes')
    base,gaps,identity=contact.sample(decoded_worlds)

    def sample(worlds):
        rows,other_gaps,other_identity=contact.sample(worlds)
        if (rows.vectors.shape!=base.vectors.shape or other_gaps.shape!=gaps.shape
                or not np.isfinite(other_gaps).all() or other_identity['identity']!=identity['identity']
                or not np.array_equal(rows.caps,base.caps) or not np.array_equal(rows.scales,base.scales)):
            raise ValueError('Complete contact row population, caps or scales changed')
        return rows,other_gaps

    smooth,smooth_gaps=sample(problem.worlds(value,quantized=False))
    vdata=[];vids=[];vp=[0];sdata=[];sids=[];sp=[0];offsets=[];central=0;queries=0
    for column in range(len(value)):
        def at(h):
            other=value.copy();other[column]+=h
            return sample(problem.worlds(other,quantized=False))
        if value[column]-step>=lower[column] and value[column]+step<=upper[column]:
            positive,pg=at(step);negative,ng=at(-step)
            vector=((positive.vectors-negative.vectors)/(2*step)).ravel();side=(pg-ng)/(2*step)
            offsets.append([float(step),-float(step)]);central+=1;queries+=2
        else:
            room=upper[column]-value[column] if upper[column]-value[column]>=value[column]-lower[column] else lower[column]-value[column]
            h=float(np.copysign(min(step,abs(room)),room))
            if h==0:raise ValueError('No contact finite-difference room')
            other,og=at(h);vector=((other.vectors-smooth.vectors)/h).ravel();side=(og-smooth_gaps)/h
            offsets.append([h]);queries+=1
        if not np.isfinite(np.r_[vector,side]).all():raise ValueError('Nonfinite complete contact derivative')
        vi=np.flatnonzero(vector);si=np.flatnonzero(side)
        if vp[-1]+sp[-1]+len(vi)+len(si)>maximum_elements:
            raise ValueError('Complete contact Jacobian exceeds nonzero budget; no subset returned')
        vids.append(vi);vdata.append(vector[vi]);vp.append(vp[-1]+len(vi))
        sids.append(si);sdata.append(side[si]);sp.append(sp[-1]+len(si))
    vector_jac=sparse.csc_matrix((np.concatenate(vdata),np.concatenate(vids),vp),shape=(base.vectors.size,len(value)))
    side_jac=sparse.csc_matrix((np.concatenate(sdata),np.concatenate(sids),sp),shape=(len(gaps),len(value)))
    side_rows,side_vector_jac,conversion=lift(gaps,side_jac,value,lower,upper,trust,clearance=0.,scale=.005)
    combined=NormRows(np.r_[base.vectors,side_rows.vectors],np.r_[base.caps,side_rows.caps],np.r_[base.scales,side_rows.scales])
    derivative=sparse.vstack([vector_jac,side_vector_jac],format='csc')
    return combined,derivative,dict(**identity,norm_rows=len(combined.caps),orientation_rows=len(base.caps),side_rows=len(gaps),
        conversion=conversion,difference_step=step,difference_source='continuous',difference_scheme='central',
        actual_difference_offsets=offsets,central_difference_columns=central,one_sided_difference_columns=len(value)-central,
        column_proxy_evaluations=queries,decoded_base_anchor=True,maximum_nonzero_jacobian_elements=maximum_elements,
        stored_nonzero_jacobian_elements=derivative.nnz,small_coefficients_discarded=False,
        scope='Complete decoded contact vectors and side gaps; symmetric proxies where both full steps fit, recorded one-sided fallback otherwise. Not a nonlinear feasibility or geometry certificate.')


class CentralCoupledContactModel(CoupledContactModel):
    def linearize(self,value,decoded_worlds,trust,*,step=.001):
        self.check_caps()
        native,jac,identity=native_linearize(self.problem,value,step=step,difference_source='continuous',
            base_worlds=decoded_worlds,difference_scheme='central')
        residual=self.problem.constraints(value,decoded_worlds)
        if np.any(residual>0):raise ValueError('Coupled contact improvement requires a feasible native/contact start')
        np.testing.assert_allclose(native.residual(),residual,atol=1e-9,rtol=1e-12)
        extra,extra_jac,contact_identity=contact_linearize(self.contact,value,decoded_worlds,trust,step=step)
        before=self.contact.residual(decoded_worlds)
        np.testing.assert_allclose(extra.residual(),before,atol=1e-9,rtol=1e-12)
        combined=NormRows(np.r_[native.vectors,extra.vectors],np.r_[native.caps,extra.caps],np.r_[native.scales,extra.scales])
        derivative=sparse.vstack([jac,extra_jac],format='csc')
        guarded,derivative,guard=protect_rows(combined,derivative,len(native.caps),before)
        self.check_caps()
        return guarded,derivative,dict(native=identity,contact=contact_identity,guard=guard,
            hard_rows=guard['hard_rows'],complete_native_rows=len(native.caps),complete_surface_contact_rows=len(before),
            source_caps_unchanged=True,all_native_contact_positions_and_frame_speeds_protected=True,
            individual_surface_rows_protected=True,authored_limits_unchanged=True,small_coefficients_discarded=False,
            full_geometry_in_proposal=False,independent_decode_and_full_geometry_required=True,
            quality_approved=False,release_approved=False)
