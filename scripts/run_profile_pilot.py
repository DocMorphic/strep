"""Supervise offline encoding and a resumable raw profile generation grid."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil
from strep import ROOT,read,save,now,offline_environment,sha256
from process_monitor import tree_rss,kill_tree
from profile_inputs import DEFAULT_STUDY,validate_study


def main(folder,study):
    config=validate_study(read(study))
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'models'/('prompt-cache-'+config['id'])
    status={'started_at':now(),'study_sha256':sha256(study),'status':'encoding','cache':str(cache),'peak_encoder_rss_bytes':0}
    save(folder/'pipeline.json',status)
    commands=[('encoding',[sys.executable,'-u',str(ROOT/'scripts/profile_encoder.py'),'--study',str(study),'--output',str(cache)]),
              ('generation',[sys.executable,'-u',str(ROOT/'scripts/generate_profiles.py'),'--study',str(study),'--cache',str(cache/'manifest.json'),'--output',str(folder/'raw')])]
    for stage,command in commands:
        status.update(status=stage);save(folder/'pipeline.json',status)
        with (folder/(stage+'.log')).open('a',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=ROOT,env=offline_environment(),stdout=stream,stderr=subprocess.STDOUT)
            reason=None
            try:
                while process.poll() is None:
                    rss=tree_rss(process.pid)
                    if stage=='encoding':status['peak_encoder_rss_bytes']=max(status['peak_encoder_rss_bytes'],rss)
                    if psutil.virtual_memory().available<600*1024**2 or rss>7*1024**3:
                        reason='memory_guard';kill_tree(process.pid);break
                    time.sleep(1)
            finally:
                if process.poll() is None:kill_tree(process.pid)
                code=process.wait()
            if code:
                status.update(status='failed',failed_stage=stage,reason=reason,exit_code=code,finished_at=now());save(folder/'pipeline.json',status)
                raise RuntimeError(f'{stage} failed; inspect retained log')
    status.update(status='raw_grid_complete',finished_at=now());save(folder/'pipeline.json',status)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,default=DEFAULT_STUDY);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.output,a.study)
