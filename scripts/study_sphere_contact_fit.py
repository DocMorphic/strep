"""Supervised v8 grasp fit of the recorded sphere-release development scene."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import psutil
from strep import ROOT,read,save,sha256,now
from process_monitor import tree_rss,kill_tree

SOURCE=ROOT/'reports/scene-release-jobs/sphere-development-v1/authored/palm.json'
LIMITS=dict(maximum_tree_rss_bytes=3*1024**3,minimum_system_available_bytes=int(1.25*1024**3),maximum_seconds=1800)


def worker(output):
    from run_scene_fit import run
    protocol=read(output/'protocol.json')
    for name,digest in protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Frozen study input changed: '+name)
    save(output/'worker.json',dict(pid=os.getpid(),created=psutil.Process().create_time(),at=now()))
    run([output/'source.json'],output/'fit',solver_version=8,preview_base=SOURCE.parent)
    for name,digest in protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Study input changed during fitting: '+name)


def study(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'reports'):raise ValueError('Study output must be under reports')
    output.mkdir(parents=True,exist_ok=False)
    source=read(SOURCE);shutil.copyfile(SOURCE,output/'source.json')
    files=[SOURCE,output/'source.json',Path(__file__),ROOT/'scripts/run_scene_fit.py']
    for entry in source['scene']['actors'].values():files.extend([ROOT/entry['motion'],SOURCE.parent/entry['preview_glb']])
    save(output/'protocol.json',dict(at=now(),inputs={p.relative_to(ROOT).as_posix():sha256(p) for p in files},
        solver_version=8,resource_limits=LIMITS,source_scene=SOURCE.relative_to(ROOT).as_posix(),
        comparison='Same actor input, object tracks and contact targets as the sphere release fixture; full floor/body preprocessing and v8 contact fit. No parameter tuning.',
        screens=dict(scene_contact_m=.03,solver_contact_m=.005,normal_degrees=15,skin_object_depth_m=.01),
        quality_approved=False,scope='One existing development motion; no held-out evidence, new generation or model training. Full mesh and temporal checks remain separate from objective.'))
    snapshot=output/'driver-snapshot';snapshot.mkdir()
    for name in ['study_sphere_contact_fit.py','run_scene_fit.py','process_monitor.py']:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    save(output/'pipeline.json',dict(status='starting',at=now(),quality_approved=False))
    command=[sys.executable,'-u',str(Path(__file__).resolve()),str(output),'--worker']
    start=time.monotonic();peak=0;reason=None
    with (output/'worker.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        identity=psutil.Process(process.pid).create_time()
        try:
            while process.poll() is None:
                rss=tree_rss(process.pid);peak=max(peak,rss);available=psutil.virtual_memory().available;elapsed=time.monotonic()-start
                save(output/'resource-supervisor.json',dict(at=now(),status='running',pid=process.pid,created=identity,
                    current_tree_rss_bytes=rss,peak_tree_rss_bytes=peak,available_bytes=available,elapsed_seconds=elapsed,limits=LIMITS))
                if rss>LIMITS['maximum_tree_rss_bytes']:reason='process_tree_memory_limit'
                elif available<LIMITS['minimum_system_available_bytes']:reason='system_memory_headroom'
                elif elapsed>LIMITS['maximum_seconds']:reason='elapsed_time_limit'
                if reason:kill_tree(process.pid);break
                time.sleep(1)
        finally:
            if process.poll() is None:kill_tree(process.pid)
        code=process.wait()
    status='interrupted_resource_guard' if reason else ('complete' if code==0 else 'failed')
    save(output/'resource-supervisor.json',dict(at=now(),status=status,pid=process.pid,created=identity,peak_tree_rss_bytes=peak,
        exit_code=code,reason=reason,elapsed_seconds=time.monotonic()-start,limits=LIMITS))
    save(output/'pipeline.json',dict(at=now(),status=status,exit_code=code,reason=reason,quality_approved=False))
    print(dict(output=str(output),status=status,exit_code=code,reason=reason),flush=True)
    return code or (15 if reason else 0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:worker(args.output.resolve())
    else:sys.exit(study(args.output))
