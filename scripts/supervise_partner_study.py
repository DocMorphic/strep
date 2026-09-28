"""Preserve headroom for the existing generation worker during CPU audits."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import psutil
from strep import ROOT,read,save,now
from process_monitor import tree_rss,kill_tree


def run(output):
    output=Path(output).resolve()
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Study already started')
    command=[sys.executable,'-u',str(ROOT/'scripts/study_breadth_partners_v2.py'),'run','--output',str(output)]
    process=subprocess.Popen(command,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
    identity=psutil.Process(process.pid).create_time();peak=0;reason=None
    try:
        while process.poll() is None:
            rss=tree_rss(process.pid);peak=max(peak,rss);available=psutil.virtual_memory().available
            save(output/'resource-supervisor.json',dict(at=now(),child_pid=process.pid,child_created_at=identity,
                status='running',peak_tree_rss_bytes=peak,current_tree_rss_bytes=rss,available_system_bytes=available,
                maximum_tree_rss_bytes=int(2.5*1024**3),minimum_system_available_bytes=2*1024**3))
            if rss>2.5*1024**3 or available<2*1024**3:
                reason='CPU audit memory guard';kill_tree(process.pid);break
            time.sleep(1)
    finally:
        if process.poll() is None:kill_tree(process.pid)
    code=process.wait()
    save(output/'resource-supervisor.json',dict(at=now(),child_pid=process.pid,child_created_at=identity,status='stopped',
        peak_tree_rss_bytes=peak,exit_code=code,reason=reason))
    if reason:
        save(output/'pipeline.json',dict(status='interrupted_resource_guard',reason=reason,quality_approved=False))
        if (output/'runner.json').exists():
            r=read(output/'runner.json');r.update(status='terminated',finished_at=now());save(output/'runner.json',r)
        d=read(output/'results.json')
        for row in d['rows']:
            if row['status']=='running':row.update(status='interrupted_resource_guard',error=reason)
        save(output/'results.json',d)
    return code if code else (15 if reason else 0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);sys.exit(run(p.parse_args().output))
