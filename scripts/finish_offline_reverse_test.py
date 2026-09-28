"""Await an exact personal-install builder, then verify relocated reverse playback."""
import argparse
import os
from pathlib import Path
import subprocess
import traceback
import psutil
from strep import ROOT,read,save,sha256,now


def run(installation,output,builder_pid,builder_created,fixtures):
    installation,output,fixtures=[Path(p).resolve() for p in [installation,output,fixtures]]
    if output.exists():raise ValueError('Preserve previous offline test')
    output.mkdir(parents=True);process=psutil.Process()
    save(output/'runner.json',dict(pid=process.pid,created=process.create_time(),at=now()))
    request=dict(at=now(),installation=str(installation),builder_pid=builder_pid,builder_created=builder_created,
        fixtures=str(fixtures),fixtures_sha256=sha256(fixtures),driver_sha256=sha256(__file__),quality_approved=False)
    save(output/'request.json',request)
    def phase(status):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False));print(status,flush=True)
    environment=os.environ.copy()
    environment['PATH']=str(Path(environment.get('SystemRoot','C:/Windows'))/'System32')
    for name in ['PYTHONPATH','PYTHONHOME','HF_TOKEN','HUGGING_FACE_HUB_TOKEN']:environment.pop(name,None)
    environment.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    executable=installation/'runtime/python/python.exe'
    def command(name,args):
        phase(name)
        with (output/(name+'.log')).open('w',encoding='utf8') as log:
            subprocess.run([str(executable),*args],cwd=installation,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        # Builder uses build-status.json rather than pipeline.json. Do not infer
        # its exit from an unchanged status file or an observation timeout.
        phase('waiting_for_exact_builder')
        import time
        while True:
            try:
                owner=psutil.Process(builder_pid)
                if owner.create_time()!=builder_created:raise RuntimeError('Builder PID reused; inspect exact owner')
                live=owner.is_running()
            except psutil.NoSuchProcess:live=False
            if not live:
                if read(installation/'build-status.json')['status']!='complete':raise RuntimeError('Builder ended without completed installation')
                break
            time.sleep(5)
        command('integrity_before',['scripts/portable_launch.py','verify'])
        command('runtime_probe',['scripts/portable_launch.py','probe'])
        if sha256(fixtures)!=request['fixtures_sha256']:raise ValueError('Fixture manifest changed')
        command('reverse_workflow',['scripts/run_reverse_cycles.py','reports/offline-reverse-v1','--fixtures',str(fixtures)])
        proof=read(installation/'reports/offline-reverse-v1/verification.json')
        local_request=read(installation/'reports/offline-reverse-v1/request.json')
        for case in local_request['cases']:
            for key in ['path','metadata','repeated']:
                if not Path(case[key]).resolve().is_relative_to(installation):raise ValueError('Executable workflow data escaped installation')
        command('integrity_after',['scripts/portable_launch.py','verify'])
        save(output/'completion.json',dict(at=now(),installation_manifest_sha256=sha256(installation/'installation.json'),
            integrity_sha256=sha256(installation/'reports/portable-integrity.json'),probe_sha256=sha256(installation/'reports/portable-runtime.json'),
            reverse_verification_sha256=sha256(installation/'reports/offline-reverse-v1/verification.json'),
            actor_transform_samples=sum(r['samples'] for c in proof['checks'] for r in c['runs']),restricted_path=environment['PATH'],
            quality_approved=False,new_model_inference=False,scope='Fresh same-laptop offline copy, full file integrity before/after, isolated Python/CUDA/source probe and installed Godot reverse playback on explicitly supplied data copied locally. Not second-machine, GPU-rendering, new inference, inverse gameplay or release qualification.'))
        phase('complete')
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('installation',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--builder-pid',type=int,required=True);p.add_argument('--builder-created',type=float,required=True);p.add_argument('--fixtures',type=Path,required=True)
    a=p.parse_args();run(a.installation,a.output,a.builder_pid,a.builder_created,a.fixtures)
