"""Small complete minimax proposal with exact normalized control-vector balls.

Only a linearization is solved. Strict nonlinear and saved-asset gates belong
to the caller; solver tolerances never become physical acceptance tolerances.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module


def minimax_step(margins,jacobian,controls,*,trust=.25,l1_penalty=1e-5,maximum_bytes=64*1024**2,protected_rows=None,
                 affine_vectors=None,affine_jacobian=None,affine_radii=None):
    raw=[np.asarray(v) for v in [margins,jacobian,controls]]
    if any(v.dtype.kind not in 'fiu' or not np.isfinite(v).all() or np.any(abs(v)>1e6) for v in raw):raise ValueError('Complete finite real model inputs required')
    m,j,x=[np.array(v,dtype=float,copy=True) for v in raw]
    if j.ndim!=2 or not 1<=len(j)<=8192 or not 3<=j.shape[1]<=384 or j.shape[1]%3 or m.shape!=(len(j),) or x.shape!=(j.shape[1],):
        raise ValueError('Every model row and complete grouped three-vector controls required')
    if np.any(np.linalg.norm(x.reshape(-1,3),axis=1)>1):raise ValueError('Initial control vectors already exceed declared budgets')
    protected=np.zeros(len(m),dtype=bool) if protected_rows is None else np.asarray(protected_rows)
    if protected.dtype!=np.bool_ or protected.shape!=m.shape:raise ValueError('Complete Boolean protected-row mask required')
    protected=protected.copy()
    if type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=1 or type(l1_penalty) not in (int,float) or not 1e-12<=l1_penalty<=1:
        raise ValueError('Explicit bounded trust and positive finite movement penalty required')
    supplied=[v is not None for v in (affine_vectors,affine_jacobian,affine_radii)]
    if any(supplied) and not all(supplied):raise ValueError('Complete affine vectors, Jacobian and radii required together')
    vectors=np.empty((0,3));transform=np.empty((0,3,len(x)));radii=np.empty(0)
    if all(supplied):
        vectors,transform,radii=[np.asarray(v) for v in (affine_vectors,affine_jacobian,affine_radii)]
        if vectors.ndim!=2 or vectors.shape[1]!=3 or not 1<=len(vectors)<=8192 or transform.shape!=(len(vectors),3,len(x)) or radii.shape!=(len(vectors),):
            raise ValueError('Every affine three-vector and all matching control columns required')
        if any(v.dtype.kind not in 'fiu' for v in (vectors,transform,radii)):
            raise ValueError('Finite real affine model inputs required')
    if type(maximum_bytes) is not int or not 1<=maximum_bytes<=64*1024**2 or (sum(v.size*8 for v in [m,j,x,vectors,transform,radii])+j[protected].nbytes)*12>maximum_bytes:
        raise ValueError('Complete preallocation model budget exceeded; no truncation')
    if any(not np.isfinite(v).all() or np.any(abs(v)>1e6) for v in (vectors,transform,radii)) or np.any(radii<1e-12):
        raise ValueError('Finite bounded affine data and positive radii at least1e-12 required')
    vectors,transform,radii=[np.array(v,dtype=float,copy=True) for v in (vectors,transform,radii)];balls=len(vectors)
    columns=len(x);rows=len(m);variables=2*columns+1;identity=sparse.eye(columns,format='csc');zero=sparse.csc_matrix
    author_lower=np.maximum(-trust,-1-x);author_upper=np.minimum(trust,1-x)
    # Search reserves are strictly inside author limits and do not alter gates.
    upper=np.maximum(0.,author_upper-1e-8);lower=np.minimum(0.,author_lower+1e-8)
    blocks=[sparse.hstack([-sparse.csc_matrix(j),zero((rows,columns)),-np.ones((rows,1))]),
        sparse.hstack([identity,-identity,zero((columns,1))]),sparse.hstack([-identity,-identity,zero((columns,1))]),
        sparse.hstack([identity,zero((columns,columns+1))]),sparse.hstack([-identity,zero((columns,columns+1))]),
        sparse.csc_matrix(([ -1.],([0],[variables-1])),shape=(1,variables))]
    rhs=[m,np.zeros(2*columns),upper,-lower,np.zeros(1)];linear_rows=rows+4*columns+1
    if protected.any():
        blocks.append(sparse.hstack([-sparse.csc_matrix(j[protected]),zero((int(protected.sum()),columns+1))]))
        rhs.append(m[protected]-1e-8);linear_rows+=int(protected.sum())
    solver=solver_module();cones=[solver.NonnegativeConeT(linear_rows)]
    for group in range(columns//3):
        index=np.arange(3*group,3*group+3);matrix=sparse.csc_matrix((-np.ones(3),(np.arange(1,4),index)),shape=(4,variables))
        blocks.append(matrix);rhs.append(np.r_[1-1e-8,x[index]]);cones.append(solver.SecondOrderConeT(4))
    if balls:
        affine=sparse.coo_matrix(transform.reshape(3*balls,columns))
        mapped=4*(affine.row//3)+1+affine.row%3
        blocks.append(sparse.csc_matrix((-affine.data,(mapped,affine.col)),shape=(4*balls,variables)))
        rhs.append(np.c_[radii*(1-1e-8),vectors].ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in range(balls))
    matrix=sparse.vstack(blocks,format='csc');matrix.sum_duplicates();matrix.eliminate_zeros();bound=np.concatenate(rhs)
    storage=matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes
    if storage>maximum_bytes:raise ValueError('Complete sparse model exceeds declared budget')
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=200;settings.time_limit=10.;settings.tol_gap_abs=1e-10;settings.tol_gap_rel=1e-10;settings.tol_feas=1e-10;settings.max_threads=1
    cost=np.r_[np.zeros(columns),np.full(columns,l1_penalty),1.]
    fit=solver.DefaultSolver(sparse.csc_matrix((variables,variables)),cost,matrix,bound,cones,settings).solve()
    solution=np.asarray(fit.x,dtype=float);direction=None;residual=None;norm_excess=None;affine_excess=None
    if str(fit.status)=='Solved' and solution.shape==(variables,) and np.isfinite(solution).all():
        delta=solution[:columns];residual=float(np.max(matrix[:linear_rows]@solution-bound[:linear_rows]));norm_excess=float(np.max(np.linalg.norm((x+delta).reshape(-1,3),axis=1)-1))
        if balls:affine_excess=float(np.max(np.linalg.norm(vectors+np.einsum('bcj,j->bc',transform,delta),axis=1)-radii))
        if np.all(delta>=author_lower) and np.all(delta<=author_upper) and norm_excess<=0 and residual<=1e-8 and np.all(m[protected]+j[protected]@delta>=0) and (not balls or affine_excess<=0):direction=delta.copy()
    after=None if direction is None else m+j@direction
    report=dict(schema='strep-conic-pose-minimax-v1',solver_status=str(fit.status),solver_version=solver.__version__,model_rows=rows,complete_columns=columns,control_vector_balls=columns//3,
        omitted_rows=0,omitted_control_balls=0,sparse_bytes=storage,usable_direction=direction is not None,maximum_linear_model_residual=residual,maximum_actual_control_norm_excess=norm_excess,
        baseline_maximum_model_violation=float(np.maximum(-m,0).max()),predicted_maximum_model_violation=None if after is None else float(np.maximum(-after,0).max()),
        search_only_interior_reserve=1e-8,added_physical_tolerance=0.,quality_approved=False,release_approved=False,
        protected_row_indices=np.flatnonzero(protected).tolist(),protected_model_solver_reserve=1e-8 if protected.any() else 0.,
        affine_norm_constraints=balls,omitted_affine_norm_constraints=0,maximum_affine_norm_excess=affine_excess,affine_radius_search_relative_reserve=1e-8 if balls else 0.,
        scope='Complete supplied signed row minimax plus L1 movement cost, every exact normalized control-vector ball and every optional hard affine-vector norm bound. Strict output checks required; affine geometry is a local model, not nonlinear feasibility or motion approval. No clipping or omitted rows.')
    return direction,report
