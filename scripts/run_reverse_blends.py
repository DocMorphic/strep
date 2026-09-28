"""Independent decoded-pose and marker oracle for reversible transitions."""
import argparse
from pathlib import Path
import shutil
import subprocess
import traceback
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from run_godot_cycles import matrices, payload_error
from run_cycle_blend_audit import periodic, blend_worlds


def crossings(case, policy, before, after, notify):
    reverse=after<before
    if reverse and not notify:return []
    rows=[]
    for label in ['a','b']:
        source=case[label];period=read(source['metadata'])['period_frames'];start=case['start_'+label]
        for cycle in range(int((start+max(before,after))//period)+1):
            for marker in source['probe_markers']:
                frame=cycle*period+marker['phase_frame'];at=frame-start
                crossed=after<=at<before if reverse else before<at<=after
                if cycle<marker['first_cycle'] or not crossed:continue
                weight=min(1.,max(0.,at/case['duration_frames']))
                if at>case['duration_frames']:accept=label=='b'
                elif policy=='silent':accept=False
                elif policy=='incoming':accept=label=='b'
                else:accept=(label=='b')==(2*at>=case['duration_frames'])
                if accept:
                    event=dict(**marker,cycle=cycle,time_s=frame/30.,source_clip=label,source_weight=weight if label=='b' else 1-weight)
                    if reverse:event['direction']=-1
                    rows.append((at,event))
    ordered=sorted(rows,key=lambda r:r[0])
    if reverse:ordered.reverse()
    return [r[1] for r in ordered]


def verify(case, actual):
    assert actual['id']==case['id'] and len(actual['runs'])==48
    assert {(r['extracted'],r['policy'],r['notify'],r['stride'],r['clock_unit']) for r in actual['runs']}=={(e,p,n,s,c) for e in [False,True] for p in ['dominant','incoming','silent'] for n in [False,True] for s in [11.,100.] for c in ['frames','seconds']}
    rigs=[RigAsset.load(case[k]['path']) for k in ['a','b']]
    samplers=[AnimationSampler(r.document,r.binary,0) for r in rigs]
    metadata=[read(case[k]['metadata']) for k in ['a','b']];rig=rigs[0];root=metadata[0]['root_node'];desc=set(metadata[0]['descendant_nodes'])
    initial=[periodic(s,m,case['start_'+k]) for s,m,k in zip(samplers,metadata,['a','b'])]
    anchor=initial[0][root];alignment=anchor@np.linalg.inv(initial[1][root])
    names={n.get('name'):i for i,n in enumerate(rig.document['nodes'])};cache={};checks=[]
    for run in actual['runs']:
        order=[names[n] for n in run['bone_names']];assert set(order)==set(rig.joints)
        assert len(run['stages'])==len(case['destinations']) and run['invalid_requests_preserve_state']
        placement=matrices(run['placement']);cursor=0.;error=root_error=skin_error=0.;count=forward=reverse=0
        for target,stage in zip(case['destinations'] if run['clock_unit']=='frames' else case['seconds_destinations'],run['stages']):
            begin=cursor;steps=[]
            while cursor!=target:
                cursor=max(cursor-run['stride'],target) if target<cursor else min(cursor+run['stride'],target);steps.append(cursor)
            assert [s['at_frame'] for s in stage['frames']]==steps
            for sample in stage['frames']:
                frame=sample['at_frame'];count+=1
                if frame not in cache:
                    worlds=[periodic(s,m,case['start_'+k]+frame) for s,m,k in zip(samplers,metadata,['a','b'])]
                    expected=blend_worlds(rig.parents,worlds,root,alignment,min(1.,frame/case['duration_frames']))
                    cache[frame]=(expected,expected[root]@np.linalg.inv(anchor))
                expected,motion=cache[frame];desired=placement@expected[order]
                if run['extracted']:
                    for j,node in enumerate(order):
                        if node not in desc:desired[j]=placement@motion@expected[node]
                found=matrices(sample['bones']);error=max(error,float(np.abs(found-desired).max()))
                root_error=max(root_error,float(np.abs(matrices(sample['motion'])-motion).max()),float(np.abs(matrices(sample['accumulated'])-motion).max()))
                observed=expected.copy();observed[order]=np.linalg.inv(placement)@found
                skin_error=max(skin_error,float(np.linalg.norm(rig.vertices(observed)-rig.vertices(expected),axis=1).max()))
            wanted=crossings(case,run['policy'],begin,target,run['notify'])
            payload_error(stage['reverse_events'] if target<begin else stage['forward_events'],wanted)
            assert not (stage['forward_events'] if target<begin else stage['reverse_events'])
            forward+=len(stage['forward_events']);reverse+=len(stage['reverse_events'])
        assert max(error,root_error,skin_error)<1e-4,(case['id'],run,error,root_error,skin_error)
        assert run['reentrant_rejections']==reverse
        checks.append(dict(clock_unit=run['clock_unit'],extracted=run['extracted'],policy=run['policy'],notify=run['notify'],stride=run['stride'],samples=count,forward_markers=forward,reverse_markers=reverse,max_transform_error=error,max_root_error=root_error,max_cpu_skin_error_m=skin_error,reentrant_rejections=reverse))
    return dict(id=case['id'],runs=checks)


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);project=output/'project';project.mkdir();(output/'implementation').mkdir()
    names=['godot_reverse_blend_audit.gd','godot_cycle_blend_audit.gd','godot_cycle_blend.gd','godot_cycle_adapter.gd','run_reverse_blends.py','run_cycle_blend_audit.py','run_godot_cycles.py','rig_asset.py','rig_clip_import.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    def phase(status,**details):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**details));print(status,flush=True)
    try:
        previous=ROOT/'reports/runtime-crossfade-v3';proof=read(previous/'verification.json');assert sha256(previous/'request.json')==proof['request_sha256']
        cases=read(previous/'request.json')['cases']
        for case in cases:
            for label in ['a','b']:
                for key,digest in [('path','glb_sha256'),('metadata','metadata_sha256')]:assert sha256(case[label][key])==case[label][digest]
            case['destinations']=[90.,25.5,10.,20.,5.5,0.,30.]
            case['seconds_destinations']=[90.25,25.25,10.25,20.25,5.25,0.,30.25]
        save(output/'request.json',dict(at=now(),cases=cases,implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False))
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep reverse crossfades"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        for name in names:
            if name.endswith('.gd'):shutil.copyfile(ROOT/'scripts'/name,project/name)
        phase('engine');engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
        with (output/'engine.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([str(engine),'--headless','--path',str(project),'--script','godot_reverse_blend_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or 'ERROR:' in (output/'engine.log').read_text(encoding='utf-8'):raise ValueError('Godot failed; inspect engine.log')
        phase('verifying');actual=read(output/'engine-output.json');assert len(actual['cases'])==len(cases)
        checks=[verify(case,got) for case,got in zip(cases,actual['cases'])]
        for name,digest in read(output/'request.json')['implementation'].items():assert sha256(ROOT/'scripts'/name)==digest
        save(output/'verification.json',dict(at=now(),checks=checks,request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json'),engine=actual['engine'],engine_exe_sha256=sha256(engine),quality_approved=False,scope='Latest retained transition, reverse through completed handover, partial reversal and forward replay. Both root modes, three event policies, explicit reverse notifications and silent default. No older transition history, interrupted blend, gameplay undo, physics or quality approval.'))
        phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
