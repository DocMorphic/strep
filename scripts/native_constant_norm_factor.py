"""Factor exact constant affine norm constraints without losing witnesses.

The largest original-unit constant excess represents their conjunction. Every
original row maps to its retained cone; no small-Jacobian cutoff is used.
This is an affine-model equivalence, never nonlinear or saved-motion approval.
"""
import numpy as np
from scipy import sparse

MAXIMUM_BYTES=64*1024**2


def factor_constant_norms(vectors,matrix,radii,*,maximum_working_bytes=MAXIMUM_BYTES,maximum_output_norms=65536):
    v=np.asarray(vectors);r=np.asarray(radii)
    if (v.ndim!=2 or v.shape[1]!=3 or not 1<=len(v)<=131072 or r.shape!=(len(v),)
            or any(a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all() for a in [v,r])
            or np.any(np.abs(v)>1e12) or np.any(r<=0) or np.any(r>1e6)):
        raise ValueError('Complete bounded finite three-vectors and positive original radii required')
    if (not sparse.issparse(matrix) or matrix.format not in ('csr','csc') or len(matrix.shape)!=2 or matrix.shape[0]!=3*len(v)
            or not 1<=matrix.shape[1]<=768 or matrix.data.ndim!=1
            or matrix.data.dtype.kind not in 'fiu' or matrix.data.dtype.itemsize>8 or not np.isfinite(matrix.data).all()):
        raise ValueError('Complete finite CSR/CSC norm matrix with every declared column required')
    if (type(maximum_working_bytes) is not int or not 1<=maximum_working_bytes<=MAXIMUM_BYTES
            or type(maximum_output_norms) is not int or not 1<=maximum_output_norms<=65536):
        raise ValueError('Explicit complete working and solver-cone budgets required')
    rows,cols=matrix.shape;outer,inner=(rows,cols) if matrix.format=='csr' else (cols,rows)
    ptr=matrix.indptr;indices=matrix.indices
    if (ptr.shape!=(outer+1,) or indices.ndim!=1 or len(indices)!=len(matrix.data)
            or ptr.dtype.kind not in 'iu' or indices.dtype.kind not in 'iu'
            or ptr.dtype.itemsize>8 or indices.dtype.itemsize>8 or ptr[0]!=0 or ptr[-1]!=len(indices)
            or np.any(ptr[1:]<ptr[:-1]) or np.any(indices<0) or np.any(indices>=inner)):
        raise ValueError('Complete valid sparse storage required before canonical copying')
    input_bytes=(v.size+r.size+matrix.data.size)*8+ptr.nbytes+indices.nbytes
    estimated=3*input_bytes+len(v)*128+cols*8
    if estimated>maximum_working_bytes:raise ValueError('Complete input/canonical/factor workspace exceeds budget; no population removed')
    original=v.astype(float,copy=True);radius=r.astype(float,copy=True)
    canonical=sparse.csr_matrix(matrix,dtype=float,copy=True);canonical.sum_duplicates();canonical.eliminate_zeros();canonical.sort_indices()
    if not np.isfinite(canonical.data).all():raise ValueError('Summed sparse coefficients must remain finite')
    constant=np.sum(np.diff(canonical.indptr).reshape(len(v),3),axis=1)==0
    changing=np.flatnonzero(~constant);fixed=np.flatnonzero(constant)
    output_count=len(changing)+bool(len(fixed))
    if output_count>maximum_output_norms:raise ValueError('Every nonconstant cone plus constant conjunction exceeds solver budget')
    representative=None;maximum_excess=None;constant_pass=True
    if len(fixed):
        excess=np.linalg.norm(original[fixed],axis=1)-radius[fixed]
        representative=int(fixed[int(np.argmax(excess))]);maximum_excess=float(np.max(excess));constant_pass=bool(maximum_excess<=0)
    retained=np.r_[changing,representative].astype(np.int64) if representative is not None else changing.astype(np.int64)
    mapping=np.empty(len(v),dtype=np.int64);mapping[changing]=np.arange(len(changing))
    if len(fixed):mapping[fixed]=len(changing)
    selected=(retained[:,None]*3+np.arange(3)).ravel()
    return dict(vectors=original[retained].copy(),matrix=canonical[selected].tocsr(),radii=radius[retained].copy(),
        original_to_factor=mapping,retained_original_rows=retained,constant_original_rows=fixed,
        report=dict(schema='strep-native-constant-norm-factor-v1',original_norms=len(v),factor_norms=len(retained),columns=cols,
            constant_norms=len(fixed),nonconstant_norms=len(changing),constant_representative_original_row=representative,
            maximum_original_unit_constant_excess=maximum_excess,all_constant_cones_pass=constant_pass,
            estimated_working_array_bytes=int(estimated),maximum_working_bytes=maximum_working_bytes,
            exact_zero_coefficients_only=True,all_original_rows_mapped=True,original_radii_unchanged=True,
            quality_approved=False,release_approved=False,
            scope='Equivalent complete affine norm system: every nonconstant cone retained and all exact constant cones represented by the largest original-unit norm excess. '
                  'No normalization, near-zero cutoff, clipping, row selection by motion error, or nonlinear invariance claim. '
                  'Caller retains original vectors/matrix/radii and must recheck every original norm at the proposed direction, then all raw/saved motion/scene/engine/human gates.'))
