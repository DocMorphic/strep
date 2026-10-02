"""Explicit authored-key or half-open frame-hold contact sampling."""
import numpy as np

CONTACT_CLOCKS=('authored-keys','frame-hold')

def validate_clock(choice):
    if type(choice) is not str or choice not in CONTACT_CLOCKS:
        raise ValueError('Contact clock must be authored-keys or frame-hold')
    return choice

def validate_overrides(overrides,count):
    if overrides is None:return {}
    if type(overrides) is not dict:raise ValueError('Contact clock overrides must map interval indices to clocks')
    result={}
    for index,choice in overrides.items():
        if type(index) is not str or not index.isascii() or not index.isdecimal() or str(int(index))!=index or not 0<=int(index)<count:
            raise ValueError('Contact clock override index must identify an existing interval')
        result[index]=validate_clock(choice)
    return result


def layout(spec,times,choice,overrides=None):
    validate_clock(choice);overrides=validate_overrides(overrides,len(spec['contacts']));times=np.asarray(times,float)
    keys=(np.arange(spec['frames']+1,dtype=np.float32)/spec['fps']).astype(float)
    groups=[];selected=[]
    for index,target in enumerate(spec['contacts']):
        a,b=target['start_frame'],target['end_frame_exclusive']
        selected_choice=overrides.get(str(index),choice)
        clock=keys[a:b] if selected_choice=='authored-keys' else times[(times>=keys[a])&(times<keys[b])]
        if not len(clock):raise ValueError('Contact interval has no playback samples')
        selected.extend(clock.tolist());groups.extend([index]*len(clock))
    return np.asarray(selected,float),np.asarray(groups,dtype=int)
