"""Keep complete grouped guidance, failing objectives and passing hard rows.

Passing scalar rows have zero hinge cost throughout their retained local hard
constraints. They need not also consume duplicate soft-objective rows. The
caller must retain every returned hard row and all original physical checks.
"""
import numpy as np

MAXIMUM_ROWS=65536
MAXIMUM_COLUMNS=768
MAXIMUM_MODEL_ROWS=8192
MAXIMUM_HARD_ROWS=8192
MAXIMUM_ARRAY_BYTES=64*1024**2


def _real(array):
    value=np.asarray(array)
    if value.dtype.kind not in 'fiu' or value.dtype.itemsize>8 or not np.isfinite(value).all():
        raise ValueError('Complete finite real arrays required')
    return value


def partition_world_objective(group_margins,group_jacobian,row_ids,raw_margins,saved_margins,margin_jacobian,required_rows,*,
                              maximum_model_rows=MAXIMUM_MODEL_ROWS,maximum_hard_rows=MAXIMUM_HARD_ROWS,maximum_array_bytes=MAXIMUM_ARRAY_BYTES):
    """Retain every supplied row in its objective and/or hard-constraint role.

    Margins are nonnegative on passing rows; Jacobians differentiate margins.
    Every original group remains in the objective. Every row failing either
    raw or saved mode is appended using the lower baseline margin. Every row
    passing either mode is returned as a hard row, including mixed-mode rows
    that require both roles. The raw Jacobian is local guidance for both modes;
    it is not a derivative or certificate of Float32 quantization.
    """
    for value,limit in [(maximum_model_rows,MAXIMUM_MODEL_ROWS),(maximum_hard_rows,MAXIMUM_HARD_ROWS),(maximum_array_bytes,MAXIMUM_ARRAY_BYTES)]:
        if type(value) is not int or not 1<=value<=limit:raise ValueError('Explicit bounded complete output budgets required')
    g=_real(group_margins);gj=_real(group_jacobian);raw=_real(raw_margins);saved=_real(saved_margins);j=_real(margin_jacobian);ids=np.asarray(row_ids)
    if (g.ndim!=1 or not 1<=len(g)<=MAXIMUM_MODEL_ROWS or gj.ndim!=2 or gj.shape[0]!=len(g)
            or not 1<=gj.shape[1]<=MAXIMUM_COLUMNS or raw.ndim!=1 or not 1<=len(raw)<=MAXIMUM_ROWS
            or saved.shape!=raw.shape or j.shape!=(len(raw),gj.shape[1])
            or ids.shape!=raw.shape or ids.dtype.kind not in 'iu' or ids.dtype.itemsize>8
            or np.any(ids<0) or np.any(ids>np.iinfo(np.int64).max) or len(np.unique(ids))!=len(ids)):
        raise ValueError('Complete aligned group/row margins, every column and distinct row identities required')
    if (not isinstance(required_rows,list) or any(type(r) is not int or r<0 for r in required_rows)
            or len(set(required_rows))!=len(required_rows)):
        raise ValueError('Explicit distinct repaired row identities required')
    lookup={int(row):i for i,row in enumerate(ids)}
    if not set(required_rows).issubset(lookup):raise ValueError('Every repaired witness must be present; no required row omitted')
    required=[lookup[r] for r in required_rows]
    if np.any(raw[required]<0) or np.any(saved[required]<0):raise ValueError('Every repaired witness must already pass both baseline modes')
    soft_mask=(raw<0)|(saved<0);hard_mask=(raw>=0)|(saved>=0);soft=int(soft_mask.sum());hard=int(hard_mask.sum());groups=len(g);rows=len(raw);columns=gj.shape[1]
    if groups+soft>maximum_model_rows or hard>maximum_hard_rows:
        raise ValueError('Complete objective/hard population exceeds budget; no row or group truncated')
    # Conservative array-copy/output estimate; callers still enforce process RSS.
    estimated=8*(groups*columns+rows*columns+(groups+soft)*columns+groups+2*rows+(groups+soft)+rows+2*soft+3*hard)+2*rows
    if estimated>maximum_array_bytes:raise ValueError('Complete input/output array budget exceeded; no columns or rows dropped')
    group_values=g.astype(float,copy=True);group_matrix=gj.astype(float,copy=True);row_matrix=j.astype(float,copy=True)
    raw=raw.astype(float,copy=True);saved=saved.astype(float,copy=True);ids=ids.astype(np.int64,copy=True)
    soft_indices=np.flatnonzero(soft_mask);hard_indices=np.flatnonzero(hard_mask)
    hard_passing=np.minimum(np.where(raw[hard_indices]>=0,raw[hard_indices],np.inf),np.where(saved[hard_indices]>=0,saved[hard_indices],np.inf))
    assert np.isfinite(hard_passing).all() and np.all(hard_passing>=0) and np.all(soft_mask|hard_mask)
    return dict(objective_margins=np.r_[group_values,np.minimum(raw,saved)[soft_indices]],
        objective_jacobian=np.vstack([group_matrix,row_matrix[soft_indices]]),
        objective_row_ids=ids[soft_indices],objective_indices=soft_indices,hard_row_ids=ids[hard_indices],hard_indices=hard_indices,
        hard_passing_margins=hard_passing,overlap_row_ids=ids[soft_mask&hard_mask],
        report=dict(schema='strep-native-world-objective-partition-v1',original_groups=groups,supplied_rows=rows,columns=columns,
            failing_either_mode=soft,passing_either_mode=hard,overlapping_roles=int((soft_mask&hard_mask).sum()),
            model_rows=groups+soft,required_repairs=len(required_rows),estimated_array_bytes=estimated,
            all_groups_retained=True,all_supplied_rows_have_objective_or_hard_role=True,physical_margin_tolerance_added=0.,
            quality_approved=False,release_approved=False,
            scope='Complete supplied affected/required population and original grouped guidance only. Every passing row must be retained by the caller as a hard constraint; no top-error selection, row dropping or group removal. '
                  'Baseline minima and a shared raw Jacobian guide both modes, not the quantizer derivative. Caller binds original sources, complete population/order, native and world norms, full raw/saved/geometry gates. No feasible-motion, optimum or release claim.'))
