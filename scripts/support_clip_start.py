"""Experimental clipped-start policy; observed internal transitions stay intact."""
import copy
import numpy as np


def retain_start_support(support, frames):
    if type(frames) is not int or frames<1:
        raise ValueError('Positive integer frame count required')
    result=copy.deepcopy(support);fade=support['edge_fade_frames'];changed=[]
    if not np.isfinite(fade) or fade<=0:raise ValueError('Positive finite fade required')
    for guide in result['guides'].values():
        weights=np.asarray(guide['weights'],dtype=float)
        if weights.shape!=(frames,) or not np.isfinite(weights).all() or np.any((weights<0)|(weights>1)):
            raise ValueError('Finite per-frame support weights required')
    for interval in result['intervals']:
        a,b=interval['start_frame'],interval['end_frame_exclusive'];side=interval['side']
        if type(a) is not int or type(b) is not int or not 0<=a<b<=frames or side not in result['guides']:
            raise ValueError('Invalid support interval')
        if a!=0:continue
        old=np.asarray(result['guides'][side]['weights'][a:b])
        # Only remove the clipped onset ramp. Keep the existing values once
        # that ramp was fully weighted, including any separately authored EOF.
        onset=np.sin(np.minimum(np.arange(1,b-a+1)/fade,1.)*np.pi/2)**2
        if np.any(onset<=0):raise ValueError('Invalid onset ramp')
        release=np.sin(np.minimum(np.arange(b-a,0,-1)/fade,1.)*np.pi/2)**2 if b<frames else np.ones(b-a)
        ramp=onset<1-1e-12
        if not np.allclose(old[ramp],np.minimum(onset,release)[ramp],rtol=0,atol=1e-12):
            raise ValueError('Start weights are not the recorded draft ramp; preserve custom weights')
        weights=np.minimum(1.,old/onset)
        # The original draft uses min(onset, release), not multiplication.
        # Preserve a real release even when its ramp overlaps a short onset.
        if b<frames:
            weights=np.minimum(weights,release)
        changed.extend(dict(side=side,frame=int(i),before=float(old[i]),after=float(weights[i]))
                       for i in np.flatnonzero(np.abs(old-weights)>1e-12))
        result['guides'][side]['weights'][a:b]=weights.tolist()
    result['start_boundary_policy']=dict(name='retain_support_at_clip_start',changed_weights=changed,
        extrapolated_frames=0,confirmed=False)
    return result
