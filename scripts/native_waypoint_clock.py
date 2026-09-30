"""Choose the shared native-key support around a requested approach peak.

This planner requires synchronized arm tracks. It never resamples or changes
native clocks, and rejects asynchronous tracks rather than approximating them.
"""
import numpy as np
from timed_rotation_edit import editable_keys


def guarded_approach_window(authored,peak,protected):
    """Largest guard-delimited interval containing the requested editable peak."""
    authored=np.asarray(authored,float);spans=np.asarray(protected,float).reshape(-1,2)
    if authored.shape!=(2,) or not np.isfinite(authored).all() or not np.isfinite(peak) or not 0<=authored[0]<peak<authored[1]:
        raise ValueError('Peak inside a finite authored edit interval required')
    if not np.isfinite(spans).all() or np.any(spans<0) or np.any(spans[:,1]<spans[:,0]):
        raise ValueError('Ordered finite protected intervals required')
    start,end=authored
    for first,last in spans:
        if first<=peak<=last:raise ValueError('Requested approach peak is protected')
        if last<peak:start=max(start,last)
        if first>peak:end=min(end,first)
    return float(start),float(peak),float(end)


def guide_clock(clocks,window,protected):
    window=np.asarray(window,float)
    if window.shape!=(3,) or not np.isfinite(window).all() or not 0<=window[0]<window[1]<window[2]:
        raise ValueError('Finite start, peak and end required')
    clocks=[np.asarray(c,float) for c in clocks]
    if not clocks:raise ValueError('Native arm clocks required')
    clock=clocks[0]
    ids=editable_keys(clock,window[[0,2]],protected)
    if any(not np.array_equal(c,clock) for c in clocks[1:]):
        raise ValueError('Synchronized native arm clocks required for this planner')
    runs=np.split(ids,np.flatnonzero(np.diff(ids)!=1)+1)
    matches=[r for r in runs if len(r) and clock[r[0]-1]<window[1]<clock[r[-1]+1]]
    if len(matches)!=1:raise ValueError('No editable native support around requested peak')
    run=matches[0]
    # The adjacent frozen keys are exact zero-control endpoints. Every interior
    # key is editable, including when a protected span splits the allowed window.
    return clock[run[0]-1:run[-1]+2].copy()
