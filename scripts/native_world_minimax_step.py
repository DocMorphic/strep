"""Bounded minimax/L1 direction; complete nonlinear acceptance is separate.

Margins are positive when a supplied proposal-model row passes. Extra cuts use
matrix @ delta <= upper. No source/cap interpretation or motion choice is made.
"""
import numpy as np
from scipy import sparse
from scipy.optimize import linprog

MAXIMUM_BYTES=64*1024**2


def _real(value):
    array=np.asarray(value)
    if array.dtype.kind not in 'fiu' or array.dtype.itemsize>8 or not np.isfinite(array).all():raise ValueError('Complete finite real arrays required')
    return array.astype(float,copy=True)


def minimax_step(margins,jacobian,lower_delta,upper_delta,*,extra_matrix=None,extra_upper=None,
                 l1_penalty=1e-5,maximum_matrix_bytes=MAXIMUM_BYTES,time_limit_seconds=30.,maximum_iterations=1000):
    if type(maximum_matrix_bytes) is not int or not 1<=maximum_matrix_bytes<=MAXIMUM_BYTES:raise ValueError('Complete matrix storage budget up to64MiB required')
    if type(l1_penalty) not in (int,float) or not np.isfinite(l1_penalty) or not 1e-12<=l1_penalty<=1:raise ValueError('Finite positive bounded L1 penalty required')
    if type(time_limit_seconds) not in (int,float) or not np.isfinite(time_limit_seconds) or not .01<=time_limit_seconds<=60 or type(maximum_iterations) is not int or not 1<=maximum_iterations<=100000:
        raise ValueError('Explicit bounded solver time and iteration budget required')
    raw=np.asarray(jacobian);rows=np.asarray(margins)
    if raw.ndim!=2 or not 1<=raw.shape[0]<=8192 or not 1<=raw.shape[1]<=768 or rows.shape!=(raw.shape[0],):raise ValueError('Every original model row and explicit complete column required')
    count,columns=raw.shape
    if (extra_matrix is None)!=(extra_upper is None):raise ValueError('Complete extra matrix/upper pair required')
    cuts=np.empty((0,columns)) if extra_matrix is None else np.asarray(extra_matrix)
    upper=np.empty(0) if extra_upper is None else np.asarray(extra_upper)
    if cuts.ndim!=2 or cuts.shape[1]!=columns or not 0<=len(cuts)<=8192 or upper.shape!=(len(cuts),):raise ValueError('Every extra proposal row and full matching column set required')
    if (raw.size+cuts.size)*8>maximum_matrix_bytes:raise ValueError('Complete input Jacobians exceed budget; no rows/columns discarded')
    margin=_real(rows);jac=_real(raw);cuts=_real(cuts);upper=_real(upper);lower=_real(lower_delta);higher=_real(upper_delta)
    if (lower.shape!=(columns,) or higher.shape!=(columns,) or np.any(lower>0) or np.any(higher<0) or np.any(lower>higher) or np.any(lower< -2) or np.any(higher>2)):
        raise ValueError('Complete finite relative step boxes containing zero within [-2,2] required')
    nonzeros=int(np.count_nonzero(jac)+count+4*columns+np.count_nonzero(cuts));constraint_rows=count+2*columns+len(cuts)
    estimated_bytes=12*nonzeros+4*(constraint_rows+1)
    if estimated_bytes>maximum_matrix_bytes:raise ValueError('Complete sparse model exceeds storage budget before allocation')
    identity=sparse.eye(columns,format='csr')
    matrix=sparse.vstack([sparse.hstack([-sparse.csr_matrix(jac),sparse.csr_matrix((count,columns)),-np.ones((count,1))]),
        sparse.hstack([identity,-identity,sparse.csr_matrix((columns,1))]),sparse.hstack([-identity,-identity,sparse.csr_matrix((columns,1))]),
        sparse.hstack([sparse.csr_matrix(cuts),sparse.csr_matrix((len(cuts),columns+1))])],format='csr')
    actual_bytes=matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes
    if actual_bytes>maximum_matrix_bytes:raise ValueError('Complete sparse storage exceeds budget')
    rhs=np.r_[margin,np.zeros(2*columns),upper];cost=np.r_[np.zeros(columns),np.full(columns,l1_penalty),1.]
    bounds=list(zip(lower,higher))+[(0.,float(v)) for v in np.maximum(-lower,higher)]+[(0.,None)]
    # Do not override the host process's existing HiGHS thread scheduler.
    fit=linprog(cost,A_ub=matrix,b_ub=rhs,bounds=bounds,method='highs',options=dict(time_limit=float(time_limit_seconds),maxiter=maximum_iterations,primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9))
    direction=None;residual=None
    if fit.success:
        solution=np.asarray(fit.x,float)
        if solution.shape==(2*columns+1,) and np.isfinite(solution).all():
            residual=float(np.max(matrix@solution-rhs));candidate=solution[:columns]
            if not np.any(candidate<lower) and not np.any(candidate>higher) and residual<=1e-7:direction=candidate.copy()
    predicted=None if direction is None else margin+jac@direction
    if predicted is not None and not np.isfinite(predicted).all():direction=None;predicted=None
    report=dict(schema='strep-native-world-minimax-step-v1',model_rows=count,extra_proposal_rows=len(cuts),complete_columns=columns,
        linear_constraint_rows=constraint_rows,sparse_nonzero_entries=matrix.nnz,sparse_matrix_bytes=actual_bytes,maximum_matrix_bytes=maximum_matrix_bytes,
        solver_success=bool(fit.success),solver_status=int(fit.status),solver_message=str(fit.message),usable_direction=direction is not None,
        maximum_model_constraint_residual=residual,baseline_maximum_model_violation=float(np.maximum(-margin,0).max()),
        predicted_maximum_model_violation=None if predicted is None else float(np.maximum(-predicted,0).max()),
        maximum_extra_cut_violation=None if direction is None or not len(cuts) else float(np.max(cuts@direction-upper)),
        l1_penalty=float(l1_penalty),existing_highs_scheduler_preserved=True,original_selected=True,quality_approved=False,release_approved=False,
        scope='All supplied local model rows/cuts/columns retained. Linear success, failure or a zero direction is not nonlinear motion feasibility/infeasibility. Caller retains source bindings and every original raw/saved/native/pose/geometry check; no clip, optimizer convergence or selection.')
    return direction,report
