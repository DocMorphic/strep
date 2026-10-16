"""Restore violated material norms without rebasing original native bounds."""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_scene_conic import solver_module


def assemble(system,jacobian,hard_rows,vectors,vector_jacobian,source_limits_m,*,reserve_m=5e-7,scale_m=.005,maximum_nonzeros=6000000):
    if (not isinstance(system,NormRows) or type(hard_rows) is not int or not 0<=hard_rows<=len(system.caps)
            or type(reserve_m) not in (int,float) or not np.isfinite(reserve_m) or not 0<=reserve_m<=.0001
            or type(scale_m) not in (int,float) or not np.isfinite(scale_m) or scale_m<=0
            or type(maximum_nonzeros) is not int or not 1<=maximum_nonzeros<=6000000):raise ValueError('Explicit complete base, bounded inward reserve and sparse budget required')
    limits=np.asarray(source_limits_m,float);vectors=np.asarray(vectors,float)
    if limits.ndim!=1 or not len(limits) or np.any(limits<reserve_m):raise ValueError('Complete original material limits must contain the inward search reserve')
    reference=NormRows(vectors,limits,np.full(len(limits),scale_m));guards=NormRows(vectors,limits-reserve_m,reference.scales)
    jac=sparse.csr_matrix(jacobian);vj=sparse.csr_matrix(vector_jacobian)
    if (not jac.shape[1] or jac.shape[0]!=system.vectors.size or vj.shape!=(vectors.size,jac.shape[1])
            or not np.isfinite(jac.data).all() or not np.isfinite(vj.data).all() or np.any(system.residual()[:hard_rows]>1e-8)):
        raise ValueError('Complete finite matrices and passing original base anchor required')
    combined=NormRows(np.r_[system.vectors[:hard_rows],guards.vectors,system.vectors[hard_rows:]],np.r_[system.caps[:hard_rows],guards.caps,system.caps[hard_rows:]],np.r_[system.scales[:hard_rows],guards.scales,system.scales[hard_rows:]])
    matrix=sparse.vstack([jac[:3*hard_rows],vj,jac[3*hard_rows:]],format='csc')
    if matrix.nnz>maximum_nonzeros:raise ValueError('Complete restoration matrix exceeds budget; no entries discarded')
    return combined,matrix,dict(original_hard_rows=hard_rows,material_vector_rows=len(limits),hard_rows=hard_rows+len(limits),total_rows=len(combined.caps),combined_nonzeros=matrix.nnz,
        original_material_limits_m=limits.tolist(),material_search_reserve_m=reserve_m,initial_reference_material_failures=int((reference.residual()>0).sum()),initial_search_material_failures=int((guards.residual()>0).sum()),
        all_original_rows_caps_scales_retained=True,infeasible_material_start_allowed=True,original_selected=True,quality_approved=False,release_approved=False,
        scope='Explicit restoration from violated material bounds. Only material search caps tighten; original base rows and reference material limits remain unchanged. Complete decoded acceptance remains necessary.')


