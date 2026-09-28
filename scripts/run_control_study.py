"""Resume stage-complete calibration artifacts, preserving partial failures."""
import subprocess
import sys
import time
from pathlib import Path
from strep import ROOT,read,save,sha256,now,offline_environment
from apply_control_study import FOLDER,STUDY


def main():
    started=now()
    while True:
        state=read(FOLDER/'text/pipeline.json')
        if state['status']=='raw_grid_complete':break
        if state['status']=='failed':raise RuntimeError('Raw generation failed; inspect retained logs')
        time.sleep(5)
    # Freeze implementation before applying controls to any new seed.
    freeze=FOLDER/'implementation-freeze.json'
    hashes={name:sha256(ROOT/'scripts'/name) for name in ['motion_controls.py','apply_control_study.py','correct_loops.py','correct_stance.py','profile_metrics.py','retarget_cesium.py']}
    if freeze.exists():
        if read(freeze)['files']!=hashes:raise RuntimeError('Frozen implementation changed')
    else:save(freeze,{'frozen_at':now(),'study_sha256':sha256(STUDY),'files':hashes,'held_out_seed':55})
    commands=[('process-text',[sys.executable,'scripts/process_profile_pilot.py',str(FOLDER/'text'),'--study',str(STUDY)],FOLDER/'text/stance/neutral/summary.json'),
        ('measure-text',[sys.executable,'scripts/profile_metrics.py',str(FOLDER/'text'),'--study',str(STUDY)],FOLDER/'text/summary.json'),
        ('edit',[sys.executable,'scripts/apply_control_study.py'],FOLDER/'direct/summary.json')]
    for method in ['text','direct']:
        for stage,script,result in [('export','export_profile_characters.py','character-summary.json'),('measure-rig','measure_profile_characters.py','character-quality.json')]:
            commands.append((stage+'-'+method,[sys.executable,'scripts/'+script,str(FOLDER/method)],FOLDER/method/result))
        commands.append(('validate-'+method,['node','scripts/validate_profile_exports.mjs',str(FOLDER/method)],FOLDER/method/'gltf-validation-summary.json'))
    for stage,cmd,marker in commands:
        status={'started_at':started,'stage':stage,'status':'running','command':cmd};save(FOLDER/'execution.json',status)
        # Stage markers can be incrementally written: only this journal marks a stage complete.
        journal=FOLDER/'stages'/f'{stage}.json'
        if journal.exists() and read(journal).get('status')=='complete':continue
        with (FOLDER/(stage+'.log')).open('a',encoding='utf-8') as log:
            result=subprocess.run(cmd,cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT)
        status.update(status='complete' if result.returncode==0 else 'failed',exit_code=result.returncode,finished_at=now())
        save(journal,status);save(FOLDER/'execution.json',status)
        if result.returncode:raise RuntimeError('Stage failed: '+stage)
    save(FOLDER/'execution.json',{'started_at':started,'finished_at':now(),'status':'artifacts_complete'})


if __name__=='__main__':main()
