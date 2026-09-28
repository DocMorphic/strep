"""Frozen all-seed support/reference comparison on the same two-rig inputs."""
import argparse
import os
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT, read, save, sha256, now
from study_breadth_contact import validate, SOURCES


def run(output):
    output=Path(output).resolve();baseline=ROOT/'reports/breadth-contact-v1'
    if output.exists():raise ValueError('Inspect and preserve earlier study')
    original=validate(baseline)
    names=[*SOURCES,'study_support_reference.py','support_reference_fit.py']
    output.mkdir();(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    protocol=dict(at=now(),baseline=str(baseline),baseline_protocol_sha256=sha256(baseline/'protocol.json'),cases=original['cases'],
        method='support_reference',planned_candidates=10,support_weight=40.,max_sweeps=6,
        change='Horizontal input-reference penalty multiplied by sqrt(1-drafted_support_weight). All other objective terms, guides, bounds and sweep budgets retained.',
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Same five jab-cross-retreat development seeds on both rigs; all attempts retained. Compare only after full population and source-matched validation. No held-out action or anatomy/semantic/physical/human claim.')
    save(output/'protocol.json',protocol);save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json')))
    save(output/'runner.json',dict(pid=os.getpid(),created=psutil.Process().create_time(),at=now()))
    data=dict(rows=[dict(case=c['id'],status='pending') for c in protocol['cases']],quality_approved=False)
    save(output/'results.json',data)
    try:
        os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
        from support_reference_fit import run as fit
        from verify_breadth_contact import verify
        from run_godot_rig_import import run as engine
        for case in protocol['cases']:
            validate(baseline)
            for name,digest in protocol['implementation'].items():
                if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Frozen implementation changed: '+name)
            row=next(r for r in data['rows'] if r['case']==case['id']);row.update(status='fitting',started_at=now())
            save(output/'results.json',data);save(output/'pipeline.json',dict(status='fitting',case=case['id'],quality_approved=False))
            folder=output/'takes'/case['id']
            try:
                fit(case['source'],folder);proof=verify(folder)
                group=output/'engine-groups'/case['id'];group.mkdir(parents=True)
                save(group/'manifest.json',dict(cases=[dict(id=case['id']+'-'+mode,path=str(path),sha256=sha256(path),frames=case['motion']['frames'],fps=30)
                    for mode,path in [('input',folder/'input/character.glb'),('candidate',folder/'candidate/character.glb')]]))
                save(output/'pipeline.json',dict(status='engine',case=case['id'],quality_approved=False));engine(group,group/'audit')
                checks=read(group/'audit/verification.json')['checks']
                if len(checks)!=2 or any(c['frames']!=case['motion']['frames'] for c in checks):raise ValueError('Incomplete engine frames')
                row.update(status='complete',verification=proof,engine_sha256=sha256(group/'audit/verification.json'),engine_actor_frames=sum(c['frames'] for c in checks),finished_at=now())
            except Exception as exc:
                row.update(status='failed',error=str(exc),traceback=traceback.format_exc(),finished_at=now())
            save(output/'results.json',data);print(case['id'],row['status'],flush=True)
        save(output/'pipeline.json',dict(status='complete' if all(r['status']=='complete' for r in data['rows']) else 'complete_with_failures',quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
