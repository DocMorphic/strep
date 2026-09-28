"""Experimental ablation: keep support weight until an observed interval ends.

Only the release ramp inside an existing draft interval changes. Onset,
anchors, labels and frames outside the interval remain unchanged. A sharp
release can worsen swing continuity; full decoded motion must be measured.
"""
import copy
import numpy as np


def hold_until_release(support, frames):
    if type(frames) is not int or frames<1:raise ValueError('Positive integer frame count required')
    fade=support['edge_fade_frames']
    if not np.isfinite(fade) or fade<=0:raise ValueError('Positive finite fade duration required')
    result=copy.deepcopy(support);occupied={};changed=[]
    for side,guide in result['guides'].items():
        w=np.asarray(guide['weights'],float);a=np.asarray(guide['anchors_xz_m'],float)
        if w.shape!=(frames,) or a.shape!=(frames,2) or not np.isfinite(np.r_[w,a.ravel()]).all() or np.any((w<0)|(w>1)):
            raise ValueError('Finite matching support weights and anchors required')
        occupied[side]=np.zeros(frames,bool)
    for interval in result['intervals']:
        a,b=interval['start_frame'],interval['end_frame_exclusive'];side=interval['side']
        if type(a) is not int or type(b) is not int or not 0<=a<b<=frames or side not in occupied:
            raise ValueError('Invalid recorded interval')
        if occupied[side][a:b].any():raise ValueError('Overlapping recorded intervals')
        occupied[side][a:b]=True
        old=np.asarray(result['guides'][side]['weights'][a:b],float)
        onset=np.sin(np.minimum(np.arange(1,b-a+1)/fade,1.)*np.pi/2)**2
        release=np.sin(np.minimum(np.arange(b-a,0,-1)/fade,1.)*np.pi/2)**2
        if a==0 and result.get('start_boundary_policy',{}).get('name')=='retain_support_at_clip_start':onset[:]=1.
        if b==frames and result.get('boundary_policy',{}).get('name')=='retain_support_at_clip_end':release[:]=1.
        if not np.allclose(old,np.minimum(onset,release),rtol=0,atol=1e-12):
            raise ValueError('Weights are not the recorded draft ramps; preserve custom authoring')
        # EOF has no observed release. Existing EOF policy is retained verbatim.
        if b==frames:continue
        result['guides'][side]['weights'][a:b]=onset.tolist()
        changed.extend(dict(side=side,frame=int(a+i),before=float(old[i]),after=float(onset[i]))
            for i in np.flatnonzero(np.abs(old-onset)>1e-12))
    result['release_hold_policy']=dict(name='hold_drafted_support_until_observed_release',changed_weights=changed,
        extrapolated_frames=0,confirmed=False,scope='Release-weight ablation only; swing continuity and contact semantics remain unvalidated.')
    return result
