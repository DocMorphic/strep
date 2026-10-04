"""Guarded local request execution; an immutable request snapshot per output."""
import argparse
import subprocess
import sys
import time
import shutil
from pathlib import Path
import psutil
from strep import ROOT,read,save,now,offline_environment,sha256
from action_requests import validate_batch,request_digest
from process_monitor import tree_rss,kill_tree


def run(request_path,folder):
    batch=validate_batch(read(request_path));folder=Path(folder).resolve()
    from scene_target_preflight import validate_preflight
    source_preflight=validate_preflight(Path(request_path).resolve().parent,batch)
    if folder!=Path(request_path).resolve().parent:validate_preflight(folder,batch)
    folder.mkdir(parents=True,exist_ok=True)
    snapshot=folder/'request.json'
    if snapshot.exists() and request_digest(read(snapshot))!=request_digest(batch):raise ValueError('Output belongs to a different request')
    save(snapshot,batch)
    if any('motion_profile' in r for r in batch['requests']):
        from motion_profile import brief
        save(folder/'motion-briefs.json',{r['id']:brief(r) for r in batch['requests'] if 'motion_profile' in r})
        implementation=folder/'profile-implementation';implementation.mkdir(exist_ok=True)
        for name in ['motion_profile.py','action_requests.py','generate_actions.py','action_encoder.py','run_actions.py','export_actions.py']:
            shutil.copyfile(ROOT/'scripts'/name,implementation/name)
    status={'status':'starting','started_at':now(),'request_sha256':request_digest(batch),'peak_process_tree_rss_bytes':0}
    if source_preflight is not None:status['scene_reference_preflight']=dict(audit_sha256=sha256(Path(request_path).resolve().parent/'target-preflight/audit.json'),
        mode=read(Path(request_path).resolve().parent/'freeze.json')['target_preflight_mode'],
        reference_screens_passed=source_preflight['reference_screens_passed'],quality_approved=False)
    save(folder/'pipeline.json',status)
    try:
        from generation_constraints import compile_guides
        for request in batch['requests']:
            if request.get('generation_constraints'):compile_guides(request)
    except Exception as exc:
        status.update(status='failed',failed_stage='pose_source_validation',error=str(exc),finished_at=now())
        save(folder/'pipeline.json',status);raise
    stages=[('encoding','action_encoder.py',[str(snapshot),str(folder/'conditioning')]),
            ('generation','generate_actions.py',[str(snapshot),str(folder)]),
            ('export','export_actions.py',[str(folder)])]
    for stage,script,args in stages:
        status.update(status=stage);save(folder/'pipeline.json',status)
        with (folder/(stage+'.log')).open('a',encoding='utf8') as log:
            process=subprocess.Popen([sys.executable,'-u',str(ROOT/'scripts'/script),*args],cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT)
            reason=None;started=time.monotonic()
            try:
                while process.poll() is None:
                    rss=tree_rss(process.pid);status['peak_process_tree_rss_bytes']=max(status['peak_process_tree_rss_bytes'],rss)
                    if psutil.virtual_memory().available<600*1024**2 or rss>7*1024**3 or time.monotonic()-started>3600:
                        reason='memory_or_time_guard';kill_tree(process.pid);break
                    time.sleep(1)
            finally:
                if process.poll() is None:kill_tree(process.pid)
                code=process.wait()
            if code or reason:
                status.update(status='failed',failed_stage=stage,reason=reason,exit_code=code,finished_at=now());save(folder/'pipeline.json',status)
                raise RuntimeError(f'{stage} failed; preserved log: {folder/(stage+".log")}')
    status.update(status='complete',finished_at=now());save(folder/'pipeline.json',status)


def main(request_path,folder):
    from action_worker_lock import worker_lock
    with worker_lock():
        run(request_path,folder)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.request,a.output)
