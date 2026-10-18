"""Equivalent exact-constant affine hinge and hard-row representation.

Every original row has an occurrence map or explicit constant value. Constant
hinges remain in the full cost offset; constant hard rows retain their strongest
conjunction. No near-zero cutoff, approximate rank test or physical approval.
"""
import numpy as np
from scipy import sparse

MAXIMUM_BYTES=64*1024**2


def factor_affine_constants(margins,jacobian,hard_matrix,hard_upper,*,maximum_model_violation=None,maximum_working_bytes=MAXIMUM_BYTES):
    g=np.asarray(margins);j=np.asarray(jacobian);u=np.asarray(hard_upper)
    if (j.ndim!=2 or not 1<=j.shape[0]<=8192 or not 1<=j.shape[1]<=768 or g.shape!=(j.shape[0],)
            or u.ndim!=1 or len(u)>65536 or any(a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all() for a in [g,j,u])
            or np.any(np.abs(g)>1e6)):
        raise ValueError('Complete bounded finite original objective and hard bounds required')
    rows,columns=j.shape
    if (not sparse.issparse(hard_matrix) or hard_matrix.format not in ('csr','csc') or hard_matrix.shape!=(len(u),columns)
            or hard_matrix.data.dtype.kind not in 'fiu' or hard_matrix.data.dtype.itemsize>8 or not np.isfinite(hard_matrix.data).all()):
        raise ValueError('Complete matching finite original CSR/CSC hard matrix required')
    if type(maximum_working_bytes) is not int or not 1<=maximum_working_bytes<=MAXIMUM_BYTES:raise ValueError('Explicit complete workspace budget required')
    if maximum_model_violation is not None and (type(maximum_model_violation) not in (int,float) or not np.isfinite(maximum_model_violation) or not 0<=maximum_model_violation<=1e6):
        raise ValueError('Original finite bounded peak ceiling required')
    input_bytes=8*(g.size+j.size+u.size+hard_matrix.data.size)+hard_matrix.indices.nbytes+hard_matrix.indptr.nbytes
    estimate=3*input_bytes+8*(12*rows+20*len(u)+2*columns)
    if estimate>maximum_working_bytes:raise ValueError('Complete input/factor/occurrence workspace exceeds budget; no rows or columns removed')
    g=g.astype(float,copy=True);j=j.astype(float,copy=True);u=u.astype(float,copy=True)
    raw=hard_matrix.astype(float,copy=True);raw.check_format(full_check=True)
    if not raw.has_canonical_format:raise ValueError('Canonical distinct sparse coefficients required; use original solver canonicalization first')
    h=raw.tocsr(copy=True);h.eliminate_zeros();h.sort_indices()
    constant_objective=~np.any(j!=0,axis=1);constant_hard=np.diff(h.indptr)==0
    objective_rows=np.flatnonzero(~constant_objective);fixed_objective=np.flatnonzero(constant_objective)
    changing=np.flatnonzero(~constant_hard);fixed_hard=np.flatnonzero(constant_hard)
    objective_map=np.full(rows,-1,dtype=np.int64);objective_map[objective_rows]=np.arange(len(objective_rows))
    representative=None if not len(fixed_hard) else int(fixed_hard[int(np.argmin(u[fixed_hard]))])
    retained=np.r_[changing,representative].astype(np.int64) if representative is not None else changing.astype(np.int64)
    hard_map=np.empty(len(u),dtype=np.int64);hard_map[changing]=np.arange(len(changing))
    if len(fixed_hard):hard_map[fixed_hard]=len(changing)
    offset=float(np.maximum(-g[fixed_objective],0).sum());constant_peak=float(np.maximum(-g[fixed_objective],0).max()) if len(fixed_objective) else 0.
    constant_hard_excess=None if not len(fixed_hard) else float(-u[fixed_hard].min())
    return dict(margins=g[objective_rows].copy(),jacobian=j[objective_rows].copy(),hard_matrix=h[retained].tocsr(),hard_upper=u[retained].copy(),
        objective_original_rows=objective_rows,constant_objective_rows=fixed_objective,constant_objective_margins=g[fixed_objective].copy(),original_objective_to_factor=objective_map,
        hard_original_rows=retained,constant_hard_rows=fixed_hard,constant_hard_upper=u[fixed_hard].copy(),original_hard_to_factor=hard_map,
        constant_hinge_offset=offset,constant_maximum_violation=constant_peak,
        report=dict(schema='strep-native-constant-affine-factor-v1',columns=columns,original_objectives=rows,responsive_objectives=len(objective_rows),constant_objectives=len(fixed_objective),
            all_objectives_constant=not len(objective_rows),constant_hinge_offset=offset,constant_maximum_violation=constant_peak,
            original_hard_rows=len(u),factor_hard_rows=len(retained),nonconstant_hard_rows=len(changing),constant_hard_rows=len(fixed_hard),
            constant_hard_representative_original_row=representative,maximum_constant_hard_residual=constant_hard_excess,
            constant_hard_conditions_pass=constant_hard_excess is None or constant_hard_excess<=0,
            original_peak_ceiling=maximum_model_violation,constant_peak_conditions_pass=maximum_model_violation is None or constant_peak<=maximum_model_violation,
            all_original_rows_accounted=True,exact_zero_coefficients_only=True,control_columns_unchanged=True,estimated_working_array_bytes=int(estimate),maximum_working_bytes=maximum_working_bytes,
            quality_approved=False,release_approved=False,
            scope='Equivalent complete float64 affine model: responsive hinge rows plus explicit original constant values/cost offset, and every nonconstant hard row plus the strongest exact constant conjunction. '
                  'All original row maps retained. No normalization, near-zero cutoff, variable removal, physical tolerance or permission change. '
                  'Caller retains original arrays and must recheck full original costs/peak, every hard/norm/box bound, then raw/saved motion, scene and human gates. Zero affine coefficients never prove nonlinear invariance.'))