def direction(system,jacobian,value,lower,upper,trust,*,hard_rows,precision='strict'):
    if precision not in ('strict','standard'):raise ValueError('Explicit strict or standard solver convergence required')
    if any(isinstance(v,(bool,np.bool_)) for v in np.asarray(value,dtype=object).flat):raise ValueError('Explicit numeric original controls required')
    value,lower,upper=[np.asarray(v,float) for v in (value,lower,upper)]
    if (not isinstance(system,NormRows) or value.ndim!=1 or not 1<=len(value)<=768 or lower.shape!=value.shape or upper.shape!=value.shape
            or any(not np.isfinite(v).all() for v in (value,lower,upper)) or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
            or type(hard_rows) is not int or not 1<=hard_rows<=len(system.caps) or type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=1):raise ValueError('Complete original boxes, bounded trust and hard prefix required')
    jac=sparse.csr_matrix(jacobian)
    if jac.shape!=(system.vectors.size,len(value)) or not np.isfinite(jac.data).all() or jac.nnz>6000000:raise ValueError('Complete finite bounded restoration Jacobian required')
    n=len(value);hard=NormRows(system.vectors[:hard_rows],system.caps[:hard_rows],system.scales[:hard_rows]);j=jac[:3*hard_rows].copy();j.eliminate_zeros()
    lo=np.maximum(-1.,(lower-value)/trust);hi=np.minimum(1.,(upper-value)/trust)
    counts=np.diff(j.indptr).reshape(-1,3).sum(1);initial=hard.residual();fixed=counts==0
    if not np.isfinite(initial).all():raise ValueError('Complete finite hard norm measurements required')
    meta=dict(protected_norm_rows=hard_rows,initial_failed_hard_rows=int((initial>0).sum()),soft_rows_retained_not_optimized=len(system.caps)-hard_rows,
        convergence_precision=precision,
        objective='minimum normalized control step under every hard norm',original_selected=True,quality_approved=False,release_approved=False,
        scope='Affine restoration proposal only; no nonlinear native, material, mesh, engine or quality approval.')
    if np.any(initial[fixed]>0):return None,dict(meta,status='FixedProtectedConflict')
    radius=np.asarray(abs(j)@(np.maximum(abs(lo),abs(hi))*trust)).reshape(hard.vectors.shape);upper_norm=np.linalg.norm(abs(hard.vectors)+radius,axis=1)
    reserve=64*(n+4)*np.finfo(float).eps*np.maximum.reduce([upper_norm,abs(hard.caps),np.ones(hard_rows)])
    box=(counts>0)&np.isfinite(upper_norm)&(upper_norm+reserve<=hard.caps);active=np.flatnonzero((counts>0)&~box)
    solver=solver_module();mats=[sparse.eye(n,format='csc'),-sparse.eye(n,format='csc')];rhs=[hi,-lo];cones=[solver.NonnegativeConeT(2*n)]
    if len(active):
        rows=(3*active[:,None]+np.arange(3)).ravel();derivative=j[rows].multiply((-trust/np.repeat(hard.scales[active],3))[:,None]).tocoo()
        matrix=sparse.csc_matrix((derivative.data,(4*(derivative.row//3)+1+derivative.row%3,derivative.col)),shape=(4*len(active),n))
        mats.append(matrix);rhs.append((np.c_[hard.caps[active],hard.vectors[active]]/hard.scales[active,None]).ravel());cones.extend(solver.SecondOrderConeT(4) for _ in active)
    settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-11 if precision=='strict' else 1e-9
    settings.reduced_tol_gap_abs=settings.reduced_tol_gap_rel=settings.reduced_tol_feas=1e-10 if precision=='strict' else 1e-8
    if hasattr(settings,'max_threads'):settings.max_threads=1
    matrix=sparse.vstack(mats,format='csc');bound=np.concatenate(rhs)
    if not np.isfinite(matrix.data).all() or not np.isfinite(bound).all():raise ValueError('Finite scaled restoration cones required')
    answer=solver.DefaultSolver(sparse.eye(n,format='csc'),np.zeros(n),matrix,bound,cones,settings).solve()
    meta.update(status=str(answer.status),iterations=answer.iterations,active_cones=len(active),omitted_fixed_passing_rows=int(fixed.sum()),omitted_affine_box_passing_rows=int(box.sum()),solver_version=solver.__version__)
    raw=np.asarray(answer.x,float)
    if raw.shape!=(n,) or not np.isfinite(raw).all():return None,dict(meta,invalid_solution=True)
    step=raw*trust;boxed=np.clip(step,lo*trust,hi*trust);residual=system.residual(jac,boxed)
    if not np.isfinite(residual).all():return None,dict(meta,proposed_step=boxed.tolist(),affine_hard_rows_pass=False,nonfinite_affine_rows=True)
    passed=bool(np.all(step>=lo*trust-1e-9) and np.all(step<=hi*trust+1e-9) and np.all(residual[:hard_rows]<=1e-8))
    meta.update(proposed_step=boxed.tolist(),affine_hard_rows_pass=passed,maximum_normalized_hard_excess=float(residual[:hard_rows].max()),failed_hard_rows=int((residual[:hard_rows]>1e-8).sum()))
    return (boxed if passed and str(answer.status) in ('Solved','AlmostSolved') else None),meta
