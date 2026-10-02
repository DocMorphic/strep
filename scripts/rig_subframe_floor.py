"""Independent decoded flat-floor checks; finite samples are not a certificate."""
from pathlib import Path
import numpy as np
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import sha256


def inspect(path, floor_depth_m, hz=120):
    if type(floor_depth_m) not in (int,float) or not np.isfinite(floor_depth_m) or floor_depth_m<=0:
        raise ValueError('Positive finite floor depth required')
    if type(hz) is not int or not 1<=hz<=1000:raise ValueError('Integer sampling frequency from 1 to 1000 required')
    path=Path(path);digest=sha256(path);rig=RigAsset.load(path)
    if len(rig.document.get('animations',[]))!=1:raise ValueError('One animation required for floor inspection')
    # Export acceptance must not impose the Studio importer's 30-second limit.
    sampler=NativeSupportSampler(rig.document,rig.binary,0,max_duration_s=None)
    groups=[np.arange(int(np.floor(sampler.duration*hz))+1,dtype=float)/hz,np.array([sampler.duration])]
    for channel in sampler.channels:
        times=np.asarray(channel[2],float);groups.extend([times,(times[:-1]+times[1:])/2])
    times=np.unique(np.concatenate(groups));worst=None;failed=[]
    for time in times:
        points=rig.vertices(sampler.sample(float(time)))
        if not np.isfinite(points).all():raise ValueError('Nonfinite decoded floor geometry')
        vertex=int(np.argmin(points[:,1]));depth=max(0.,-float(points[vertex,1]))
        witness=dict(time_s=float(time),vertex=vertex,depth_m=depth,position_m=points[vertex].tolist())
        if worst is None or depth>worst['depth_m']:worst=witness
        if depth>floor_depth_m:failed.append(witness)
    if sha256(path)!=digest:raise ValueError('Floor inspection source changed')
    return dict(schema='strep-decoded-subframe-floor-v1',glb_sha256=digest,sampling_hz=hz,duration_s=sampler.duration,
        floor_depth_cap_m=float(floor_depth_m),samples=len(times),floor_depth_max_m=worst['depth_m'],
        failed_samples=len(failed),failures=failed,worst_floor=worst,sampled_floor_passed=not failed,quality_approved=False,
        scope='Decoded full-surface Y-up flat-floor check at a uniform clock, all exact native keys and channel midpoints. Finite samples only; no continuous collision, anatomical contact, object/partner collision, dynamics, semantics or human approval.')
