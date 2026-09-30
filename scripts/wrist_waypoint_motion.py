"""Bake a two-bone wrist waypoint into eligible native rotation keys only."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from elbow_swivel import local_transforms
from two_bone_waypoint import reach
from timed_rotation_edit import editable_keys
from paired_temporal_neighbor import rotation_channels
from rig_clip_import import AnimationSampler
from gltf_tools import append_accessor,write_glb


def bump(time,start,peak,end):
    if not np.isfinite([time,start,peak,end]).all() or not 0<=start<peak<end:
        raise ValueError('Finite ordered waypoint times required')
    if time<=start or time>=end:return 0.
    u=(time-start)/(peak-start) if time<=peak else (end-time)/(end-peak)
    return float(u**3*(10+u*(-15+6*u)))


def peak_window(geometry,sample,window):
    """End in the clear interval after the peak's contiguous failing cluster."""
    times=np.asarray([r['time_s'] for r in geometry]);depth=np.asarray([r['candidate_depth_m'] for r in geometry])
    if ([r['sample'] for r in geometry]!=list(range(len(geometry))) or
            len(times)<3 or not np.isfinite([times,depth]).all() or np.any(np.diff(times)<=0)):
        raise ValueError('Complete finite ordered geometry required')
    if type(sample) is not int or not 0<=sample<len(times) or depth[sample]<=.005:
        raise ValueError('Failing peak sample required')
    start,end=map(float,window);peak=float(times[sample]);last=sample
    while last+1<len(times) and depth[last+1]>.005:last+=1
    later=np.flatnonzero((np.arange(len(times))>last)&(depth>.005))
    if len(later):end=min(end,float((times[last]+times[later[0]])/2))
    if not 0<=start<peak<end:raise ValueError('No nonempty approach interval around peak')
    return start,peak,end


def bake(rig,chain,world_offset,placement_rotation,angle_degrees,window,protected,output,budget_degrees=45.,control_curve=None):
    times=np.asarray(window,float)
    if times.shape!=(3,):raise ValueError('Start, peak and end required')
    bump(times[1],*times)
    offset=np.asarray(world_offset,float);rotation=np.asarray(placement_rotation,float)
    if offset.shape!=(3,) or rotation.shape!=(3,3) or not np.isfinite(offset).all() or not np.isfinite(rotation).all():
        raise ValueError('Finite waypoint and placement required')
    if not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-10) or np.linalg.det(rotation)<0:
        raise ValueError('Rigid placement rotation required')
    if not np.isfinite([angle_degrees,budget_degrees]).all() or not 0<budget_degrees<=45:
        raise ValueError('Finite pose controls and budget up to 45 degrees required')
    source=AnimationSampler(rig.document,rig.binary,0);channels=rotation_channels(rig.document,rig.binary)
    if len(chain)!=3 or len(set(chain))!=3 or any(n not in channels for n in chain):
        raise ValueError('Three distinct animated arm joints required')
    if times[-1]>source.duration:raise ValueError('Waypoint window outside clip')
    controls={};observations=[];cache={}
    for node in chain:
        _,clock,original=channels[node];values=original.copy()
        indices=editable_keys(clock,[times[0],times[2]],protected)
        for key in indices:
            stamp=float(clock[key]);factor=bump(stamp,*times)
            desired=np.r_[offset*factor,angle_degrees*factor] if control_curve is None else np.asarray(control_curve(stamp),float)
            if desired.shape!=(4,) or not np.isfinite(desired).all():raise ValueError('Finite 3D offset and swivel curve required')
            if np.linalg.norm(desired[:3])>.06+1e-12 or abs(desired[3])>45+1e-12:raise ValueError('Curve exceeds guide domain')
            if not np.any(desired):continue
            if stamp not in cache:
                world=source.sample(stamp);target=world[chain[2],:3,3]+desired[:3]@rotation
                _,local=reach(world,rig.parents,*chain,target,np.deg2rad(desired[3]))
                before=local_transforms(world,rig.parents)
                edits=Rotation.from_matrix(before[:,:3,:3]).inv()*Rotation.from_matrix(local[:,:3,:3])
                magnitude=float(np.rad2deg(edits.magnitude()).max())
                if magnitude>budget_degrees+1e-4:raise ValueError('Waypoint exceeds native pose budget')
                cache[stamp]=local
                observation=dict(time_s=stamp,factor=factor if control_curve is None else None,maximum_edit_degrees=magnitude)
                if control_curve is not None:observation['guide']=desired.tolist()
                observations.append(observation)
            q=Rotation.from_matrix(cache[stamp][node,:3,:3]).as_quat()
            if q@original[key]<0:q=-q
            values[key]=q.astype(np.float32)
        controls[node]=(values,indices)
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=doc['animations'][0]
    for channel in animation['channels']:
        node=channel['target']['node']
        if channel['target']['path']=='rotation' and node in controls:
            sampler=copy.deepcopy(animation['samplers'][channel['sampler']])
            sampler['output']=append_accessor(doc,binary,controls[node][0],'VEC4')
            channel['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
    write_glb(output,doc,binary)
    return dict(nodes={str(n):indices.tolist() for n,(_,indices) in controls.items()},
                observations=sorted(observations,key=lambda r:r['time_s']),budget_degrees=budget_degrees)
