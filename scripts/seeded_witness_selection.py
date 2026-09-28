"""Select every original contact vertex within a declared distance of its cap."""
import numpy as np


def select(records,depths,cap,band):
    depths=np.asarray(depths,float)
    if not np.isfinite(cap) or cap<0 or not np.isfinite(band) or band<=0:raise ValueError('Finite nonnegative cap and positive band required')
    keys=[]
    for r in records:
        if {r['source'],r['target']}!={0,1}:raise ValueError('Distinct actor directions required')
        for p in r['points']:
            if type(p[0]) is not int or p[0]<0:raise ValueError('Nonnegative integer vertex required')
            keys.append((r['source'],r['target'],p[0]))
    if depths.shape!=(len(keys),) or not np.isfinite(depths).all() or len(set(keys))!=len(keys):
        raise ValueError('Finite matching depths and unique identities required')
    if np.any(depths>cap+3e-10):raise ValueError('Original contact already exceeds declared cap')
    chosen=[(key,float(depth)) for key,depth in zip(keys,depths) if depth>=cap-band-1e-12]
    chosen.sort(key=lambda row:row[0])
    return dict(keys=[r[0] for r in chosen],original_depths_m=[r[1] for r in chosen],cap_m=float(cap),band_m=float(band))
