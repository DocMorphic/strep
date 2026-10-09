"""Lightweight resource admission and owned-process supervision, not motion approval."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import psutil
from resource_admission import ResourcePolicy,Admission
from process_monitor import tree_rss,kill_tree
from action_worker_lock import worker_busy
from strep import ROOT,save,sha256,now,offline_environment

METHODS=['run_guarded_job.py','resource_admission.py','process_monitor.py','action_worker_lock.py','strep.py']


def run(worker,output,policy,*,worker_args=None):
    if not isinstance(policy,ResourcePolicy):raise ValueError('Explicit resource policy required')
    worker=Path(worker).resolve();output=Path(output).resolve()
    worker_args=[] if worker_args is None else worker_args
    if (not isinstance(worker_args,list) or any(type(a) is not str or '\0' in a for a in worker_args)
            or sum(len(a) for a in worker_args)>30000):
        raise ValueError('Bounded literal worker arguments required')
    if (not worker.is_relative_to(ROOT.resolve()) or not output.is_relative_to(ROOT.resolve())
            or not worker.is_file() or worker.suffix!='.py' or worker.is_relative_to(output)):
        raise ValueError('Existing in-project Python worker and separate fresh guard output required')
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
    method_root=Path(__file__).resolve().parent
    for name in METHODS:shutil.copyfile(method_root/name,archive/name)
    shutil.copyfile(worker,archive/'worker-source.py')
    methods={name:sha256(archive/name) for name in METHODS};worker_digest=sha256(worker)
    argument_digest=hashlib.sha256(json.dumps(worker_args,ensure_ascii=False).encode('utf-8')).hexdigest()
    protocol=dict(schema='strep-guarded-job-v1',at=now(),worker=worker.relative_to(ROOT).as_posix(),worker_sha256=worker_digest,
        worker_args_sha256=argument_digest,policy=asdict(policy),required_available_bytes=policy.required_available_bytes,
        methods_sha256=methods,scope='Admission and owned process completion only. Child retains its job lock and immutable motion protocol. Other applications can change RAM after admission. No motion, GPU/VRAM, import or human approval.',
        quality_approved=False,release_approved=False)
    save(output/'protocol.json',protocol)
    status=dict(status='waiting_resources',started_at=now(),supervisor_pid=__import__('os').getpid(),
        peak_process_tree_rss_bytes=0,resource_samples=0,worker_started=False,
        protocol_sha256=sha256(output/'protocol.json'),quality_approved=False,release_approved=False)
    started=time.monotonic();status['started_monotonic']=started
    admission=Admission(policy,started);process=None
    trace=output/'resource-samples.jsonl';trace.touch(exist_ok=False)
    def sample(phase,rss=None):
        clock=time.monotonic()
        available=int(psutil.virtual_memory().available)
        record=dict(phase=phase,clock=clock,available_bytes=available)
        if rss is not None:record['tree_rss_bytes']=rss
        with trace.open('a',encoding='utf-8') as stream:stream.write(json.dumps(record,allow_nan=False)+'\n')
        status.update(available_bytes=available,resource_samples=status['resource_samples']+1,last_observed_at=now())
        return clock,available
    def finish(state,reason=None):
        status.update(status=state,reason=reason,finished_at=now(),elapsed_seconds=time.monotonic()-started)
        status['resource_trace_sha256']=sha256(trace)
        save(output/'pipeline.json',status)
        return status
    try:
        while True:
            if worker_busy():return finish('deferred','owned_worker_busy')
            clock,available=sample('admission');readiness=admission.observe(clock,available)
            status.update(status=readiness,admission_elapsed_seconds=time.monotonic()-started,
                stable_since_seconds=None if admission.ready_since is None else admission.ready_since-started)
            save(output/'pipeline.json',status)
            if readiness=='deferred':return finish('deferred','admission_timeout')
            if readiness=='ready':break
            time.sleep(policy.poll_seconds)
        if sha256(worker)!=worker_digest:raise ValueError('Bound worker changed before launch')
        if worker_busy():return finish('deferred','owned_worker_busy')
        # Recheck RAM immediately before Popen; a low sample revokes admission.
        if sample('launch')[1]<policy.required_available_bytes:return finish('deferred','headroom_changed_before_launch')
        with (output/'worker.log').open('x',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-u',str(worker),*worker_args],cwd=ROOT,
                env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            status.update(status='processing',worker_started=True,worker_pid=process.pid)
            try:status['worker_created_at']=psutil.Process(process.pid).create_time()
            except psutil.NoSuchProcess:pass
            execution_started=time.monotonic();status['execution_started_monotonic']=execution_started
            save(output/'pipeline.json',status);reason=None
            while process.poll() is None:
                rss=tree_rss(process.pid);clock,available=sample('execution',rss);elapsed=clock-execution_started
                status.update(peak_process_tree_rss_bytes=max(status['peak_process_tree_rss_bytes'],rss),execution_seconds=elapsed)
                save(output/'pipeline.json',status)
                if available<policy.min_available_bytes:reason='available_ram_guard'
                elif rss>policy.max_tree_rss_bytes:reason='process_tree_rss_guard'
                elif elapsed>policy.max_seconds:reason='execution_time_guard'
                if reason:
                    kill_tree(process.pid,reap_parent=False);break
                time.sleep(policy.poll_seconds)
            status['exit_code']=process.wait()
        if sha256(worker)!=worker_digest or any(sha256(method_root/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):
            raise ValueError('Bound guard implementation or worker changed during execution')
        return finish('complete' if status['exit_code']==0 and reason is None else 'failed',reason)
    except BaseException as exc:
        if process is not None:
            if process.poll() is None:kill_tree(process.pid,reap_parent=False)
            status['exit_code']=process.wait()
        status.update(error_type=type(exc).__name__,error=str(exc))
        finish('failed','supervisor_exception')
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-rss-mib',type=int,required=True)
    p.add_argument('--stable-seconds',type=float,default=10);p.add_argument('--admission-seconds',type=float,default=60)
    p.add_argument('--max-seconds',type=float,default=3600);p.add_argument('--poll-seconds',type=float,default=1)
    p.add_argument('worker_args',nargs=argparse.REMAINDER);a=p.parse_args()
    policy=ResourcePolicy(a.expected_rss_mib*1024**2,stable_seconds=a.stable_seconds,
        admission_seconds=a.admission_seconds,max_seconds=a.max_seconds,poll_seconds=a.poll_seconds)
    args=a.worker_args[1:] if a.worker_args[:1]==['--'] else a.worker_args
    result=run(a.worker,a.output,policy,worker_args=args)
    print(json.dumps(result))
    return {'complete':0,'deferred':2,'failed':1}[result['status']]


if __name__=='__main__':raise SystemExit(main())
