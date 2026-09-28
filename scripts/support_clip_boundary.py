"""Explicit experimental EOF policy: do not invent an observed release."""
import copy
import numpy as np


def retain_end_support(support, frames):
    """Retain onset fading; remove only a release fade cut off by clip EOF.

    Predicted intervals stay unconfirmed. This does not extrapolate outside
    the clip or override a release observed before its last frame.
    """
    if not isinstance(frames, int) or frames < 1:
        raise ValueError('Positive integer frame count required')
    result=copy.deepcopy(support)
    fade=support['edge_fade_frames']
    if not np.isfinite(fade) or fade <= 0:
        raise ValueError('Positive finite fade duration required')
    for side, guide in result['guides'].items():
        weights=np.asarray(guide['weights'],dtype=float)
        if weights.shape != (frames,) or not np.isfinite(weights).all() or np.any((weights<0)|(weights>1)):
            raise ValueError('Finite per-frame weights between zero and one required')
    changed=[]
    for interval in result['intervals']:
        a,b=interval['start_frame'],interval['end_frame_exclusive'];side=interval['side']
        if not isinstance(a,int) or not isinstance(b,int) or not 0<=a<b<=frames or side not in result['guides']:
            raise ValueError('Invalid recorded support interval')
        if b != frames:
            continue
        old=np.asarray(result['guides'][side]['weights'][a:b])
        # Preserve the original onset ramp even for an interval spanning EOF.
        phase=np.minimum(np.arange(1,b-a+1)/fade,1.)
        weights=np.sin(phase*np.pi/2)**2
        changed.extend(dict(side=side,frame=int(a+i),before=float(old[i]),after=float(weights[i]))
                       for i in np.flatnonzero(np.abs(old-weights)>1e-12))
        result['guides'][side]['weights'][a:b]=weights.tolist()
    result['boundary_policy']=dict(name='retain_support_at_clip_end',changed_weights=changed,
        extrapolated_frames=0,confirmed=False)
    return result
