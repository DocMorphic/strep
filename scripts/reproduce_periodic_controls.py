"""Reproduce the evaluated experiment in a new directory; not a new blind test."""
import argparse
import subprocess
import sys
from pathlib import Path
from strep import ROOT,read,save,sha256,now,offline_environment


def main(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    reference=ROOT/'reports/periodic-controls-v1'
    freeze=read(reference/'implementation-freeze.json')
    for name,digest in freeze['files'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise RuntimeError('Frozen implementation changed')
    save(output/'protocol.json',read(reference/'protocol.json'))
    freeze['reproduction']={'at':now(),'scope':'Seed 101 is now observed. Artifact reproduction, not a new held-out test.'}
    save(output/'implementation-freeze.json',freeze)
    study=str(ROOT/'benchmarks/periodic-arms-holdout-v1.json')
    stages=[('generate','run_profile_pilot.py',['--study',study,'--output',str(output/'holdout')]),
        ('process','process_profile_pilot.py',[str(output/'holdout'),'--study',study]),
        ('measure','profile_metrics.py',[str(output/'holdout'),'--study',study]),
        ('edit','run_periodic_controls.py',['--output',str(output)]),
        ('viewer','build_periodic_viewer.py',['--output',str(output)])]
    for name,script,args in stages:
        with (output/(name+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['node',str(ROOT/'scripts/validate_periodic_exports.mjs'),str(output)],cwd=ROOT,check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    main(parser.parse_args().output)
