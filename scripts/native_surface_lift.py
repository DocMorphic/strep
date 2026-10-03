"""Exact affine halfspace-to-norm conversion inside an explicit local trust box."""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows


def lift(gaps,jacobian,value,lower,upper,trust,*,clearance=.0005,scale=.005):
    gaps,value,lower,upper=map(lambda a:np.asarray(a,float),(gaps,value,lower,upper))
    jacobian=sparse.csr_matrix(jacobian)
    if (gaps.ndim!=1 or not len(gaps) or value.ndim!=1 or lower.shape!=value.shape or upper.shape!=value.shape
            or jacobian.shape!=(len(gaps),len(value)) or any(not np.isfinite(a).all() for a in (gaps,value,lower,upper,jacobian.data))
            or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
            or type(trust) not in (int,float) or not np.isfinite(trust) or trust<=0
            or type(clearance) not in (int,float) or not np.isfinite(clearance) or clearance<0
            or type(scale) not in (int,float) or not np.isfinite(scale) or scale<=0):
        raise ValueError('Finite scalar surface model and valid trust box required')
    extent=np.maximum(np.minimum(trust,upper-value),np.minimum(trust,value-lower))
    excursion=np.asarray(abs(jacobian)@extent).ravel()
    offset=np.maximum(1.,gaps+excursion+1.)
    vectors=np.c_[offset-gaps,np.zeros((len(gaps),2))]
    rows=NormRows(vectors,offset-clearance,np.full(len(gaps),scale))
    j=jacobian.tocoo();matrix=sparse.csc_matrix((-j.data,(3*j.row,j.col)),shape=(3*len(gaps),len(value)))
    return rows,matrix,dict(offset_m=offset.tolist(),absolute_affine_gap_excursion_m=excursion.tolist(),
        clearance_m=float(clearance),scale_m=float(scale),trust=float(trust),
        scope='Norm residual equals the scalar clearance deficit inside this affine trust box. '
            'No nonlinear pose, mesh separation or continuous-time bound.')
