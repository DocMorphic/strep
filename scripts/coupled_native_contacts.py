"""Native motion and complete contact surfaces in one protected proposal model.

Linear proposals are never acceptance certificates. Independently saved motion,
individual contact conditions and complete declared geometry decide retention.
"""
import numpy as np
from scipy import sparse
from cached_contact_norms import CachedContactNorms
from native_scene_norms import NormRows,linearize as native_linearize
from native_contact_norms import protect_rows,row_regression,score


def acceptable(before_native,after_native,before_contact,after_contact,geometry):
    before_native,after_native,before_contact,after_contact=[np.asarray(a,float) for a in (before_native,after_native,before_contact,after_contact)]
    if (any(a.ndim!=1 or not len(a) or not np.isfinite(a).all() for a in (before_native,after_native,before_contact,after_contact))
            or before_native.shape!=after_native.shape or before_contact.shape!=after_contact.shape):
        raise ValueError('Matching complete finite native and contact populations required')
    if np.any(before_native>0) or np.any(after_native>0):return False
    if np.any(row_regression(before_contact,after_contact)>0):return False
    if not isinstance(geometry,dict) or geometry.get('sampled_conditions_pass') is not True:return False
    old,new=score(before_contact),score(after_contact)
    return bool(new[0]<=old[0] and new[1]<old[1]-1e-12)


class CoupledContactModel:
    def __init__(self,problem,policy,digest,*,maximum_contact_rows=20000,maximum_cache_bytes=256*1024**2):
        self.problem=problem
        self.contact=CachedContactNorms(problem,policy,digest,maximum_rows=maximum_contact_rows,maximum_cache_bytes=maximum_cache_bytes)
        self.uniform=problem.uniform.copy()
        self.rates={n:dict(dt=c.dt,tolerance=c.tolerance,caps=[a.copy() for a in c.caps]) for n,c in problem.caps.items()}

    def check_caps(self):
        if not np.array_equal(self.uniform,self.problem.uniform) or set(self.rates)!=set(self.problem.caps):
            raise ValueError('Original uniform source-rate population changed')
        for name,original in self.rates.items():
            current=self.problem.caps[name]
            if current.dt!=original['dt'] or current.tolerance!=original['tolerance'] or len(current.caps)!=len(original['caps']):
                raise ValueError('Original source-rate settings changed')
            if any(not np.array_equal(a,b) for a,b in zip(current.caps,original['caps'])):
                raise ValueError('Original source-rate caps changed')

    def linearize(self,value,decoded_worlds,trust,*,step=.001):
        self.check_caps()
        native,jac,identity=native_linearize(self.problem,value,step=step,difference_source='continuous',base_worlds=decoded_worlds)
        residual=self.problem.constraints(value,decoded_worlds)
        if np.any(residual>0):raise ValueError('Coupled contact improvement requires a feasible native/contact start')
        np.testing.assert_allclose(native.residual(),residual,atol=1e-9,rtol=1e-12)
        extra,extra_jac,contact_identity=self.contact.linearize(value,decoded_worlds,trust,step=step)
        contact_before=self.contact.residual(decoded_worlds)
        np.testing.assert_allclose(extra.residual(),contact_before,atol=1e-9,rtol=1e-12)
        combined=NormRows(np.r_[native.vectors,extra.vectors],np.r_[native.caps,extra.caps],np.r_[native.scales,extra.scales])
        derivative=sparse.vstack([jac,extra_jac],format='csc')
        guarded,derivative,guard=protect_rows(combined,derivative,len(native.caps),contact_before)
        self.check_caps()
        return guarded,derivative,dict(native=identity,contact=contact_identity,guard=guard,
            hard_rows=guard['hard_rows'],complete_native_rows=len(native.caps),complete_surface_contact_rows=len(contact_before),
            source_caps_unchanged=True,all_native_contact_positions_and_frame_speeds_protected=True,
            individual_surface_rows_protected=True,authored_limits_unchanged=True,
            full_geometry_in_proposal=False,independent_decode_and_full_geometry_required=True,
            quality_approved=False,release_approved=False)
