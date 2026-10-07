"""Bounded finite retreat of an affine step toward a verified original anchor.

Original caps remain unchanged. This checks represented affine vectors only;
actual stored motion and geometry remain separate acceptance gates.
"""
import numpy as np
from scipy import sparse

FRACTIONS=(1.,*[1.-2.**(-k) for k in range(40,0,-1)],*[2.**(-k) for k in range(2,41)],0.)


def project(native,jacobian,step,value,lower,upper,trust):
    vectors,caps,scales=[np.asarray(a,float) for a in (native.vectors,native.caps,native.scales)]
    step,value,lower,upper=[np.asarray(a,float) for a in (step,value,lower,upper)]
    jac=sparse.csr_matrix(jacobian,copy=True);n=len(value) if value.ndim==1 else 0
    if (not 1<=n<=96 or vectors.ndim!=2 or vectors.shape[1:]!=(3,) or not len(vectors)
            or caps.shape!=(len(vectors),) or scales.shape!=caps.shape
            or any(a.shape!=(n,) for a in (step,lower,upper)) or jac.shape!=(vectors.size,n)
            or any(not np.isfinite(a).all() for a in (vectors,caps,scales,step,value,lower,upper,jac.data))
            or np.any(scales<=0) or np.any(caps<0) or np.any(lower>=upper)
            or np.any(value<lower) or np.any(value>upper)
            or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6<=trust<=.02):
        raise ValueError('Complete finite original affine norms, ordered controls and trust required')
    lo,hi=np.maximum(-trust,lower-value),np.minimum(trust,upper-value)
    if np.any(step<lo-1e-9) or np.any(step>hi+1e-9):
        raise ValueError('Candidate must remain in the original trust/control box')
    anchor=float(((np.linalg.norm(vectors,axis=1)-caps)/scales).max())
    info=dict(schema='strep-native-affine-ray-retreat-v1',status='not-selected',original_anchor_maximum_excess=anchor,
        maximum_candidate_probes=len(FRACTIONS),original_caps_scales_unchanged=True,strict_zero_excess_required=True,
        records=[],selected_fraction=None,quality_approved=False,release_approved=False,
        scope='First tested strictly passing nonzero projected step in an explicit81-fraction ray prefix. '
            'Original affine caps/scales and trust/control boxes only; no maximal feasible fraction, solver optimum, '
            'actual stored-motion/contact/geometry or quality guarantee.')
    if anchor>0:return None,dict(info,status='OriginalAnchorNotStrictlyPassing')
    for alpha in FRACTIONS:
        projected=np.clip(step*alpha,lo,hi)
        projected=np.clip(value+projected,lower,upper)-value
        # Control subtraction may round outward; never accept an out-of-box step.
        inside=bool(np.all(projected>=lo) and np.all(projected<=hi))
        moved=vectors+(jac@projected).reshape(vectors.shape)
        excess=float(((np.linalg.norm(moved,axis=1)-caps)/scales).max())
        passing=inside and excess<=0
        positive=bool(np.any(projected!=0))
        info['records'].append(dict(fraction=alpha,original_affine_native_max_excess=excess,
            original_step_box_pass=inside,strict_native_pass=excess<=0,nonzero_step=positive))
        if passing and positive:
            return projected,dict(info,status='VerifiedFiniteRayPoint',selected_fraction=alpha,
                selected_native_maximum_excess=excess,maximum_control_step=float(abs(projected).max()))
    return None,dict(info,status='NoPositiveTestedRayPoint')
