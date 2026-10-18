"""Complete exact-equal stored-row conflicts for projection proposal guides.

Guard A*x <= upper and repair B*x >= lower contradict when A and B
contain exactly equal finite stored coefficients and lower > upper. This
diagnoses a supplied linear proposal only, never scene/action infeasibility.
It does not remove guards, choose branches, or change physical permissions.
"""
import numpy as np

MAXIMUM_BYTES=64*1024**2
MAXIMUM_PAIR_CHECKS=1048576
MAXIMUM_MATCHES=16384


def find_equal_row_conflicts(guard_matrix,guard_upper,repair_matrix,repair_lower,*,
                            maximum_pair_checks=MAXIMUM_PAIR_CHECKS,
                            maximum_matches=MAXIMUM_MATCHES,
                            maximum_working_bytes=MAXIMUM_BYTES):
    """Retain all matching row identities and compare EVERY supplied column.

    Explicit numpy arrays allow shape/budget admission before conversion.
    Exact equality includes signed zero. No near-equality/proportional-row
    search is performed, so an empty result is not a feasibility finding.
    Output order is repair row, then guard row. Duplicates remain distinct.
    """
    for value,limit in [(maximum_pair_checks,MAXIMUM_PAIR_CHECKS),(maximum_matches,MAXIMUM_MATCHES),(maximum_working_bytes,MAXIMUM_BYTES)]:
        if type(value) is not int or not 1<=value<=limit:raise ValueError('Explicit positive bounded complete comparison/output/workspace budgets required')
    arrays=(guard_matrix,guard_upper,repair_matrix,repair_lower)
    if any(not isinstance(a,np.ndarray) or a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 for a in arrays):raise ValueError('Explicit finite real numpy arrays required')
    g,u,r,l=arrays
    if g.ndim!=2 or r.ndim!=2 or not 1<=g.shape[1]<=768 or r.shape[1]!=g.shape[1] or not 0<=len(g)<=8192 or not 0<=len(r)<=8192:raise ValueError('Complete bounded matching row/column matrices required')
    if u.shape!=(len(g),) or l.shape!=(len(r),):raise ValueError('One complete bound per supplied row required')
    checks=len(g)*len(r)
    if checks>maximum_pair_checks:raise ValueError('Complete row-pair population exceeds comparison budget; no rows dropped')
    # Owned float64 inputs, full boolean comparison block, output admission,
    # row validation/conversion temporaries and vector indexing workspace.
    required=8*sum(a.size for a in arrays)+g.size+48*maximum_matches+64*(len(g)+len(r)+g.shape[1]+1)
    if required>maximum_working_bytes:raise ValueError('Complete row comparison exceeds workspace budget; no columns dropped')
    for a in arrays:
        for row in a if a.ndim==2 else (a,):
            if not np.isfinite(row).all() or np.any(row>1e12) or np.any(row < -1e12):raise ValueError('Complete finite stored coefficients/bounds within1e12 required')
    g,u,r,l=(a.astype(float,copy=True) for a in arrays)
    pairs=np.empty((maximum_matches,2),np.int64);gaps=np.empty(maximum_matches,float);count=0
    for repair_index,row in enumerate(r):
        matched=np.flatnonzero(np.all(g==row,axis=1)&(l[repair_index]>u))
        if count+len(matched)>maximum_matches:raise ValueError('Complete conflict output exceeds budget; no matching identities dropped')
        stop=count+len(matched);pairs[count:stop,0]=matched;pairs[count:stop,1]=repair_index;gaps[count:stop]=l[repair_index]-u[matched];count=stop
    return dict(pairs=pairs[:count].copy(),bound_gaps=gaps[:count].copy(),report=dict(
        schema='strep-native-projection-guard-conflicts-v1',guard_rows=len(g),repair_rows=len(r),columns=g.shape[1],complete_pair_checks=checks,conflicts=count,
        all_rows_and_columns_retained=True,exact_stored_coefficient_equality=True,row_order='repair-row,guard-row',maximum_admitted_working_bytes=required,
        guards_removed=False,physical_permissions_verified=False,nonlinear_infeasibility_proven=False,quality_approved=False,release_approved=False,
        scope='Contradictory bounds on exactly equal supplied stored linear rows only. No near-equal/proportional search, other feasibility test or scene certificate. Caller binds row labels/source/clocks/permissions and retains original nonlinear raw/saved/full-mesh/contact gates for every alternative proposal.'))
