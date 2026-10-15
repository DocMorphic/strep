"""Local common-improvement LP; independent nonlinear acceptance is mandatory."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,hstack,vstack,eye


def inward_step(x, residuals, jacobian, lower, upper, trust):
    x,g,j,lo,hi,radius=[np.asarray(a,dtype=float) for a in (x,residuals,jacobian,lower,upper,trust)]
    if x.ndim!=1 or not len(x) or g.ndim!=1 or not len(g) or j.shape!=(len(g),len(x)) or any(a.shape!=x.shape for a in [lo,hi,radius]):
        raise ValueError('Matching parameter and constraint arrays required')
    if not all(np.isfinite(a).all() for a in [x,g,j,radius]) or np.isnan(lo).any() or np.isnan(hi).any() or np.any(lo>hi) or np.any(radius<=0) or np.any(x<lo) or np.any(x>hi):
        raise ValueError('Finite constraints, positive trust and bounded seed required')
    weights=np.minimum(np.maximum(g,0.),1.)
    if not weights.any():return None,dict(success=True,reason='No failed linear-model rows',common_improvement=0.)
    bounds=list(zip(np.maximum(-1.,(lo-x)/radius),np.minimum(1.,(hi-x)/radius)))
    derivative=csr_matrix(j*radius);ceiling=np.maximum(g,0.)-g
    fit=linprog(np.r_[np.zeros(len(x)),-1.],A_ub=hstack([derivative,csr_matrix(weights[:,None])]),
        b_ub=ceiling,bounds=bounds+[(0.,1.)],method='highs',
        options=dict(primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9))
    info=dict(success=bool(fit.success),status=int(fit.status),message=str(fit.message))
    if not fit.success:return None,info
    eta=float(fit.x[-1]);info['common_improvement']=eta
    if eta<=1e-10:return None,{**info,'reason':'No common inward direction in this local model'}
    # Lexicographic tie-break keeps essentially the same common improvement,
    # while minimizing the largest normalized coordinate displacement.
    target=eta*(1-1e-6);identity=eye(len(x),format='csr');ones=csr_matrix(-np.ones((len(x),1)))
    tie=linprog(np.r_[np.zeros(len(x)),1.],
        A_ub=vstack([hstack([derivative,csr_matrix((len(g),1))]),hstack([identity,ones]),hstack([-identity,ones])]),
        b_ub=np.r_[ceiling-target*weights,np.zeros(2*len(x))],bounds=bounds+[(0.,1.)],method='highs',
        options=dict(primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9))
    delta=(tie.x[:-1] if tie.success else fit.x[:-1])*radius
    step=np.clip(x+delta,lo,hi)-x
    predicted=g+j@step
    info.update(tie_break_success=bool(tie.success),predicted_maximum_violation=float(max(0.,predicted.max())),
        predicted_maximum_regression=float(max(0.,(np.maximum(predicted,0)-np.maximum(g,0)).max())),
        minimum_failed_row_decrease=float((g-predicted)[g>0].min()))
    return step,info
