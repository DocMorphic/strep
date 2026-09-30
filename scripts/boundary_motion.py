"""Export-decoded per-joint boundary motion comparisons, including join stencils."""
import numpy as np
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def affected_positions(parents,variable_joints):
    affected=set();variable=set(variable_joints)
    for joint,parent in enumerate(parents):
        if parent>=joint or parent < -1:raise ValueError('Topologically ordered skeleton required')
        if parent in variable or parent in affected:affected.add(joint)
    return sorted(affected)


def sample_positions(path,frames):
    times=np.arange(frames[0]-2,frames[-1]+2.001,.25)
    doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0)
    return times,np.array([sampler.sample(t/30)[doc['skins'][0]['joints'],:3,3] for t in times])


def window_peaks(times,positions,frames):
    times=np.asarray(times,float);positions=np.asarray(positions,float)
    if positions.ndim!=3 or positions.shape[0]!=len(times) or positions.shape[2]!=3 or not np.isfinite(positions).all() or not np.allclose(np.diff(times),.25,atol=1e-12,rtol=0):
        raise ValueError('Finite quarter-frame positions required')
    lo,hi=frames[0]-1,frames[-1]+1
    velocity=np.linalg.norm(np.diff(positions,axis=0)*120,axis=-1)
    acceleration=np.linalg.norm(np.diff(positions,n=2,axis=0)*120**2,axis=-1)
    speed_mask=(times[:-1]>=lo)&(times[1:]<=hi)
    acceleration_mask=(times[1:-1]>=lo)&(times[1:-1]<=hi)
    if not speed_mask.any() or not acceleration_mask.any() or times[0]>lo-.25 or times[-1]<hi+.25:
        raise ValueError('Both fixed-neighbor join stencils required')
    return velocity[speed_mask].max(0),acceleration[acceleration_mask].max(0)


def make_caps(input_glb,reference_glb,frames,joints,names,fraction=.99):
    if not 0<fraction<1:raise ValueError('Strictly interior fitting fraction required')
    measured=[]
    for path in [input_glb,reference_glb]:
        times,positions=sample_positions(path,frames);speed,acceleration=window_peaks(times,positions,frames)
        measured.append(dict(speed_m_s=speed[joints].tolist(),acceleration_m_s2=acceleration[joints].tolist()))
    speed=np.minimum(measured[0]['speed_m_s'],measured[1]['speed_m_s'])
    acceleration=np.minimum(measured[0]['acceleration_m_s2'],measured[1]['acceleration_m_s2'])
    return dict(frames=frames,joints=joints,joint_names=[names[j] for j in joints],input=measured[0],reference=measured[1],
                fitting_fraction=fraction,speed_caps_m_s=speed.tolist(),acceleration_caps_m_s2=acceleration.tolist(),
                fitting_speed_caps_m_s=(fraction*speed).tolist(),fitting_acceleration_caps_m_s2=(fraction*acceleration).tolist())
