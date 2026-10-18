"""Complete bounded peak/L1 proposals with sparse affine norm constraints.

One shared peak variable replaces per-row hinge variables. No row reduction,
pose clipping, nonlinear acceptance or optimality certificate is provided.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module

MAXIMUM_BYTES=64*1024**2


def _storage(matrix):
    return matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes


def _real(value):
    a=np.asarray(value)
    if a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all() or np.any(a>1e6) or np.any(a< -1e6):
        raise ValueError('Complete finite bounded real arrays up to Float64 required')
    return np.array(a,dtype=float,copy=True)


def peak_step(margins,jacobian,lower_delta,upper_delta,norm_vectors,norm_matrix,norm_radii,*,
              extra_matrix=None,extra_upper=None,l1_penalty=1e-5,solver_box_reserve=1e-9,
              solver_norm_reserve=0.,solver_cut_reserve=0.,
              maximum_bytes=MAXIMUM_BYTES,time_limit_seconds=20.,maximum_iterations=200):
    j=np.asarray(jacobian);m=np.asarray(margins);lo=np.asarray(lower_delta);hi=np.asarray(upper_delta);v=np.asarray(norm_vectors);r=np.asarray(norm_radii)
    if j.ndim!=2 or not 1<=j.shape[0]<=8192 or not 1<=j.shape[1]<=384 or j.dtype.kind not in 'fiu' or j.dtype.itemsize>8:
        raise ValueError('Every complete bounded model row and control column required')
    rows,columns=j.shape
    if m.shape!=(rows,) or lo.shape!=(columns,) or hi.shape!=(columns,) or v.ndim!=2 or v.shape[1:]!=(3,) or not 1<=len(v)<=8192 or r.shape!=(len(v),):
        raise ValueError('Complete margins, boxes and affine three-vector norms required')
    balls=len(v)
    if not sparse.issparse(norm_matrix) or norm_matrix.format not in ('csr','csc') or norm_matrix.shape!=(3*balls,columns):
        raise ValueError('Complete CSR/CSC norm matrix required')
    if (extra_matrix is None)!=(extra_upper is None):raise ValueError('Complete extra hard matrix/upper pair required')
    cuts=sparse.csr_matrix((0,columns)) if extra_matrix is None else extra_matrix
    upper=np.empty(0) if extra_upper is None else np.asarray(extra_upper)
    if not sparse.issparse(cuts) or cuts.format not in ('csr','csc') or cuts.ndim!=2 or cuts.shape[1]!=columns or not 0<=cuts.shape[0]<=8192 or upper.shape!=(cuts.shape[0],):
        raise ValueError('Every complete CSR/CSC extra hard row required')
    cut_rows=cuts.shape[0]
    if type(maximum_bytes) is not int or not 1<=maximum_bytes<=MAXIMUM_BYTES:raise ValueError('Complete allocation allowance up to64MiB required')
    if type(l1_penalty) not in (int,float) or not np.isfinite(l1_penalty) or not 1e-12<=l1_penalty<=1:raise ValueError('Positive bounded movement penalty required')
    if type(solver_box_reserve) not in (int,float) or not np.isfinite(solver_box_reserve) or not 0<=solver_box_reserve<=1e-5:raise ValueError('Explicit bounded numerical box interior required')
    for reserve in [solver_norm_reserve,solver_cut_reserve]:
        if type(reserve) not in (int,float) or not np.isfinite(reserve) or not 0<=reserve<=1e-5:raise ValueError('Explicit bounded numerical norm/cut interiors required')
    if type(time_limit_seconds) not in (int,float) or not np.isfinite(time_limit_seconds) or not .01<=time_limit_seconds<=60 or type(maximum_iterations) is not int or not 1<=maximum_iterations<=10000:
        raise ValueError('Explicit bounded solver time and iteration limits required')
    raw_bytes=sum(a.nbytes for a in [j,m,lo,hi,v,r,upper])+_storage(norm_matrix)+_storage(cuts)
    scalar_copy_bytes=sum(a.size for a in [m,lo,hi,v,r,upper])*8
    sparse_copy_bytes=sum(a.data.size*8+a.indices.nbytes+a.indptr.nbytes for a in [norm_matrix,cuts])
    preparation_scratch=128*columns*32+max(rows,columns,3*balls,cut_rows)*32
    if raw_bytes+scalar_copy_bytes+2*sparse_copy_bytes+preparation_scratch>maximum_bytes:raise ValueError('Complete peak-model input allowance exceeded; no truncation')
    m,lo,hi,v,r,upper=[_real(a) for a in [m,lo,hi,v,r,upper]]
    if np.any(lo>0) or np.any(hi<0) or np.any(lo>hi) or np.any(lo< -2) or np.any(hi>2) or np.any(r<1e-12):
        raise ValueError('Original bounded boxes containing zero and positive norm radii required')
    owned=[]
    for matrix in [norm_matrix,cuts]:
        if matrix.data.dtype.kind not in 'fiu' or matrix.data.dtype.itemsize>8:raise ValueError('Finite real sparse coefficients up to Float64 required')
        value=sparse.csr_matrix(matrix,dtype=float,copy=True);value.check_format(full_check=True);value.sum_duplicates();value.eliminate_zeros()
        for first in range(0,len(value.data),1024):
            block=value.data[first:first+1024]
            if not np.isfinite(block).all() or np.any(abs(block)>1e6):raise ValueError('Finite summed sparse coefficients required')
        owned.append(value)
    transform,cuts=owned;owned_bytes=sum(_storage(a) for a in owned)
    nonzero=0;chunk_rows=128
    for first in range(0,rows,chunk_rows):
        block=j[first:first+chunk_rows]
        if not np.isfinite(block).all() or np.any(block>1e6) or np.any(block< -1e6):raise ValueError('Every finite bounded model row required')
        nonzero+=int(np.count_nonzero(block))
    variables=2*columns+1;linear_rows=rows+4*columns+1+cut_rows;matrix_rows=linear_rows+4*balls
    entries=nonzero+rows+6*columns+1+cuts.nnz+transform.nnz
    # Input ownership, COO triplets, final CSC, bounds and bounded emit scratch
    # coexist during assembly. Solver-owned factorization is separately guarded.
    scratch=max(min(chunk_rows,rows)*columns*32,min(128*columns,max(cuts.nnz,transform.nnz))*64)+max(rows,columns,3*balls,cut_rows)*32
    estimated=raw_bytes+scalar_copy_bytes+owned_bytes+entries*44+(variables+1)*4+matrix_rows*8+scratch
    if estimated>maximum_bytes:raise ValueError('Complete peak assembly allowance exceeded before allocation; no rows/columns truncated')
    data=np.empty(entries);row_ids=np.empty(entries,dtype=np.int32);col_ids=np.empty(entries,dtype=np.int32);cursor=0
    def emit(values,rr,cc):
        nonlocal cursor
        count=len(values);assert cursor+count<=entries;data[cursor:cursor+count]=values;row_ids[cursor:cursor+count]=rr;col_ids[cursor:cursor+count]=cc;cursor+=count
    for first in range(0,rows,chunk_rows):
        block=j[first:first+chunk_rows];rr,cc=np.nonzero(block);values=np.array(block[rr,cc],dtype=float,copy=True);values*=-1;emit(values,rr+first,cc)
    emit(-np.ones(rows),np.arange(rows),np.full(rows,2*columns))
    ids=np.arange(columns);offset=rows
    emit(np.ones(columns),offset+ids,ids);emit(-np.ones(columns),offset+ids,columns+ids)
    emit(-np.ones(columns),offset+columns+ids,ids);emit(-np.ones(columns),offset+columns+ids,columns+ids)
    emit(np.ones(columns),offset+2*columns+ids,ids);emit(-np.ones(columns),offset+3*columns+ids,ids)
    emit(np.array([-1.]),np.array([offset+4*columns]),np.array([2*columns]))
    for matrix,start,is_norm in [(cuts,rows+4*columns+1,False),(transform,linear_rows,True)]:
        for first in range(0,matrix.shape[0],128):
            local=matrix[first:first+128].tocoo();rr=local.row+first;rr=4*(rr//3)+1+rr%3 if is_norm else rr
            emit(-local.data if is_norm else local.data,rr+start,local.col)
    assert cursor==entries
    matrix=sparse.coo_matrix((data,(row_ids,col_ids)),shape=(matrix_rows,variables)).tocsc();matrix.sum_duplicates();matrix.eliminate_zeros()
    del data,row_ids,col_ids
    solve_lo=np.minimum(0.,lo+solver_box_reserve);solve_hi=np.maximum(0.,hi-solver_box_reserve)
    cut_norms=np.empty(cut_rows)
    for row in range(cut_rows):cut_norms[row]=np.linalg.norm(cuts.data[cuts.indptr[row]:cuts.indptr[row+1]])
    solve_upper=upper-float(solver_cut_reserve)*cut_norms;solve_radii=r*(1-float(solver_norm_reserve))
    bound=np.r_[m,np.zeros(2*columns),solve_hi,-solve_lo,0.,solve_upper,np.c_[solve_radii,v].ravel()];assert bound.shape==(matrix_rows,)
    solver=solver_module();settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=maximum_iterations;settings.time_limit=float(time_limit_seconds);settings.tol_gap_abs=settings.tol_gap_rel=1e-10;settings.tol_feas=1e-12
    if hasattr(settings,'max_threads'):settings.max_threads=1
    cones=[solver.NonnegativeConeT(linear_rows)]+[solver.SecondOrderConeT(4) for _ in range(balls)]
    cost=np.r_[np.zeros(columns),np.full(columns,l1_penalty),1.];fit=solver.DefaultSolver(sparse.csc_matrix((variables,variables)),cost,matrix,bound,cones,settings).solve()
    point=np.asarray(fit.x,dtype=float);direction=None;peak=None;checks=None;valid_point=point.shape==(variables,) and np.isfinite(point).all()
    if str(fit.status) in ('Solved','AlmostSolved') and valid_point:
        delta=point[:columns];after=m+j@delta;norms=np.linalg.norm(v+(transform@delta).reshape(-1,3),axis=1)
        checks=dict(original_boxes_pass=bool(np.all(delta>=lo) and np.all(delta<=hi)),all_norm_constraints_pass=bool(np.all(norms<=r)),all_hard_rows_pass=bool(np.all(cuts@delta<=upper)))
        if all(checks.values()):direction=delta.copy();peak=float(np.maximum(-after,0).max())
    report=dict(schema='strep-conic-peak-step-v1',solver_status=str(fit.status),solver_version=solver.__version__,iterations=fit.iterations,model_rows=rows,complete_columns=columns,variables=variables,shared_peak_variables=1,per_row_deficit_variables=0,hard_rows=cut_rows,norm_constraints=balls,matrix_rows=matrix_rows,matrix_nonzeros=matrix.nnz,sparse_matrix_bytes=_storage(matrix),estimated_complete_assembly_bytes=int(estimated),maximum_bytes=maximum_bytes,usable_direction=direction is not None,strict_admission=checks,baseline_peak_deficit=float(np.maximum(-m,0).max()),predicted_peak_deficit=peak,solver_peak=None if not valid_point else float(point[-1]),solver_box_reserve=solver_box_reserve,solver_norm_reserve=solver_norm_reserve,solver_cut_reserve=solver_cut_reserve,admission_uses_unshrunk_original_bounds=True,auxiliary_peak_recomputed_without_pose_clipping=True,omitted_rows=0,omitted_columns=0,physical_tolerance_added=0.,optimality_certified=False,nonlinear_checked=False,quality_approved=False,release_approved=False)
    return direction,report
