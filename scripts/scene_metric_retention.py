"""Exact, complete named lower-is-better metric comparisons, without approval."""
import numpy as np

MAX_BYTES=64*1024**2


def snapshot_metrics(values):
    if not isinstance(values,dict) or not 1<=len(values)<=256 or any(not isinstance(k,str) or not k or len(k)>160 for k in values):
        raise ValueError('Complete bounded named metric population required')
    raw={k:np.asarray(v) for k,v in values.items()}
    if (sum(v.size*8 for v in raw.values())*6>MAX_BYTES
            or any(v.dtype.kind not in 'fiu' or v.ndim>3 or not v.size or not np.isfinite(v).all() or np.any(v<0) or np.any(v>1e9) for v in raw.values())):
        raise ValueError('Finite nonnegative complete metric arrays within the working budget required')
    return {k:v.astype(np.float64,copy=True) for k,v in raw.items()}


def compare_metrics(before,after):
    before=snapshot_metrics(before);after=snapshot_metrics(after)
    if set(before)!=set(after) or any(before[k].shape!=after[k].shape for k in before):
        raise ValueError('All original metric names, shapes and row identities/order required')
    summaries={}
    for name,old in before.items():
        new=after[name];delta=new-old
        summaries[name]=dict(rows=old.size,shape=list(old.shape),before_maximum=float(old.max()),after_maximum=float(new.max()),
            maximum_increase=float(delta.max()),worsened_rows=int(np.count_nonzero(delta>0)))
    return dict(schema='strep-scene-metric-retention-v1',all_metrics_nonregressing=all(v['worsened_rows']==0 for v in summaries.values()),
        complete_metric_rows=sum(v.size for v in before.values()),metrics=summaries,tolerance_added=0.,quality_approved=False,release_approved=False,
        scope='Complete caller-bound named lower-is-better numeric populations, exact nonincrease per supplied scalar. No metric pruning, added epsilon, changed threshold or scene/motion/human approval. Caller retains the complete original observation populations and validates exported assets separately.')
