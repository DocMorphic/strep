"""Decoded foot-centroid dynamics around every drafted release, including swing."""
import numpy as np
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from strep import sha256


def dynamics(points,fps):
    points=np.asarray(points,float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<3 or not np.isfinite(points).all() or not np.isfinite(fps) or fps<=0:
        raise ValueError('Finite three-dimensional centroid track and positive fps required')
    velocity=np.diff(points,axis=0)*fps
    acceleration=np.diff(velocity,axis=0)*fps
    return velocity,acceleration


def release_windows(points,intervals,fps):
    velocity,acceleration=dynamics(points,fps);count=len(points);rows=[]
    for interval in intervals:
        b=interval['end_frame_exclusive']
        if type(b) is not int or not 1<=b<=count:raise ValueError('Release outside clip')
        if b==count:continue
        # Acceleration at frame f uses samples f-1,f,f+1. Include the last
        # planted frame and first three swing frames, clipped to real data.
        frames=np.arange(max(1,b-1),min(count-2,b+2)+1,dtype=int)
        speed_frames=np.arange(max(1,b-1),min(count-1,b+2)+1,dtype=int)
        rows.append(dict(start_frame=interval['start_frame'],release_frame=b,acceleration_frames=frames.tolist(),
            acceleration_max_m_s2=float(np.linalg.norm(acceleration[frames-1],axis=1).max()) if len(frames) else None,
            horizontal_speed_max_m_s=float(np.linalg.norm(velocity[speed_frames-1][:,[0,2]],axis=1).max()) if len(speed_frames) else None))
    return dict(centroids_m=np.asarray(points).tolist(),velocity_m_s=velocity.tolist(),acceleration_m_s2=acceleration.tolist(),
        global_acceleration_max_m_s2=float(np.linalg.norm(acceleration,axis=1).max()),releases=rows)


def measure(path,spec,support):
    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0);count=spec['frames'];fps=spec['fps']
    centers={side:[] for side in spec['patches']}
    for frame in range(count):
        vertices=rig.vertices(sampler.sample(float(np.float32(frame/fps))))
        for side,patch in spec['patches'].items():centers[side].append(vertices[patch['vertices']].mean(axis=0))
    return dict(source_sha256=sha256(path),feet={side:release_windows(np.asarray(points),[r for r in support['intervals'] if r['side']==side],fps) for side,points in centers.items()},
        quality_approved=False,scope='Decoded mesh-centroid dynamics, not sole slip, force balance or confirmed support semantics.')
