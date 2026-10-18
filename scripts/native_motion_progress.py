"""Complete paired sampled-world progress without loosening physical margins.

A fixed worst row may belong to another temporal block. Reducing other errors
can be useful while that peak remains unchanged. This module never approves
native permissions, contacts, geometry, an exported asset or a release.
"""
import numpy as np

MAXIMUM_ROWS=2000000
MAXIMUM_INPUT_BYTES=64*1024**2
MODES=('raw_world','encoded_world')


def compare_motion_rows(before,after,required_rows,*,minimum_squared_improvement=1e-7,
                        maximum_rows=MAXIMUM_ROWS,maximum_input_bytes=MAXIMUM_INPUT_BYTES):
    """Compare every original signed margin in both representations.

    Nonnegative margins pass exactly; there is no added acceptance epsilon.
    Both modes must reduce total squared violation strictly beyond the declared
    progress threshold, preserve their peak, all passing rows and every required
    repair. The caller binds equal row identities/order, source caps and files.
    """
    if (not isinstance(before,dict) or not isinstance(after,dict)
            or set(before)!=set(MODES) or set(after)!=set(MODES)):
        raise ValueError('Complete named raw/saved margin populations required')
    if (type(maximum_rows) is not int or not 1<=maximum_rows<=MAXIMUM_ROWS
            or type(maximum_input_bytes) is not int or not 1<=maximum_input_bytes<=MAXIMUM_INPUT_BYTES
            or type(minimum_squared_improvement) not in (int,float)
            or not 0<=minimum_squared_improvement<=1e12):
        raise ValueError('Explicit bounded complete budgets and progress threshold required')
    arrays=[np.asarray(collection[mode]) for collection in (before,after) for mode in MODES]
    count=arrays[0].size
    if (not 1<=count<=maximum_rows or count*len(arrays)*8>maximum_input_bytes
            or any(a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or a.shape!=(count,)
                   or not np.isfinite(a).all() or np.any(np.abs(a.astype(float))>1e6) for a in arrays)):
        raise ValueError('Complete matching finite bounded margin vectors required; no row pruning')
    if (not isinstance(required_rows,list) or len(set(required_rows))!=len(required_rows)
            or any(type(i) is not int or not 0<=i<count for i in required_rows)):
        raise ValueError('Explicit distinct in-range repaired row identities required')
    before={m:a.astype(float,copy=True) for m,a in zip(MODES,arrays[:2])}
    after={m:a.astype(float,copy=True) for m,a in zip(MODES,arrays[2:])}
    if any(np.any(before[m][required_rows]<0) for m in MODES):
        raise ValueError('Every required witness must already pass in both baseline populations')
    comparisons={}
    for mode in MODES:
        old,new=before[mode],after[mode];a=np.maximum(-old,0);b=np.maximum(-new,0)
        old_score=float(a@a);new_score=float(b@b)
        row=dict(rows=count,before_failed=int(np.count_nonzero(old<0)),after_failed=int(np.count_nonzero(new<0)),
            new_failures=int(np.count_nonzero((old>=0)&(new<0))),required_failures=int(np.count_nonzero(new[required_rows]<0)),
            before_peak=float(a.max()),after_peak=float(b.max()),before_sum_squared=old_score,after_sum_squared=new_score,
            squared_improvement=old_score-new_score,repaired_rows=np.flatnonzero((old<0)&(new>=0)).tolist())
        row['progress']=bool(row['new_failures']==row['required_failures']==0
            and row['after_failed']<=row['before_failed'] and row['after_peak']<=row['before_peak']
            and row['squared_improvement']>minimum_squared_improvement)
        comparisons[mode]=row
    return dict(schema='strep-native-motion-progress-v1',rows_per_mode=count,required_repairs=len(required_rows),
        minimum_squared_improvement=float(minimum_squared_improvement),comparisons=comparisons,
        sampled_world_progress=all(c['progress'] for c in comparisons.values()),
        all_rows_and_both_modes_retained=True,physical_margin_tolerance_added=0.,quality_approved=False,release_approved=False,
        scope='Complete supplied paired sampled-world margins only, caller-bound same row identities/order and original source caps. '
              'Strict total-error improvement permits an unchanged worst row in another temporal block; no other regression allowed. '
              'No native/pose/pair/geometry/continuous/dynamics/engine/semantic/human or whole-clip approval.')
