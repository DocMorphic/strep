"""Deterministic Godot unsigned-16 weight targets with checked Float32 loading."""
import numpy as np
from native_scene_imported_skin import godot_normalize
from native_engine_contacts import packed_weights


def condition(weights):
    weights=np.asarray(weights,float)
    if (weights.ndim!=2 or not len(weights) or weights.shape[1] not in (4,8)
            or not np.isfinite(weights).all() or np.any(weights<0) or np.any(weights.sum(1)<=0)):
        raise ValueError('Finite nonnegative four/eight weights with positive sums required')
    source=weights/weights.sum(1)[:,None]
    scaled=source*65535.;units=np.floor(scaled).astype(np.int64);remaining=65535-units.sum(1)
    if np.any(remaining<0) or np.any(remaining>weights.shape[1]):raise ValueError('Weight grid allocation unavailable')
    order=np.argsort(-(scaled-units),axis=1,kind='stable')
    for slot in range(weights.shape[1]):units[np.arange(len(units)),order[:,slot]]+=(remaining>slot)
    result=units.astype(np.float32)/np.float32(65535);leader=np.argmax(result,axis=1);adjusted=np.zeros(len(result),int)
    def total():
        value=np.zeros(len(result),np.float32)
        for slot in range(result.shape[1]):value=np.add(value,result[:,slot],dtype=np.float32)
        return value
    for _ in range(16):
        ids=np.flatnonzero(total()>1)
        if not len(ids):break
        result[ids,leader[ids]]=np.nextafter(result[ids,leader[ids]],np.float32(0));adjusted[ids]+=1
    if np.any(total()>1):raise ValueError('Bounded Float32 weight adjustment did not finish')
    encoded=packed_weights(godot_normalize(result));codes=np.rint(encoded*65535).astype(np.int64)
    error=65535-codes.sum(1)
    if np.any(abs(error)>1):raise ValueError('Checked weight grid exceeds one integer unit of sum error')
    if np.any(result[source==0]!=0) or float(abs(result-source).max())>2/65535:
        raise ValueError('Weight conditioning exceeds its declared coefficient change')
    return result,dict(vertices=len(result),influences=result.shape[1],float32_adjusted_rows=int((adjusted>0).sum()),
        maximum_adjustment_ulps=int(adjusted.max()),maximum_weight_change=float(abs(result-source).max()),
        encoded_integer_sum_error_counts={str(int(v)):int(c) for v,c in zip(*np.unique(error,return_counts=True))},
        original_encoding_unchanged=False,source_zeros_preserved=True,encoding_checked=True,
        scope='Coefficient conditioning only; actual skin/contact/engine fidelity still requires verification.')
