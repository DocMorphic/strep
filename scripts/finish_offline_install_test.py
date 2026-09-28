"""Verify a new personal install after its exact builder exits; never restart it."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import time
import traceback
import psutil
from strep import ROOT,read,save,sha256,now


def run(installation,output,builder_pid,builder_created):
    installation,output=Path(installation).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve existing installation-test attempt')
    output.mkdir();save(output/'runner.json',dict(pid=os.getpid(),created=psutil.Process().create_time(),started_at=now()))
    save(output/'request.json',dict(installation=str(installation),builder_pid=builder_pid,builder_created=builder_created,script_sha256=sha256(__file__)))
    def phase(status):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False));print(status,flush=True)
    def command(name,args):
        phase(name)
        with (output/(name+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run(args,cwd=installation,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True)
    try:
        phase('waiting_for_exact_builder')
        while True:
            try:
                owner=psutil.Process(builder_pid)
                if owner.create_time()!=builder_created:raise RuntimeError(f'Builder identity mismatch: expected {builder_created!r}, observed {owner.create_time()!r}; do not infer termination')
                live=owner.is_running()
            except psutil.NoSuchProcess:live=False
            if not live:
                if read(installation/'build-status.json')['status']!='complete':raise RuntimeError('Builder ended before complete evidence')
                break
            time.sleep(5)
        executable=installation/'runtime/python/python.exe';environment=os.environ.copy()
        environment['PATH']=str(Path(environment.get('SystemRoot','C:/Windows'))/'System32')
        for name in ['PYTHONPATH','PYTHONHOME']:environment.pop(name,None)
        environment.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        command('integrity',[str(executable),'scripts/portable_launch.py','verify'])
        command('runtime_probe',[str(executable),'scripts/portable_launch.py','probe'])
        target=installation/'reports/offline-hand-posture-driver.py'
        shutil.copyfile(ROOT/'scripts/verify_offline_hand_posture.py',target)
        source=ROOT/'reports/rig-jobs/rig-diversity-height-v1-18'
        command('hand_posture',[str(executable),str(target),str(source/'transfer/character.glb'),str(source/'source')])
        proof=installation/'reports/offline-hand-posture-v1/completion.json'
        save(output/'completion.json',dict(at=now(),installation_manifest_sha256=sha256(installation/'installation.json'),
            integrity_sha256=sha256(installation/'reports/portable-integrity.json'),runtime_probe_sha256=sha256(installation/'reports/portable-runtime.json'),
            hand_workflow_sha256=sha256(proof),driver_sha256=sha256(target),restricted_path=environment['PATH'],
            quality_approved=False,new_model_inference=False,scope='Fresh local installation hashes/runtime isolation and imported-clip hand editing. No new inference or second-machine release qualification.'))
        phase('complete')
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('installation',type=Path);p.add_argument('output',type=Path);p.add_argument('--builder-pid',type=int,required=True);p.add_argument('--builder-created',type=float,required=True)
    a=p.parse_args();run(a.installation,a.output,a.builder_pid,a.builder_created)
