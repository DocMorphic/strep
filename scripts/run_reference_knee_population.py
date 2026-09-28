"""Serialize the predeclared knee reference-method cohort and decoded audits."""
import argparse
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
import psutil
from action_worker_lock import worker_lock
from audit_temporal_knee_patch import run as audit
from compare_reference_temporal_knee import verified_audit, peaks
from probe_reference_knee_population import run as generate
from strep import ROOT, now, read, save, sha256


def run(output):
    if output.exists():
        raise ValueError('Preserve earlier populations')
    with worker_lock():
        source=ROOT/'reports/knee-contact-windows-v1'
        cases=read(source/'results.json')['rows']
        if len(cases)!=8 or len({c['id'] for c in cases})!=8:
            raise ValueError('Expected frozen eight-case cohort')
        pilot=ROOT/'reports/knee-contact-reference-v1'
        pilot_audit=ROOT/'reports/knee-contact-reference-audit-v1'
        record=verified_audit(pilot_audit)
        if record['case']!=cases[0]['id']:
            raise ValueError('Pilot is not first declared case')
        output.mkdir(parents=True)
        files=['run_reference_knee_population.py','probe_reference_knee_population.py',
               'audit_temporal_knee_patch.py','compare_reference_temporal_knee.py',
               'audit_knee_window_bounds.py','probe_knee_contact_windows.py']
        (output/'implementation').mkdir()
        for name in files:
            shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        save(output/'protocol.json',dict(at=now(),cases=[c['id'] for c in cases],
            source_sha256=sha256(source/'results.json'),
            first_case_reused=str(pilot), first_audit_sha256=sha256(pilot_audit/'verification.json'),
            implementation={f'scripts/{n}':sha256(ROOT/'scripts'/n) for n in files},
            scope='Development expansion, not held-out evaluation. Same objective, limits, four sweeps and 80 iterations per frame. Center-frame contact only; retain all failures.',
            quality_approved=False))
        save(output/'runner.json',dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time()))
        rows=[]
        for index,case in enumerate(cases):
            name=case['id']
            study=pilot if index==0 else output/'cases'/name
            audited=pilot_audit if index==0 else output/'audits'/name
            stage='reuse' if index==0 else 'generation'
            save(output/'pipeline.json',dict(at=now(),status='running',case=name,index=index,stage=stage,completed=len(rows)))
            try:
                if index:
                    generate(study,index)
                    stage='engine'
                    save(output/'pipeline.json',dict(at=now(),status='running',case=name,index=index,stage=stage,completed=len(rows)))
                    subprocess.run([sys.executable,str(ROOT/'scripts/run_godot_rig_import.py'),
                        '--study',str(study),'--output',str(study/'engine')],cwd=ROOT,check=True)
                    stage='audit'
                    save(output/'pipeline.json',dict(at=now(),status='running',case=name,index=index,stage=stage,completed=len(rows)))
                    audit(study,audited)
                result=verified_audit(audited)
                rows.append(dict(id=name,status='complete',reused=index==0,study=str(study),audit=str(audited),
                    verification_sha256=sha256(audited/'verification.json'),peaks=peaks(audited),
                    **{k:result[k] for k in ['floor_worst','center_contact_errors_m','dense_floor_passed',
                        'center_contact_passed','candidate_pose_bounds_passed','window_step_bounds_passed',
                        'global_step_bounds_passed','outside_matrix_max_error','engine_actor_frames']},
                    ordered_posture_proxy=result['after_posture']['upright_kneel_upright_proxy_present']))
            except Exception as exc:
                failure=dict(at=now(),id=name,stage=stage,error=str(exc),traceback=traceback.format_exc())
                save(output/'failures'/f'{name}.json',failure)
                rows.append(dict(id=name,status='failed',stage=stage,error=str(exc)))
                print(failure,flush=True)
            save(output/'results.json',dict(at=now(),rows=rows,quality_approved=False))
        failures=sum(r['status']!='complete' for r in rows)
        save(output/'pipeline.json',dict(at=now(),status='complete_with_failures' if failures else 'complete',
            planned=len(cases),complete=len(rows)-failures,failed=failures,quality_approved=False))
        print(dict(complete=len(rows)-failures,failed=failures),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    run(parser.parse_args().output.resolve())
