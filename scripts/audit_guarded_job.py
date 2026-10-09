"""Replay recorded resource admission/stop decisions; this cannot approve motion."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import math
import psutil
from resource_admission import ResourcePolicy
from strep import ROOT,read,sha256,save,now


def audit(folder):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(ROOT.resolve()):raise ValueError('In-project guard record required')
    p=read(folder/'protocol.json');s=read(folder/'pipeline.json')
    if p.get('schema')!='strep-guarded-job-v1' or s.get('status') not in ['complete','deferred','failed']:
        raise ValueError('Terminal versioned resource record required')
    if type(s.get('worker_started')) is not bool or type(s.get('resource_samples')) is not int:
        raise ValueError('Explicit worker and resource observation state required')
    if (sha256(folder/'protocol.json')!=s['protocol_sha256'] or sha256(folder/'resource-samples.jsonl')!=s['resource_trace_sha256']
            or sha256(folder/'implementation/worker-source.py')!=p['worker_sha256']
            or any(sha256(folder/'implementation'/n)!=h for n,h in p['methods_sha256'].items())
            or any(d.get(k) is not False for d in [p,s] for k in ['quality_approved','release_approved'])):
        raise ValueError('Immutable unapproved worker/implementation/resource bindings required')
    policy=ResourcePolicy(**p['policy']);required=policy.required_available_bytes
    if p['required_available_bytes']!=required:raise ValueError('Original admission reserve required')
    rows=[]
    with (folder/'resource-samples.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            if len(line)>4096 or len(rows)>=500000:raise ValueError('Bounded complete resource trace required')
            rows.append(json.loads(line))
    if len(rows)!=s['resource_samples']:raise ValueError('Every sampled resource observation required')
    started=s['started_monotonic'];previous=started;stable=None;ready=False;launch=False;reason=None;peak=0;expired=False
    if type(started) not in [int,float] or not math.isfinite(started):raise ValueError('Finite start clock required')
    for row in rows:
        clock=row['clock'];available=row['available_bytes'];phase=row['phase']
        if (type(clock) not in [int,float] or not math.isfinite(clock) or clock<previous
                or type(available) is not int or available<0 or phase not in ['admission','launch','execution']):
            raise ValueError('Complete monotonic sampled observations required')
        previous=clock
        if phase=='admission':
            if ready or launch or expired:raise ValueError('Admission cannot resume after its decision')
            expired=clock-started>=policy.admission_seconds
            if not expired:
                if available<required:stable=None
                elif stable is None:stable=clock
                ready=stable is not None and clock-stable>=policy.stable_seconds
        elif phase=='launch':
            if not ready or launch or expired:raise ValueError('Stable admitted state required before launch')
            launch=True
            if available<required:reason='headroom_changed_before_launch'
        else:
            if not launch or reason is not None:raise ValueError('No execution after revoked or stopped admission')
            rss=row['tree_rss_bytes']
            if type(rss) is not int or rss<0:raise ValueError('Complete process-tree sample required')
            peak=max(peak,rss);elapsed=clock-s['execution_started_monotonic']
            if elapsed<0:raise ValueError('Execution clock precedes process launch')
            if available<policy.min_available_bytes:reason='available_ram_guard'
            elif rss>policy.max_tree_rss_bytes:reason='process_tree_rss_guard'
            elif elapsed>policy.max_seconds:reason='execution_time_guard'
    if rows and rows[-1]['available_bytes']!=s['available_bytes']:raise ValueError('Final RAM sample differs')
    if s.get('stable_since_seconds')!=(None if stable is None else stable-started):raise ValueError('Stable margin clock differs')
    if peak!=s['peak_process_tree_rss_bytes']:raise ValueError('Whole process-tree peak differs')
    if s['status']=='deferred':
        expected='admission_timeout' if expired else ('headroom_changed_before_launch' if reason else 'owned_worker_busy')
        if s['reason']!=expected or s['worker_started'] or 'worker_pid' in s or (folder/'worker.log').exists():
            raise ValueError('Deferred jobs cannot start a worker')
    else:
        if not ready or not launch or not s['worker_started'] or s['reason']!=reason:
            raise ValueError('Recorded admission and runtime guard decision differ')
        if (s['status']=='complete')!=(s['exit_code']==0 and reason is None):raise ValueError('Exit/guard status differs')
        pid=s['worker_pid'];finished=datetime.fromisoformat(s['finished_at']).timestamp()
        if psutil.pid_exists(pid) and psutil.Process(pid).create_time()<=finished:
            raise ValueError('Recorded owned worker remains live')
    return dict(at=now(),status=s['status'],reason=s['reason'],observations_replayed=len(rows),worker_started=s['worker_started'],
        protocol_sha256=sha256(folder/'protocol.json'),pipeline_sha256=sha256(folder/'pipeline.json'),
        resource_trace_sha256=s['resource_trace_sha256'],required_available_bytes=required,all_archived_bindings_match=True,
        scope='Independent recorded policy/phase/clock/peak/stop/exit replay. Sampled RAM only; no guarantee between samples or against changing external load. No worker computation, motion, GPU/VRAM, engine or human approval.',
        quality_approved=False,release_approved=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();result=audit(a.folder)
    if a.output:save(a.output,result)
    print(json.dumps(result))
