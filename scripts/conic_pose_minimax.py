"""Small complete minimax proposal with exact normalized control-vector balls.

Only a linearization is solved. Strict nonlinear and saved-asset gates belong
to the caller; solver tolerances never become physical acceptance tolerances.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module


def minimax_step(margins,jacobian,controls,*,trust=.25,l1_penalty=1e-5,maximum_bytes=64*1024**2):
    raw=[np.asarray(v) for v in [margins,jacobian,controls]]
    if any(v.dtype.kind not in 'fiu' or not np.isfinite(v).all() or np.any(abs(v)>1e6) for v in raw):raise ValueError('Complete finite real model inputs required')
    m,j,x=[np.array(v,dtype=float,copy=True) for v in raw]
    if j.ndim!=2 or not 1<=len(j)<=8192 or not 3<=j.shape[1]<=384 or j.shape[1]%3 or m.shape!=(len(j),) or x.shape!=(j.shape[1],):
        raise ValueError('Every model row and complete grouped three-vector controls required')
    if np.any(np.linalg.norm(x.reshape(-1,3),axis=1)>1):raise ValueError('Initial control vectors already exceed declared budgets')
    if type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=1 or type(l1_penalty) not in (int,float) or not 1e-12<=l1_penalty<=1:
        raise ValueError('Explicit bounded trust and positive finite movement penalty required')
    if type(maximum_bytes) is not int or not 1<=maximum_bytes<=64*1024**2 or sum(v.nbytes for v in [m,j,x])*12>maximum_bytes:
        raise ValueError('Complete preallocation model budget exceeded; no truncation')
    columns=len(x);rows=len(m);variables=2*columns+1;identity=sparse.eye(columns,format='csc');zero=sparse.csc_matrix
    lower=np.maximum(-trust,-1-x);upper=np.minimum(trust,1-x)
    # Search reserves are strictly inside author limits and do not alter gates.
    upper=np.maximum(0.,upper-1e-8);lower=np.minimum(0.,lower+1e-8)
    blocks=[sparse.hstack([-sparse.csc_matrix(j),zero((rows,columns)),-np.ones((rows,1))]),
        sparse.hstack([identity,-identity,zero((columns,1))]),sparse.hstack([-identity,-identity,zero((columns,1))]),
        sparse.hstack([identity,zero((columns,columns+1))]),sparse.hstack([-identity,zero((columns,columns+1))]),
        sparse.csc_matrix(([ -1.],([0],[variables-1])),shape=(1,variables))]
    rhs=[m,np.zeros(2*columns),upper,-lower,np.zeros(1)];linear_rows=rows+4*columns+1
    solver=solver_module();cones=[solver.NonnegativeConeT(linear_rows)]
    for group in range(columns//3):
        index=np.arange(3*group,3*group+3);matrix=sparse.csc_matrix((-np.ones(3),(np.arange(1,4),index)),shape=(4,variables))
        blocks.append(matrix);rhs.append(np.r_[1-1e-8,x[index]]);cones.append(solver.SecondOrderConeT(4))
    matrix=sparse.vstack(blocks,format='csc');matrix.sum_duplicates();matrix.eliminate_zeros();bound=np.concatenate(rhs)
    storage=matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes
    if storage>maximum_bytes:raise ValueError('Complete sparse model exceeds declared budget')
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=200;settings.time_limit=10.;settings.tol_gap_abs=1e-10;settings.tol_gap_rel=1e-10;settings.tol_feas=1e-10;settings.max_threads=1
    cost=np.r_[np.zeros(columns),np.full(columns,l1_penalty),1.]
    fit=solver.DefaultSolver(sparse.csc_matrix((variables,variables)),cost,matrix,bound,cones,settings).solve()
    solution=np.asarray(fit.x,dtype=float);direction=None;residual=None;norm_excess=None
    if str(fit.status)=='Solved' and solution.shape==(variables,) and np.isfinite(solution).all():
        delta=solution[:columns];residual=float(np.max(matrix[:linear_rows]@solution-bound[:linear_rows]));norm_excess=float(np.max(np.linalg.norm((x+delta).reshape(-1,3),axis=1)-1))
        if np.all(delta>=lower) and np.all(delta<=upper) and norm_excess<=0 and residual<=1e-8:direction=delta.copy()
    after=None if direction is None else m+j@direction
    report=dict(schema='strep-conic-pose-minimax-v1',solver_status=str(fit.status),solver_version=solver.__version__,model_rows=rows,complete_columns=columns,control_vector_balls=columns//3,
        omitted_rows=0,omitted_control_balls=0,sparse_bytes=storage,usable_direction=direction is not None,maximum_linear_model_residual=residual,maximum_actual_control_norm_excess=norm_excess,
        baseline_maximum_model_violation=float(np.maximum(-m,0).max()),predicted_maximum_model_violation=None if after is None else float(np.maximum(-after,0).max()),
        search_only_interior_reserve=1e-8,added_physical_tolerance=0.,quality_approved=False,release_approved=False,
        scope='Complete supplied signed row minimax plus L1 movement cost and every exact normalized three-vector ball. Strict output checks required; linear status is not nonlinear feasibility or motion approval. No clipping or omitted rows.')
    return direction,report
