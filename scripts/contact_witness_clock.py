"""Derive a development fitting clock from retained full-clock collision witnesses."""
import math


def enrich(base,curves,window=(45.,105.),threshold=.005):
    clock=[i*.5 for i in range(299)]
    if not curves or not math.isfinite(threshold) or threshold<=0:
        raise ValueError('Audited curves and positive finite threshold required')
    if len(window)!=2 or any(x not in clock for x in window) or window[0]>=window[1]:
        raise ValueError('Valid editable window on the half-frame clock required')
    if not base or len(set(base))!=len(base) or list(base)!=sorted(base) or any(f not in clock for f in base):
        raise ValueError('Unique ordered original clock required')
    if any(not window[0]<=f<=window[1] for f in base):raise ValueError('Original clock outside editable window')
    witnesses={};outside=set();inside=set()
    for name,curve in curves.items():
        depth=curve['body_depth_m']
        if curve['frames']!=clock or len(depth)!=len(clock) or any(not math.isfinite(d) or d<0 for d in depth):
            raise ValueError('Complete finite nonnegative full-clock geometry required')
        failures=[f for f,d in zip(clock,depth) if d>threshold]
        witnesses[name]=failures
        inside.update(f for f in failures if window[0]<=f<=window[1])
        outside.update(f for f in failures if not window[0]<=f<=window[1])
    neighbors={f+offset for f in inside for offset in [-.5,0.,.5] if window[0]<=f+offset<=window[1]}
    result=sorted(set(base)|neighbors)
    return dict(original_frames=list(base),frames=result,added_frames=sorted(set(result)-set(base)),
        source_failure_frames=witnesses,uneditable_failure_frames=sorted(outside),threshold_m=threshold,
        neighbor_half_steps=1,window=list(window),quality_approved=False,
        scope='Development witness enrichment using all retained methods, including failures and adjacent half-frames. Full exported validation remains required; no guarantee between these samples.')
