"""Repair only the recorded joint-position axis error, preserving the failed run."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from inspect_motion import skeleton_metadata,validate_motion


def run(source,output):
    source,output=Path(source).resolve(),Path(output).resolve();request=read(source/'request.json')
    if output.exists() or not output.is_relative_to(ROOT):raise ValueError('Use a new project output folder')
    try:
        owner=psutil.Process(request['pid'])
        if owner.create_time()==request['created'] and owner.is_running():raise ValueError('Original exporter still running')
    except psutil.NoSuchProcess:pass
    state=read(source/'pipeline.json')
    if state['status']!='failed' or 'broadcast together' not in state['error']:raise ValueError('Not the recorded axis failure')
    manifest=read(source/'manifest.json');output.mkdir();shutil.copytree(source/'implementation',output/'implementation')
    shutil.copyfile(__file__,output/'implementation'/Path(__file__).name);shutil.copyfile(source/'request.json',output/'source-request.json');shutil.copyfile(source/'bounds.json',output/'bounds.json')
    repaired_request=copy.deepcopy(request);repaired_request.update(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),repair_source=str(source),source_request_sha256=sha256(source/'request.json'),source_failure_sha256=sha256(source/'pipeline.json'),fixed_exporter_sha256=sha256(ROOT/'scripts/export_bounded_wrist_motion.py'))
    repaired_request['implementation'][Path(__file__).name]=sha256(__file__);save(output/'request.json',repaired_request)
    names,_,_=skeleton_metadata(77);repairs=[]
    try:
        for seed in request['seeds']:shutil.copytree(source/f'seed-{seed}',output/f'seed-{seed}')
        for item in manifest['scenes']:
            scene=read(source/item['variants']['palm'])['scene']
            for actor,entry in scene['actors'].items():
                relative=Path(entry['motion']).relative_to(source.relative_to(ROOT));old=source/relative;dest=output/relative;glb=output/entry['preview_glb']
                if sha256(old)!=entry['source_sha256'] or sha256(glb)!=manifest['assets'][entry['preview_glb']]['sha256']:raise ValueError('Source actor changed')
                original=dict(np.load(old,allow_pickle=False));motion={k:v.copy() for k,v in original.items()};changed=not item['id'].startswith('raw-')
                if changed:
                    if motion['posed_joints'].shape!=(77,150,3):raise ValueError('Unexpected failed layout')
                    motion['posed_joints']=motion['posed_joints'].transpose(1,0,2).copy()
                    if any(not np.array_equal(motion[k],original[k]) for k in motion if k!='posed_joints'):raise ValueError('Repair changed another field')
                    np.savez_compressed(dest,**motion)
                validate_motion(motion,30)
                rig=RigAsset.load(glb);sampler=AnimationSampler(rig.document,rig.binary,0);nodes={n.get('name'):i for i,n in enumerate(rig.document['nodes'])};order=[nodes[n] for n in names]
                error=0.
                for frame in range(150):
                    world=sampler.sample(float(np.float32(frame/30)));ordered=np.take(world,order,axis=0)
                    error=max(error,float(np.abs(ordered[:,:3,3]-motion['posed_joints'][frame]).max()),float(np.abs(ordered[:,:3,:3]-motion['global_rot_mats'][frame]).max()))
                if error>1e-5:raise ValueError('Repaired arrays differ from actual exported animation')
                entry.update(motion=dest.relative_to(ROOT).as_posix(),source_sha256=sha256(dest));repairs.append(dict(scene=item['id'],actor=actor,changed_position_axes=changed,old_sha256=sha256(old),new_sha256=sha256(dest),decoded_max_error=error))
            save(output/item['variants']['palm'],dict(scene=scene))
        save(output/'manifest.json',manifest);save(output/'axis-repair-verification.json',dict(at=now(),rows=repairs,source_manifest_sha256=sha256(source/'manifest.json'),quality_approved=False))
        from run_godot_scene_import import run as engine
        save(output/'pipeline.json',dict(status='engine_import',quality_approved=False));engine(output,output/'engine-audit');checks=read(output/'engine-audit/verification.json')['checks']
        if len(checks)!=30 or any(c['frames']!=150 for c in checks):raise ValueError('Incomplete engine population')
        shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt');save(output/'pipeline.json',dict(status='complete_pending_geometry',engine_actor_frames=4500,quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.source,a.output)
