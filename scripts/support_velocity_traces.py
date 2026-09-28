"""Decoded whole-clip derivatives, retaining maxima hidden by percentile screens."""
from pathlib import Path
import numpy as np
from strep import read, save, sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(folder):
    folder=Path(folder);spec=read(folder/'spec.json');annotations=read(folder/'input/contacts.json')
    count,fps=spec['frames'],spec['fps'];variants=[]
    for version in ['input','candidate']:
        path=folder/version/'character.glb';rig=RigAsset.load(path)
        sampler=AnimationSampler(rig.document,rig.binary,0)
        world=np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
        vertices=np.array([rig.vertices(w) for w in world]);feet={}
        for side,patch in spec['patches'].items():
            active=np.zeros(count,bool)
            for interval in annotations['intervals']:
                if interval['joint'] in [side+'Foot',side+'ToeBase']:
                    active[interval['start_frame']:interval['end_frame_exclusive']]=True
            points=vertices[:,patch['vertices']];center=points[:,:,[0,2]].mean(axis=1)
            speed=np.linalg.norm(np.diff(center,axis=0),axis=1)*fps;steps=active[:-1]&active[1:]
            feet[side]=dict(step_end_frames=list(range(1,count)),horizontal_speed_m_s=speed.tolist(),
                predicted_support_steps=steps.tolist(),predicted_support_max_m_s=float(speed[steps].max()) if steps.any() else None,
                predicted_support_p95_m_s=float(np.percentile(speed[steps],95)) if steps.any() else None,
                peak_step_end_frame=int(np.flatnonzero(steps)[np.argmax(speed[steps])]+1) if steps.any() else None)
        root=world[:,spec['root_node'],:3,3]
        accel=np.linalg.norm(np.diff(root,n=2,axis=0),axis=1)*fps*fps
        variants.append(dict(variant=version,source_sha256=sha256(path),feet=feet,
            root_acceleration_frames=list(range(1,count-1)),root_acceleration_m_s2=accel.tolist(),
            root_peak_frame=int(np.argmax(accel)+1),root_acceleration_max_m_s2=float(accel.max())))
    result=dict(variants=variants,quality_approved=False,scope='Predicted support, not confirmed contact. Keep all steps, including intended swing, separate from predicted-support statistics.')
    save(folder/'traces.json',result)
    return result
