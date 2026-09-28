"""Verify the next personal installation after its exact builder finishes."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import time
import traceback
import psutil
from strep import ROOT, read, save, sha256, now


def run(builder, fixtures, output):
    builder, fixtures, output = [Path(p).resolve() for p in (builder,fixtures,output)]
    owner=read(builder);installation=Path(owner['installation']);output.mkdir(parents=True,exist_ok=False)
    proc=psutil.Process()
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),builder=str(builder),builder_sha256=sha256(builder),
        owner=owner,fixtures=str(fixtures),fixtures_sha256=sha256(fixtures),driver_sha256=sha256(__file__),quality_approved=False)
    save(output/'request.json',request)
    environment=os.environ.copy();environment['PATH']=str(Path(environment.get('SystemRoot','C:/Windows'))/'System32')
    for name in ['PYTHONPATH','PYTHONHOME','HF_TOKEN','HUGGING_FACE_HUB_TOKEN']:environment.pop(name,None)
    environment.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    executable=installation/'runtime/python/python.exe'

    def phase(status):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False));print(status,flush=True)

    def command(name,args):
        phase(name)
        with (output/(name+'.log')).open('w',encoding='utf8') as log:
            subprocess.run([str(executable),*args],cwd=installation,env=environment,stdout=log,stderr=subprocess.STDOUT,
                check=True,creationflags=subprocess.CREATE_NO_WINDOW)

    try:
        phase('waiting_for_exact_builder')
        while True:
            try:
                p=psutil.Process(owner['pid'])
                if p.create_time()!=owner['created']:raise ValueError('Builder PID reused')
            except psutil.NoSuchProcess:break
            time.sleep(5)
        if read(installation/'build-status.json')['status']!='complete':raise ValueError('Incomplete build')
        if sha256(builder)!=request['builder_sha256'] or sha256(fixtures)!=request['fixtures_sha256']:
            raise ValueError('Test protocol changed')
        command('integrity_before',['scripts/portable_launch.py','verify'])
        shutil.copyfile(installation/'reports/portable-integrity.json',output/'integrity-before.json')
        command('runtime_probe',['scripts/portable_launch.py','probe'])
        shutil.copyfile(installation/'reports/portable-runtime.json',output/'runtime-probe.json')
        command('history_workflow',['scripts/verify_offline_generation_history.py',str(fixtures)])
        proof=read(installation/'reports/offline-generation-history-v1/completion.json')
        if proof['engine_actor_frames']!=455 or len(proof['packages'])!=4:raise ValueError('Portable workflow population differs')
        command('integrity_after',['scripts/portable_launch.py','verify'])
        shutil.copyfile(installation/'reports/portable-integrity.json',output/'integrity-after.json')
        save(output/'completion.json',dict(at=now(),installation=str(installation),
            installation_sha256=sha256(installation/'installation.json'),
            workflow_sha256=sha256(installation/'reports/offline-generation-history-v1/completion.json'),
            integrity_before_sha256=sha256(output/'integrity-before.json'),integrity_after_sha256=sha256(output/'integrity-after.json'),
            runtime_probe_sha256=sha256(output/'runtime-probe.json'),engine_actor_frames=455,packages=4,
            restricted_path=environment['PATH'],quality_approved=False,new_model_inference=False,
            scope='Fresh personal same-laptop copy with full integrity before/after, isolated runtime and metadata-preserving edits. No second-machine or motion-quality approval.'))
        phase('complete')
    except BaseException as exc:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['builder','fixtures','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.builder,a.fixtures,a.output)
