"""Checked optional origin proposal for explicitly objective-null coordinates.

The full control domain remains unchanged. A valid initial point is required;
every original affine norm, hard row and box bound is checked again. No clipping
or near-zero threshold. Nonlinear motion and geometry still require validation.
"""
import numpy as np
from scipy import sparse

MAXIMUM_BYTES=64*1024**2


def reset_objective_null_block(margins,jacobian,lower,upper,vectors,norm_matrix,radii,proposal,columns,*,extra_matrix=None,extra_upper=None,maximum_working_bytes=MAXIMUM_BYTES):
    g,j,lo,hi,v,r,p=[np.asarray(a) for a in (margins,jacobian,lower,upper,vectors,radii,proposal)]
    if (j.ndim!=2 or not 1<=j.shape[0]<=8192 or not 1<=j.shape[1]<=768 or g.shape!=(j.shape[0],)
            or any(a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all() for a in [g,j,lo,hi,v,r,p])):
        raise ValueError('Complete finite bounded objective and original model arrays required')
    n=j.shape[1]
    if (lo.shape!=(n,) or hi.shape!=(n,) or p.shape!=(n,) or np.any(lo>hi) or np.any(np.abs(lo)>1e6) or np.any(np.abs(hi)>1e6)
            or v.ndim!=2 or v.shape[1]!=3 or not 1<=len(v)<=131072 or r.shape!=(len(v),) or np.any(r<=0) or np.any(r>1e6) or np.any(np.abs(v)>1e12)):
        raise ValueError('Complete original control box, norm population and positive original radii required')
    if (not isinstance(columns,list) or not columns or any(type(c) is not int or not 0<=c<n for c in columns) or len(set(columns))!=len(columns)):
        raise ValueError('Explicit distinct existing objective-null columns required')
    if np.any(j[:,columns]!=0):raise ValueError('Every named primary objective column must be exactly zero')
    if (extra_matrix is None)!=(extra_upper is None):raise ValueError('Complete hard-row matrix/bound pair required')
    raw_h=sparse.csr_matrix((0,n)) if extra_matrix is None else extra_matrix
    h=np.empty(0) if extra_upper is None else np.asarray(extra_upper)
    if h.ndim!=1 or h.dtype.kind not in 'fiu' or h.dtype.itemsize>8 or not np.isfinite(h).all() or len(h)>65536:
        raise ValueError('Complete finite bounded hard-row upper values required')
    for m,shape in [(norm_matrix,(3*len(v),n)),(raw_h,(len(h),n))]:
        if (not sparse.issparse(m) or m.format not in ('csr','csc') or m.shape!=shape or m.data.dtype.kind not in 'fiu' or m.data.dtype.itemsize>8 or not np.isfinite(m.data).all()):
            raise ValueError('Complete matching finite CSR/CSC matrices required')
    if type(maximum_working_bytes) is not int or not 1<=maximum_working_bytes<=MAXIMUM_BYTES:raise ValueError('Explicit complete workspace budget required')
    input_bytes=sum(a.size*8 for a in [g,j,lo,hi,v,r,p,h])+sum(m.data.size*8+m.indices.nbytes+m.indptr.nbytes for m in [norm_matrix,raw_h])
    estimated=3*input_bytes+8*(12*len(v)+2*len(h)+6*len(g)+5*n)
    if estimated>maximum_working_bytes:raise ValueError('Whole original input/check workspace exceeds budget; no rows/columns removed')
    g,j,lo,hi,v,r,p,h=[a.astype(float,copy=True) for a in [g,j,lo,hi,v,r,p,h]]
    m=sparse.csr_matrix(norm_matrix,dtype=float,copy=True);hard=sparse.csr_matrix(raw_h,dtype=float,copy=True)
    for matrix in [m,hard]:
        matrix.check_format(full_check=True);matrix.sum_duplicates();matrix.eliminate_zeros()
        if not np.isfinite(matrix.data).all():raise ValueError('Summed original sparse coefficients must stay finite')
    def measured(point):
        with np.errstate(over='ignore',invalid='ignore'):
            norms=np.linalg.norm(v+(m@point).reshape(-1,3),axis=1)-r;cuts=hard@point-h;predicted=g+j@point
        if not all(np.isfinite(a).all() for a in [norms,cuts,predicted]):raise ValueError('Nonfinite complete original model evaluation')
        norm=float(norms.max());cut=float(cuts.max()) if len(cuts) else 0.;box=float(max((lo-point).max(),(point-hi).max()))
        return dict(maximum_norm_excess=norm,maximum_hard_residual=cut,maximum_box_excess=box,strict_feasible=bool(norm<=0 and cut<=0 and box<=0),l1=float(np.abs(point).sum())),predicted
    before,primary_before=measured(p)
    if not before['strict_feasible']:raise ValueError('Initial proposal must already pass every original norm, hard row and box; no invalid-point rescue')
    candidate=p.copy();candidate[columns]=0.;after,primary_after=measured(candidate)
    unchanged=bool(np.array_equal(primary_before,primary_after))
    accepted=bool(unchanged and after['strict_feasible'] and after['l1']<before['l1'])
    return dict(proposal=candidate.copy() if accepted else None,report=dict(schema='strep-native-objective-null-reset-v1',columns=n,reset_columns=columns.copy(),objective_rows=len(g),
        original_norms=len(v),original_hard_rows=len(h),before=before,after=after,primary_affine_values_unchanged=unchanged,l1_reduction=before['l1']-after['l1'],accepted=accepted,
        exact_objective_null_columns=True,all_original_constraints_rechecked=True,estimated_working_array_bytes=int(estimated),maximum_working_bytes=maximum_working_bytes,
        control_domain_unchanged=True,reference_origin_target=0.,coordinate_clipping=False,nonlinear_invariance_claimed=False,quality_approved=False,release_approved=False,
        scope='Optional explicit secondary origin proposal in the same full control domain. Every named primary affine column is exactly zero; unchanged full primary values, lower L1 and strict complete original norm/hard/box bounds required. '
              'No solver optimum, nonlinear invariance, saved-body identity, geometry or motion-quality claim. Caller must validate actual raw/saved motion, contacts and scene geometry before adopting.'))
