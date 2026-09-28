"""Inject runtime ownership/step/pose faults into the actual engine consumer."""
from pathlib import Path
import copy
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from probe_godot_render import run_engine


def run():
    output=ROOT/'reports/godot-event-object-faults-v2';output.mkdir(exist_ok=False)
    project=output/'project';project.mkdir()
    source=ROOT/'reports/godot-event-object-v2'
    original=read(source/'request.json')
    for name, digest in original['executed_scripts'].items():
        if sha256(source/'project'/name)!=digest: raise ValueError('Validated source snapshot changed')
        shutil.copyfile(source/'project'/name,project/name)
    shutil.copyfile(source/'project/project.godot',project/'project.godot')
    shutil.copyfile(ROOT/'scripts/godot_event_object_fault_audit.gd',project/'godot_event_object_fault_audit.gd')
    shutil.copyfile(__file__,output/Path(__file__).name)
    cases=[]
    for fault in ('changed_step','outside_clock','nonrigid_grip'):
        item=copy.deepcopy(original['cases'][0])
        for k,h in [('path','glb_sha256'),('metadata','metadata_sha256')]:
            if sha256(item[k])!=item[h]: raise ValueError('Fixture changed')
        item.update(id=fault,fault=fault);cases.append(item)
    engine=Path(original['command'][0])
    if sha256(engine)!=original['engine_sha256']: raise ValueError('Engine changed')
    command=[str(engine),'--headless','--path',str(project),'--fixed-fps','60','--script','godot_event_object_fault_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')]
    request=dict(at=now(),cases=cases,physics_fps=60,command=command,engine_sha256=original['engine_sha256'],base_request_sha256=sha256(source/'request.json'),implementation={p.name:sha256(p) for p in project.glob('*.gd')},python_sha256=sha256(__file__),limits=dict(maximum_freeze_pose_error=1e-6),preflight_note='v1 compared to the injection boundary. Engine applies a changed tick rate after one additional valid old-rate step. Freeze must preserve the last valid recorded boundary immediately before the fault, not the earlier setting-change request. Consumer unchanged; v1 retained.')
    save(output/'request.json',request)
    run_engine(command,output/'engine.log',timeout=60)
    actual=read(output/'engine-output.json');checks=[]
    expected={'changed_step':'Physics step changed','outside_clock':'Another driver changed','nonrigid_grip':'Grip provider must return'}
    for item,case in zip(cases,actual['cases']):
        before=case['records'][-2];last=case['records'][-1]
        delta=float(np.max(np.abs(np.array(last['pose'])-before['pose'])))
        passed=bool(case['id']==item['fault'] and len(case['faults'])==1 and case['faults'][0].startswith(expected[item['fault']]) and before['transport']=='live' and abs(before['step_s']-1/60)<1e-8 and last['transport']=='fault' and last['collision_layer']==last['collision_mask']==0 and delta<1e-6 and np.linalg.norm(last['velocity'])==0 and np.linalg.norm(last['spin'])==0 and len(case['actions'])==2 and np.isfinite(np.array(last['pose'])).all())
        checks.append(dict(fault=item['fault'],passed=passed,reason=case['faults'],actions=len(case['actions']),freeze_pose_error=delta,valid_ticks_after_injection=before['tick']-case['before_fault']['tick']))
    passed=bool(len(checks)==3 and all(c['passed'] for c in checks))
    save(output/'verification.json',dict(at=now(),passed=passed,checks=checks,quality_approved=False,request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json')))
    print(dict(passed=passed,checks=checks))
    if not passed: raise ValueError('Fault containment checks failed')


if __name__=='__main__': run()
