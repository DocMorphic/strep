"""Fit authored foot pins before carrying a native SOMA scene; retain failures.

This is a development experiment, not automatic stance detection or physics.
The input must be a portable single-actor scene with a platform object.
"""
import argparse
import os
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits

from strep import ROOT, read, save, sha256
from action_worker_lock import worker_lock
from build_soma_preview import ASSET
from floor_contact import Surface
from support_contact import regions
from support_contact_v8 import refine, CONFIG
from evaluate_contact_spec import evaluate
from run_body_contact import export_motion
from kimodo.skeleton import SOMASkeleton77
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from audit_scene_timing import rates
from audit_scene_edit_window import summarize as window_summary
from carry_scene_actor import run as carry
from scene_runtime import write as write_runtime


def audit(source_glb, candidate_glb, spec, window, frames):
    """Decode both exports at 120 Hz with identical, fixed material points."""
    rigs = [RigAsset.load(p) for p in [source_glb, candidate_glb]]
    clocks = [AnimationSampler(r.document, r.binary, 0) for r in rigs]
    pins = [(name, entry['segments'][0]) for name, entry in spec['regions'].items()
            if entry['mode'] == 'explicit']
    tracks = [[], []]; joints = [[], []]; floors = [[], []]; rows = []
    with threadpool_limits(limits=1):
        for i in range((frames-1)*4+1):
            matrices = [c.sample(i/120) for c in clocks]
            meshes = [r.vertices(m) for r, m in zip(rigs, matrices)]
            js = [m[r.joints] for r, m in zip(rigs, matrices)]
            rows.append(dict(frame=i/4,
                joint_position_error_m=float(np.linalg.norm(js[1][:,:3,3]-js[0][:,:3,3],axis=1).max()),
                basis_error=float(np.abs(js[1][:,:3,:3]-js[0][:,:3,:3]).max()),
                skin_position_error_m=float(np.linalg.norm(meshes[1]-meshes[0],axis=1).max())))
            for v in range(2):
                tracks[v].append([meshes[v][p['vertex_id']] for _, p in pins])
                joints[v].append(js[v]); floors[v].append(max(0.,float(-meshes[v][:,1].min())))
    variants = {}
    for v, label in enumerate(['source','candidate']):
        points = np.array(tracks[v]); contacts = []
        for j, (name, pin) in enumerate(pins):
            a,b = pin['start_frame']*4,pin['end_frame']*4+1
            error = np.linalg.norm(points[a:b,j]-pin['position_m'],axis=1)
            speed = np.linalg.norm(np.diff(points[a:b,j],axis=0)*120,axis=1)
            contacts.append(dict(region=name,vertex_id=pin['vertex_id'],samples=len(error),
                max_error_m=float(error.max()),p95_error_m=float(np.percentile(error,95)),
                samples_over_5mm=int((error>.005).sum()),
                speed_p95_m_s=float(np.percentile(speed,95)),speed_max_m_s=float(speed.max())))
        names = [rigs[v].document['nodes'][n].get('name',str(n)) for n in rigs[v].joints]
        variants[label] = dict(pins=contacts,joints=rates(np.array(joints[v]),1/120,names),
            maximum_floor_depth_m=max(floors[v]),floor_samples_over_1cm=sum(d>.01 for d in floors[v]))
    return dict(samples=len(rows),variants=variants,preservation=window_summary(rows,window,frames),
        scope='Full eight-weight exported mesh at 120 Hz; fixed material foot points. Finite differences are sampling-dependent. No continuous collision, sole orientation, anatomy, balance or force guarantee.',
        quality_approved=False)


