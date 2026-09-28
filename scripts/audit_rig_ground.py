"""Independent floor, hovering and sliding audit on exported target mesh soles."""
import argparse
from pathlib import Path
import numpy as np
from rig_asset import RigAsset
from gltf_tools import sample_animation
from target_rig_contact import regions,SoleDraftUnsupported
from correct_stance import load_motion
from inspect_motion import validate_motion
from strep import read,save,sha256,now


def audit(folder,reference_report=None):
    folder=Path(folder).resolve();report=reference_report or read(folder/'report.json');glb=folder/'character.glb'
    if sha256(glb)!=report['glb_sha256'] or sha256(report['source'])!=report['source_sha256']:
        raise ValueError('Ground audit inputs changed')
    rig=RigAsset.load(glb)
    from rig_contact_tracks import signals
    masks,contact_origin=signals(report)
    try:patches=regions(rig,report['mapping']);patch_error=None
    except SoleDraftUnsupported as exc:patches={};patch_error=str(exc)
    samples={name:[] for name in patches};depth=[];worst=None;feet={};envelopes={}
    for side in ('Left','Right'):
        joint_indices=[rig.joints.index(report['mapping'][side+role]) for role in ('Foot','ToeBase') if side+role in report['mapping']]
        membership=np.concatenate([np.zeros(len(p['positions'])) if p['joints'] is None else
            np.sum(np.where(np.isin(p['joints'],joint_indices),p['weights'],0),axis=1) for p in rig.primitives])
        feet[side]=np.flatnonzero(membership>=.65);envelopes[side]=[]
    for f in range(report['frames']):
        world=sample_animation(rig.document,rig.binary,0,f);points=rig.vertices(world)
        vertex=int(np.argmin(points[:,1]));value=max(0.,-float(points[vertex,1]));depth.append(value)
        if worst is None or value>worst['depth_m']:worst=dict(frame=f,vertex=vertex,depth_m=value,position_m=points[vertex].tolist())
        for name,patch in patches.items():samples[name].append(points[patch['vertices']].mean(axis=0))
        for side,indices in feet.items():envelopes[side].append(float(points[indices,1].min()) if len(indices) else None)
    support=[]
    for name,patch in patches.items():
        trajectory=np.array(samples[name]);mask=masks[patch['source_role']]
        frames=np.flatnonzero(mask);heights=trajectory[:,1]
        speed=np.linalg.norm(np.diff(trajectory[:,[0,2]],axis=0),axis=1)*report['fps']
        active=mask[:-1]&mask[1:];speed_frames=np.flatnonzero(active)
        height_frame=int(frames[np.argmax(np.abs(heights[frames]))]) if len(frames) else None
        speed_frame=int(speed_frames[np.argmax(speed[speed_frames])]) if len(speed_frames) else None
        support.append(dict(patch=name,source_role=patch['source_role'],predicted_frames=frames.tolist(),
            height_abs_max_m=float(np.max(np.abs(heights[mask]))) if mask.any() else None,
            hover_max_m=max(0.,float(np.max(heights[mask]))) if mask.any() else None,
            height_abs_p95_m=float(np.percentile(np.abs(heights[mask]),95)) if mask.any() else None,
            speed_p95_m_s=float(np.percentile(speed[active],95)) if active.any() else None,
            worst_height_frame=height_frame,worst_speed_frame=speed_frame))
    foot_support=[]
    for side,values in envelopes.items():
        mask=masks[side+'Foot']|masks[side+'ToeBase']
        frames=np.flatnonzero(mask);heights=np.asarray(values,dtype=float)
        valid=bool(len(feet[side]) and len(frames))
        foot_support.append(dict(side=side,weighted_vertices=len(feet[side]),predicted_frames=frames.tolist(),
            region_min_y_by_frame_m=values,hover_max_m=max(0.,float(heights[mask].max())) if valid else None,
            worst_hover_frame=int(frames[np.argmax(heights[mask])]) if valid else None))
    result=dict(created_at=now(),glb_sha256=sha256(glb),source_sha256=report['source_sha256'],frames=report['frames'],fps=report['fps'],
        floor_depth_by_frame_m=depth,worst_floor=worst,sole_support=support,sole_draft_error=patch_error,
        foot_envelope_support=foot_support,foot_envelope_scope='Minimum Y of vertices with >=65% combined foot/toe skin weight, while either source foot/toe contact is predicted. A coarse hover diagnostic, not a calibrated heel/toe patch or confirmed contact annotation.',
        contact_provenance=contact_origin,implementation_sha256=sha256(__file__),
        scope='Actual target skin vertices and reference-sole patch centroids. Support provenance is reported separately; predictions and their edited/blended timelines are not independent annotations. Positive sole height measures hovering above the declared y=0 plane; zero penetration alone is not a contact pass.')
    save(folder/'ground-audit.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path)
    args=parser.parse_args();manifest=read(args.study/'manifest.json');checks=[]
    for case in manifest['cases']:
        folder=(args.study/case['path']).parent;result=audit(folder)
        support=result['sole_support'];gaps=[p['hover_max_m'] for p in support if p['hover_max_m'] is not None]
        slips=[p['speed_p95_m_s'] for p in support if p['speed_p95_m_s'] is not None]
        envelopes=[p['hover_max_m'] for p in result['foot_envelope_support'] if p['hover_max_m'] is not None]
        checks.append(dict(id=case['id'],rig=case['rig'],action=case['action'],glb_sha256=case['sha256'],
            floor_depth_m=result['worst_floor']['depth_m'],worst_floor_frame=result['worst_floor']['frame'],
            predicted_sole_hover_max_m=max(gaps) if gaps else None,predicted_sole_speed_p95_max_m_s=max(slips) if slips else None,
            predicted_foot_region_hover_max_m=max(envelopes) if envelopes else None,
            sole_draft_error=result['sole_draft_error']))
        print(case['rig'],case['action'],checks[-1],flush=True)
    save(args.study/'ground-comparison.json',dict(checks=checks,scope='Development diagnostics only. No acceptance threshold fitted to these outputs; no human approval.'))
