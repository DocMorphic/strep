"""Explicit authored-key or half-open frame-hold contact sampling."""
import numpy as np

CONTACT_CLOCKS=('authored-keys','frame-hold')

def validate_clock(choice):
    if type(choice) is not str or choice not in CONTACT_CLOCKS:
        raise ValueError('Contact clock must be authored-keys or frame-hold')
    return choice

def layout(spec,times,choice):
    validate_clock(choice);times=np.asarray(times,float)
    keys=(np.arange(spec['frames']+1,dtype=np.float32)/spec['fps']).astype(float)
    groups=[];selected=[]
    for index,target in enumerate(spec['contacts']):
        a,b=target['start_frame'],target['end_frame_exclusive']
        clock=keys[a:b] if choice=='authored-keys' else times[(times>=keys[a])&(times<keys[b])]
        if not len(clock):raise ValueError('Contact interval has no playback samples')
        selected.extend(clock.tolist());groups.extend([index]*len(clock))
    return np.asarray(selected,float),np.asarray(groups,dtype=int)
