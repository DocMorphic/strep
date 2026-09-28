"""Repeat the frozen study in a fresh directory, never replacing prior results."""
import argparse
import subprocess
import sys
from pathlib import Path
from strep import ROOT,save,sha256,now,offline_environment


def main(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Choose a fresh output directory; existing artifacts are preserved')
    output.mkdir(parents=True)
    study=ROOT/'benchmarks/control-calibration-v1.json'
    stages=[('generate','run_profile_pilot.py',['--study',str(study),'--output',str(output/'text')]),
        ('process','process_profile_pilot.py',[str(output/'text'),'--study',str(study)]),
        ('metrics','profile_metrics.py',[str(output/'text'),'--study',str(study)])]
    for name,script,args in stages:
        with (output/(name+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,check=True)
    import apply_control_study as apply
    import analyze_control_study as analyze
    import build_control_viewer as viewer
    import verify_control_study as verify
    from export_profile_characters import main as export
    from measure_profile_characters import main as measure
    files=['motion_controls.py','apply_control_study.py','correct_loops.py','correct_stance.py','profile_metrics.py','retarget_cesium.py']
    save(output/'implementation-freeze.json',{'frozen_at':now(),'study_sha256':sha256(study),'files':{n:sha256(ROOT/'scripts'/n) for n in files},'held_out_seed':55,'scope':'Reproduction of previously evaluated protocol; not a newly blind held-out study.'})
    save(output/'analysis-freeze.json',{'frozen_at':now(),'implementation_sha256':sha256(ROOT/'scripts/analyze_control_study.py'),'rule_source_sha256':sha256(study)})
    for module in [apply,analyze,viewer,verify]:module.FOLDER=output
    apply.main()
    for method in ['text','direct']:
        export(output/method);measure(output/method)
        subprocess.run(['node',str(ROOT/'scripts/validate_profile_exports.mjs'),str(output/method)],cwd=ROOT,check=True)
    analyze.main();viewer.main();verify.main()
    save(output/'completion.json',{'status':'complete','completed_at':now(),'scope':'Artifact reproduction, not independent human validation.'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    main(p.parse_args().output)