def run(source, output, *, start=30, end=149, anchor=90, window=(20,159), stages=2, iterations=60, rate_guard=False, point_rate_guard=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'reports'):
        raise ValueError('Fresh output beneath reports required')
    scene = read(source/'portable-scene.json')
    if set(scene['actors']) != {'A'} or 'platform' not in scene['objects'] or scene['fps'] != 30:
        raise ValueError('Single A actor, platform object and 30 fps scene required')
    frames = scene['frame_count']
    if not 0 <= window[0] < start <= anchor <= end < window[1] < frames:
        raise ValueError('Pin interval and anchor must be inside the editable window')
    motion_path = (source/scene['actors']['A']['motion']).resolve()
    # Portable scene motion paths are local; never silently select another clip.
    if not motion_path.is_relative_to(source):raise ValueError('Motion escapes portable scene')
    raw = dict(np.load(motion_path)); skin = dict(np.load(ASSET)); surface = Surface(skin)
    if len(raw['root_positions']) != frames:raise ValueError('Motion frame count differs')
    spec = dict(schema_version=1,fps=30,frame_count=frames,regions={})
    for name, ids in regions(skin).items():
        if name not in ['LeftFoot','RightFoot']:
            spec['regions'][name] = dict(mode='disabled');continue
        points = surface.vertices(raw['global_rot_mats'][anchor],raw['posed_joints'][anchor],ids)
        index = int(points[:,1].argmin()); point = points[index].copy();point[1] = max(.002,point[1])
        spec['regions'][name] = dict(mode='explicit',segments=[dict(start_frame=start,end_frame=end,
            vertex_id=int(ids[index]),space='world',position_m=point.tolist())])
    output.mkdir(parents=True)
    implementation = output/'implementation';implementation.mkdir()
    hashes = {}
    for p in (ROOT/'scripts').glob('*.py'):
        shutil.copyfile(p,implementation/p.name);hashes[p.name] = sha256(p)
    inputs = {str(p):sha256(p) for p in source.rglob('*') if p.is_file()}
    inputs[str(ASSET)] = sha256(ASSET)
    protocol = dict(source=str(source),inputs=inputs,implementation=hashes,contact_spec=spec,
        edit_window=list(window),anchor_frame=anchor,outer_stages=stages,iterations_per_stage=iterations,
        config=CONFIG,root_coordinate_mode='physical_box',skin_backend='sparse',export_rate_guard=rate_guard,export_point_rate_guard=point_rate_guard,
        scope='Authored ground-space foot pins, then the existing rigid carry transform. Original motion is the initializer and edit reference. Other contact regions disabled; no original box/hand interaction constraint. Not trained, held-out, physically simulated or human reviewed.')
    save(output/'protocol.json',protocol)
    save(output/'owner.json',dict(pid=os.getpid(),create_time=psutil.Process().create_time()))
    save(output/'status.json',dict(status='running'))
    try:
        began = time.perf_counter()
        with worker_lock():
            candidate, recipe = refine(raw,raw,skin,
                lambda row: print(dict(evaluations=row['evaluations'],loss=row['loss'],seconds=time.perf_counter()-began),flush=True),
                raw=raw,contact_spec=spec,outer_stage_count=stages,iteration_count=iterations,
                root_coordinate_mode='physical_box',skin_backend='sparse',edit_window=list(window),export_rate_guard=rate_guard,export_point_rate_guard=point_rate_guard)
        elapsed = time.perf_counter()-began
        save(output/'recipe.json',recipe)
        save(output/'native-targets.json',dict(source=evaluate(raw,raw,skin,spec,.005),candidate=evaluate(raw,candidate,skin,spec,.005)))
        relative = raw['local_rot_mats'].transpose(0,1,3,2)@candidate['local_rot_mats']
        angle = float(np.rad2deg(Rotation.from_matrix(relative.reshape(-1,3,3)).magnitude()).max())
        lift = candidate['root_positions'][:,1]-raw['root_positions'][:,1]
        bounds = dict(maximum_rotation_degrees=angle,minimum_root_lift_m=float(lift.min()),maximum_root_lift_m=float(lift.max()))
        assert angle <= CONFIG['max_rotation_degrees']+1e-4 and lift.min() >= -2e-7 and lift.max() <= CONFIG['max_root_lift_m']+2e-7
        depths = [max(0.,float(-surface.vertices(r,p)[:,1].min())) for r,p in zip(candidate['global_rot_mats'],candidate['posed_joints'])]
        validation = export_motion(output/'candidate',candidate,skin,SOMASkeleton77(),depths)
        save(output/'status.json',dict(status='auditing'))
        exported = audit(source/scene['actors']['A']['preview_glb'],output/'candidate/soma.glb',spec,window,frames)
        save(output/'export-audit.json',exported)
        # Preserve the original scene/prop/event bytes and replace only A's clip.
        prepared = output/'corrected-input';shutil.copytree(source,prepared)
        shutil.copyfile(output/'candidate/soma.glb',prepared/scene['actors']['A']['preview_glb'])
        shutil.copyfile(output/'candidate/motion.npz',prepared/scene['actors']['A']['motion'])
        scene['actors']['A']['source_sha256'] = sha256(prepared/scene['actors']['A']['motion'])
        save(prepared/'portable-scene.json',scene);write_runtime(prepared)
        carried = carry(prepared,output/'carried','A','platform',0)
        if any(sha256(p)!=h for p,h in inputs.items()):raise ValueError('Study input changed')
        if any(sha256(ROOT/'scripts'/n)!=h for n,h in hashes.items()):raise ValueError('Study implementation changed')
        result = dict(status='complete',seconds=elapsed,evaluations=recipe['evaluations'],bounds=bounds,
            export_validation=validation,carry_audit=carried,protocol_sha256=sha256(output/'protocol.json'),
            export_audit_sha256=sha256(output/'export-audit.json'),quality_approved=False)
        save(output/'completion.json',result);save(output/'status.json',dict(status='complete'))
        print(dict(seconds=elapsed,bounds=bounds,pins={v:row['pins'] for v,row in exported['variants'].items()}),flush=True)
        return result
    except Exception as exc:
        save(output/'status.json',dict(status='failed',error=str(exc)));raise


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--stages',type=int,default=2);p.add_argument('--iterations',type=int,default=60)
    p.add_argument('--rate-guard',action='store_true',help='Original-source global joint speed/acceleration inequalities; not per-foot limits')
    p.add_argument('--point-rate-guard',action='store_true',help='Per-material-point source ceilings for approach, hold and release')
    args=p.parse_args();run(args.source,args.output,stages=args.stages,iterations=args.iterations,rate_guard=args.rate_guard,point_rate_guard=args.point_rate_guard)
