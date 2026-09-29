"""Supervise one Studio contact job; terminal state survives worker failure."""
import argparse
import os
from pathlib import Path
from strep import ROOT,read,save,now


def run(folder):
    folder=Path(folder).resolve()
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        request=read(folder/'edit-request.json')
        if request.get('kind')=='timing_check':
            from contact_timing_job import run as timing_check
            save(folder/'pipeline.json',dict(status='processing',kind='timing_check'))
            result=timing_check(folder)
            save(folder/'pipeline.json',dict(**result,finished_at=now()))
            return
        source=(ROOT/'reports'/request['source']).resolve()
        if not source.is_relative_to((ROOT/'reports').resolve()):raise ValueError('Source escapes reports')
        save(folder/'pipeline.json',dict(status='processing',started_at=now()))
        from run_contact_edit import run as edit
        edit(source,folder/'contact-spec.json',folder/'result')
        save(folder/'pipeline.json',dict(status='complete',finished_at=now()))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()))
        raise


def observed_state(folder):
    """A missing confirmed worker is terminal; a stale status file is not liveness."""
    import psutil
    folder=Path(folder);state=read(folder/'pipeline.json') if (folder/'pipeline.json').exists() else {'status':'unknown'}
    if state['status'] not in ['starting','processing'] or not (folder/'worker.json').exists():return state
    identity=read(folder/'worker.json')
    try:
        process=psutil.Process(identity['pid'])
        live=process.is_running() and abs(process.create_time()-identity['created_at'])<.001
    except psutil.NoSuchProcess:live=False
    except psutil.AccessDenied:return state
    if not live:
        state=dict(status='failed',error='Local contact worker exited before completing the job.',finished_at=now())
        save(folder/'pipeline.json',state)
    return state


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);run(p.parse_args().folder)
