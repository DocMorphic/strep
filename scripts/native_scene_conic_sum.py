"""Sum positive soft norm excess; original hard vector norms remain intact."""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module


def direction(system,jacobian,value,lower,upper,trust,*,hard_rows=0,maximum_soft_rows=100000):
    value,lower,upper=[np.asarray(v,float) for v in (value,lower,upper)]
    jac=sparse.csr_matrix(jacobian);n=len(value) if value.ndim==1 else 0;rows=len(system.caps)
    if (not n or lower.shape!=value.shape or upper.shape!=value.shape or jac.shape!=(3*rows,n)
            or any(not np.isfinite(v).all() for v in (value,lower,upper,jac.data))
            or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
            or type(trust) not in (int,float) or not np.isfinite(trust) or trust<=0
            or type(hard_rows) is not int or not 0<=hard_rows<=rows
            or type(maximum_soft_rows) is not int or not 1<=maximum_soft_rows<=100000):
        raise ValueError('Complete finite sparse norm model, original boxes and bounded soft population required')
    jac.eliminate_zeros();counts=np.diff(jac.indptr).reshape(rows,3);responsive=counts.sum(1)>0
    lo=np.maximum(-1.,(lower-value)/trust);hi=np.minimum(1.,(upper-value)/trust)
    radius=np.asarray(abs(jac)@(np.maximum(abs(lo),abs(hi))*trust)).reshape(rows,3)
    bound=np.linalg.norm(abs(system.vectors)+radius,axis=1)
    reserve=64*(n+4)*np.finfo(float).eps*np.maximum.reduce([bound,abs(system.caps),np.ones(rows)])
    passing=responsive&np.isfinite(bound)&(bound+reserve<=system.caps)
    residual=system.residual();fixed=~responsive
    if np.any((residual[:hard_rows]>0)&fixed[:hard_rows]):
        return None,dict(status='FixedProtectedConflict',protected_norm_rows=hard_rows)
    active=np.flatnonzero(responsive&~passing);hard=active[active<hard_rows];soft=active[active>=hard_rows];k=len(soft)
    if k>maximum_soft_rows:raise ValueError('Complete responsive soft population exceeds budget; no subset returned')
    solver=solver_module();width=n+k
    mats=[sparse.hstack([sparse.eye(n),sparse.csc_matrix((n,k))]),sparse.hstack([-sparse.eye(n),sparse.csc_matrix((n,k))])]
    rhs=[hi,-lo]
    if k:mats.append(sparse.hstack([sparse.csc_matrix((k,n)),-sparse.eye(k)]));rhs.append(np.zeros(k))
    cones=[solver.NonnegativeConeT(2*n+k)]
    scalar=(np.all(system.vectors[soft,1:]==0,axis=1)&(counts[soft,1:].sum(1)==0))
    scalar_ids=soft[scalar];scalar_aux=np.flatnonzero(scalar)
    if len(scalar_ids):
        derivative=jac[3*scalar_ids].multiply((trust/system.scales[scalar_ids])[:,None])
        auxiliary=sparse.csc_matrix((-np.ones(len(scalar_ids)),(np.arange(len(scalar_ids)),scalar_aux)),shape=(len(scalar_ids),k))
        mats.extend([sparse.hstack([derivative,auxiliary]),sparse.hstack([-derivative,auxiliary])])
        rhs.extend([(system.caps[scalar_ids]-system.vectors[scalar_ids,0])/system.scales[scalar_ids],(system.caps[scalar_ids]+system.vectors[scalar_ids,0])/system.scales[scalar_ids]])
        cones.append(solver.NonnegativeConeT(2*len(scalar_ids)))
    vector_soft=soft[~scalar];vector_aux=np.flatnonzero(~scalar)
    for ids,aux in ((hard,None),(vector_soft,vector_aux)):
        if not len(ids):continue
        selected=(3*ids[:,None]+np.arange(3)).ravel();derivative=jac[selected].multiply((-trust/np.repeat(system.scales[ids],3))[:,None]).tocoo()
        rr=4*(derivative.row//3)+1+derivative.row%3;cc=derivative.col;dd=derivative.data
        if aux is not None:rr=np.r_[rr,4*np.arange(len(ids))];cc=np.r_[cc,n+aux];dd=np.r_[dd,-np.ones(len(ids))]
        mats.append(sparse.csc_matrix((dd,(rr,cc)),shape=(4*len(ids),width)))
        rhs.append((np.c_[system.caps[ids],system.vectors[ids]]/system.scales[ids,None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in ids)
    matrix=sparse.vstack(mats,format='csc');b=np.concatenate(rhs)
    objective=np.r_[np.zeros(n),np.full(k,1/max(1,k))]
    quadratic=sparse.csc_matrix((width,width)) if k else sparse.diags(np.ones(n),format='csc')
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-9
    if hasattr(settings,'max_threads'):settings.max_threads=1
    solution=solver.DefaultSolver(quadratic,objective,matrix,b,cones,settings).solve()
    info=dict(status=str(solution.status),iterations=solution.iterations,solver_version=solver.__version__,
        norm_rows=rows,protected_norm_rows=hard_rows,responsive_soft_rows=k,scalar_soft_rows=len(scalar_ids),vector_soft_rows=len(vector_soft),
        fixed_soft_positive_sum=float(np.maximum(residual[hard_rows:][fixed[hard_rows:]],0).sum()),
        omitted_fixed_rows=int(fixed.sum()),omitted_affine_box_passing_rows=int(passing.sum()),
        soft_objective_policy='sum_positive_normalized_excess',variables=width,conic_rows=matrix.shape[0],matrix_nonzeros=matrix.nnz,
        scope='Affine sum-of-positive-excess proposal only. Hard norm caps unchanged; decoded acceptance remains required.')
    if info['status'] not in ('Solved','AlmostSolved'):return None,info
    point=np.asarray(solution.x)
    if point.shape!=(width,) or not np.isfinite(point).all() or np.any(point[:n]<lo-1e-9) or np.any(point[:n]>hi+1e-9):return None,dict(info,invalid_solution=True)
    delta=np.clip(value+trust*point[:n],lower,upper)-value;after=system.residual(jac,delta)
    info.update(maximum_control_step=float(abs(delta).max()),affine_hard_rows_pass=bool(np.all(after[:hard_rows]<=1e-8)),
        affine_positive_soft_sum=float(np.maximum(after[hard_rows:],0).sum()),affine_worst_soft_excess=float(max(0.,after[hard_rows:].max())) if hard_rows<rows else 0.)
    return delta,info
