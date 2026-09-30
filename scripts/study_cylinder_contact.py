"""Measured Studio grasp study using a retained development character motion.

The new cylinder condition preserves actor assets and grip timing. Completion
means artifacts were measured, never that the generated interaction is usable.
"""
import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import psutil
from strep import ROOT,read,save,sha256,now
from process_monitor import tree_rss,kill_tree

SOURCE_URL='/files/object-release-v2/seed-11-original/palm.json'
LIMITS=dict(maximum_tree_rss_bytes=3*1024**3,minimum_system_available_bytes=int(1.25*1024**3),maximum_seconds=1200)


def prepare_study(output):
    from scene_release_job import source_metadata
    from scene_region_job import JOBS,metadata,prepare,bundle
    from object_geometry import Geometry
    from object_floor_placement import place_above_floor
    from scene_constraints import evaluate
    from build_soma_preview import ASSET
    from action_worker_lock import worker_busy
    import numpy as np
    output=Path(output).resolve()
    if output.parent!=JOBS.resolve():raise ValueError('Study must be a direct child of the Studio region jobs directory')
    if output.exists():raise FileExistsError(output)
    if worker_busy():raise ValueError('An existing local fitting worker is active')
    source=source_metadata(SOURCE_URL)
    original=source['bundle'];scene=copy.deepcopy(original['scene'])
    if len(scene['objects'])!=1 or scene['objects']['box'].get('size_m')!=[.4,.4,.4]:
        raise ValueError('Expected the recorded 0.4 metre development box')
    fixture=output.with_name(output.name+'-input');fixture.mkdir(parents=True,exist_ok=False)
    save(fixture/'original-bundle.json',original)
    for name,entry in scene['actors'].items():
        for field,path,filename in [('motion',ROOT/entry['motion'],'motion.npz'),('preview_glb',source['base']/entry['preview_glb'],'actor.glb')]:
            destination=fixture/'actors'/name/filename;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,destination)
            if sha256(destination)!=source['files'][path.resolve()]:raise ValueError('Actor changed during snapshot')
            entry[field]=destination.relative_to(ROOT if field=='motion' else fixture).as_posix()
        entry['source_sha256']=sha256(ROOT/entry['motion'])
    obj=scene['objects'].pop('box');obj.pop('shape');obj.pop('size_m')
    obj['geometry']=Geometry('cylinder',(.2,.4)).record()
    obj,placement=place_above_floor(obj,scene['frame_count'],clearance_m=.002,max_shift_m=.25)
    obj['trajectory_provenance']='Authored cylinder condition using a retained box track and a constant floor-clearance lift; not cylinder dynamics.'
    scene['objects']['can']=obj
    for contact in scene['contacts']:
        if contact['target']['space']!='object' or contact['target']['object']!='box':raise ValueError('Unexpected contact fixture')
        contact['target']['object']='can'
        Geometry.parse(obj['geometry']).local_surface_normal(contact['target']['point_m'])
    scene['id']='cylinder-grasp-development'
    scene['review_note']='Same recorded actor and contact timing; newly authored cylinder geometry and floor placement. Not cylinder-conditioned generation or an approved grasp.'
    with np.load(ASSET,allow_pickle=False) as data:skin=dict(data)
    save(fixture/'palm.json',bundle(scene,evaluate(scene,skin),skin))
    save(fixture/'manifest.json',dict(scenes=[dict(id='source',label='Cylinder grasp · authored input',variants=dict(palm='palm.json'),review_note=scene['review_note'])]))
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',fixture/'SOMA-preview-LICENSE.txt')
    url='/files/'+fixture.relative_to(ROOT/'reports').as_posix()+'/palm.json'
    info=metadata(url)
    if not info['contacts'] or any(not row['supported'] for row in info['contacts']):raise ValueError('Cylinder regional contact compiler rejected the condition')
    contacts=[dict(row['edit'],anchor_tolerance_m=.005) for row in info['contacts']]
    prepare(dict(source_url=url,revision=info['revision'],actor='A',label='Cylinder grasp · measured development',contacts=contacts),output)
    # Freeze all Python/Godot methods, including dependencies of the auditor.
    methods=output/'study-implementation';methods.mkdir()
    for pattern in ['*.py','*.gd']:
        for path in (ROOT/'scripts').glob(pattern):shutil.copyfile(path,methods/path.name)
    save(output/'study-protocol.json',dict(at=now(),source_url=SOURCE_URL,
        source_files={p.relative_to(ROOT).as_posix():v for p,v in source['files'].items()},
        fixture=fixture.relative_to(ROOT).as_posix(),fixture_sha256=sha256(fixture/'palm.json'),
        request_sha256=sha256(output/'request.json'),placement=placement,resource_limits=LIMITS,
        methods={p.name:sha256(p) for p in methods.iterdir()},
        condition='Radius 0.2 m, full height 0.4 m, original local side grips and frames 60–120 inclusive; suggested palm patches, 5 mm anchors and unchanged Studio regional limits. Standard Studio three-stage/40-iteration balanced fitting.',
        scope='One retained development character clip, preserved unchanged. No held-out samples or training. Object trajectory is prescribed; no force, reaction, anatomical or human-quality approval.',quality_approved=False))
    return output


def worker(output):
    from scene_region_job import run
    protocol=read(output/'study-protocol.json')
    if sha256(output/'request.json')!=protocol['request_sha256']:raise ValueError('Study request changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Study method changed: '+name)
    run(output)
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during study: '+name)


def study(output):
    output=prepare_study(output);start=time.monotonic();peak=0;reason=None
    with (output/'study-worker.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),str(output),'--worker'],cwd=ROOT,
                                 stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        identity=psutil.Process(process.pid).create_time()
        try:
            while process.poll() is None:
                rss=tree_rss(process.pid);peak=max(peak,rss);available=psutil.virtual_memory().available;elapsed=time.monotonic()-start
                save(output/'study-supervisor.json',dict(at=now(),status='running',pid=process.pid,created_at=identity,
                    tree_rss_bytes=rss,peak_tree_rss_bytes=peak,available_bytes=available,elapsed_seconds=elapsed))
                if rss>LIMITS['maximum_tree_rss_bytes']:reason='process_tree_memory_limit'
                elif available<LIMITS['minimum_system_available_bytes']:reason='system_memory_headroom'
                elif elapsed>LIMITS['maximum_seconds']:reason='elapsed_time_limit'
                if reason:kill_tree(process.pid);break
                time.sleep(1)
        finally:
            if process.poll() is None:kill_tree(process.pid)
        code=process.wait()
    status='interrupted_resource_guard' if reason else ('complete' if code==0 else 'failed')
    report=dict(at=now(),status=status,pid=process.pid,created_at=identity,exit_code=code,reason=reason,
                elapsed_seconds=time.monotonic()-start,peak_tree_rss_bytes=peak,quality_approved=False)
    save(output/'study-supervisor.json',report)
    if reason:save(output/'pipeline.json',dict(status='failed',error=reason,finished_at=now()))
    print(report,flush=True)
    return code or (15 if reason else 0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if args.worker:worker(args.output.resolve())
    else:sys.exit(study(args.output))
