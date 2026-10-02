"""Inspect explicit contact timing on decoded full-mesh centroid tracks."""
from pathlib import Path
import numpy as np
from mesh_contact_clock import layout,validate_clock
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from target_rig_contact import validate
from strep import sha256


def inspect(path,spec,contact_clock='authored-keys',hz=120):
    validate_clock(contact_clock)
    if type(hz) is not int or not 1<=hz<=1000:raise ValueError('Integer sampling frequency from 1 to 1000 required')
    path=Path(path);digest=sha256(path)
    if digest!=spec['glb_sha256']:raise ValueError('Inspection draft belongs to a different mesh clip')
    rig=RigAsset.load(path);validate(spec,rig)
    if len(rig.document.get('animations',[]))!=1:raise ValueError('One animation required for contact inspection')
    sampler=NativeSupportSampler(rig.document,rig.binary,0,max_duration_s=None)
    keys=(np.arange(spec['frames']+1,dtype=np.float32)/spec['fps']).astype(float)
    if keys[-2]>sampler.duration:raise ValueError('Declared contact frames exceed animation duration')
    groups=[np.arange(int(np.floor(sampler.duration*hz))+1,dtype=float)/hz,np.array([sampler.duration]),keys[keys<=sampler.duration]]
    for channel in sampler.channels:
        times=np.asarray(channel[2],float);groups.extend([times,(times[:-1]+times[1:])/2])
    times=np.unique(np.concatenate(groups));selected,indices=layout(spec,times,contact_clock)
    tracks={}
    for time in np.unique(selected):
        points=rig.vertices(sampler.sample(float(time)))
        if not np.isfinite(points).all():raise ValueError('Nonfinite decoded contact geometry')
        tracks[float(time)]={name:points[patch['vertices']].mean(axis=0) for name,patch in spec['patches'].items()}
    contacts=[];cap=spec['screen']['contact_error_m']
    for index,target in enumerate(spec['contacts']):
        samples=selected[indices==index]
        points=np.array([tracks[float(t)][target['patch']] for t in samples])
        error=np.linalg.norm(points-target['target_position_m'],axis=1);peak=int(np.argmax(error))
        contacts.append(dict(index=index,**target,samples=len(samples),error_max_m=float(error[peak]),
            failed_samples=int(np.sum(error>cap)),times_s=samples.tolist(),positions_m=points.tolist(),
            worst_time_s=float(samples[peak]),worst_position_m=points[peak].tolist()))
    if sha256(path)!=digest:raise ValueError('Contact inspection source changed')
    return dict(schema='strep-decoded-contact-clock-v1',glb_sha256=digest,contact_clock=contact_clock,sampling_hz=hz,
        duration_s=sampler.duration,contact_error_cap_m=float(cap),contacts=contacts,samples=len(selected),
        unique_sampled_poses=len(tracks),failed_intervals=sum(c['failed_samples']>0 for c in contacts),
        sampled_contacts_passed=all(c['failed_samples']==0 for c in contacts),quality_approved=False,
        scope='Actual decoded full-mesh centroid targets at explicit authored keys or half-open frame holds intersected with the clip duration. Includes uniform times, native keys and channel midpoints. Finite samples; not continuous certification, anatomy, dynamics or semantic approval.')
