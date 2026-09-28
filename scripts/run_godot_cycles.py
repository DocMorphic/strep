"""Verify runtime cycles against frozen repeated GLBs, then make portable packs."""
import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_runtime_cycle import write


def matrices(value):
    value=np.asarray(value);out=np.broadcast_to(np.eye(4),value.shape[:-2]+(4,4)).copy();out[...,:3,:3]=value[...,:3,:].swapaxes(-1,-2);out[...,:3,3]=value[...,3,:];return out


def payload_error(found,expected):
    """Godot JSON serializes doubles to 15 significant digits; IDs/frames stay exact."""
    if isinstance(expected,dict):
        assert set(found)==set(expected)
        return max([payload_error(found[k],v) for k,v in expected.items()]+[0.])
    if isinstance(expected,list):
        assert len(found)==len(expected)
        return max([payload_error(a,b) for a,b in zip(found,expected)]+[0.])
    if type(expected) is float:
        error=abs(found-expected);assert error<=1e-12;return error
    assert found==expected
    return 0.


def run(output,jobs):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);save(out/'pipeline.json',dict(status='processing'))
    try:
        project=out/'project';project.mkdir();(project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep cycle runtime audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
        for name in ('godot_cycle_adapter.gd','godot_cycle_audit.gd'):shutil.copyfile(ROOT/'scripts'/name,project/name)
        cases=[]
        for job in jobs:
            folder=ROOT/'reports/rig-jobs'/job;target=out/job;target.mkdir();result=read(folder/'result.json')
            variant=result['variants']['repeated'].get('source_variant','transfer')
            source=folder/variant;repeated=source/'repeated' if variant=='corrected' else folder/'repeated'
            for name in ('character.glb','report.json','timeline.json','root-motion.json','events.json'):shutil.copyfile(source/name,target/name)
            write(target)
            shutil.copyfile(folder/'character-animation.zip',target/'authoring-source.zip')
            data=read(target/'runtime-cycle.json');p=data['period_frames']
            probes=data['markers']+[dict(name=name,phase_frame=phase,first_cycle=0) for name,phase in [('synthetic_start',0),('synthetic_mid_a',p//2),('synthetic_mid_b',p//2),('synthetic_last',p-1)]]
            probes.sort(key=lambda e:e['phase_frame'])
            cases.append(dict(id=job,path=str(target/'character.glb'),metadata=str(target/'runtime-cycle.json'),repeated=str(repeated/'character.glb'),repeated_sha256=result['variants']['repeated']['sha256'],probe_markers=probes))
        save(out/'request.json',dict(cases=cases));engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
        with (out/'engine.log').open('w',encoding='utf8') as log:
            result=subprocess.run([str(engine),'--headless','--path',str(project),'--script','godot_cycle_audit.gd','--',str(out/'request.json'),str(out/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise ValueError('Godot failed; inspect engine.log')
        actual=read(out/'engine-output.json');checks=[]
        assert len(actual['cases'])==len(cases)
        for case,observed in zip(cases,actual['cases']):
            assert case['id']==observed['id'] and sha256(case['repeated'])==case['repeated_sha256']
            data=read(case['metadata']);p=data['period_frames'];rig=RigAsset.load(case['repeated']);sampler=AnimationSampler(rig.document,rig.binary,0);root=data['root_node'];anchor=sampler.sample(0)[root];desc=set(data['descendant_nodes']);runchecks=[]
            expected_events=[]
            for n in range(4):
                for marker in case['probe_markers']:
                    phase,first=marker['phase_frame'],marker['first_cycle']
                    if n>=first and n*p+phase<=3*p:expected_events.append({**marker,'cycle':n,'time_s':(n*p+phase)/30})
            for observed_run in observed['runs']:
                names={rig.document['nodes'][n]['name']:n for n in rig.joints};order=[names[n] for n in observed_run['bone_names']];assert set(order)==set(rig.joints)
                placement=matrices(observed_run['placement']);error=skin_error=root_error=0.
                for sample in observed_run['frames']:
                    t=sample['at_frame']/30;expected=sampler.sample(t);motion=expected[root]@np.linalg.inv(anchor);actual_bones=matrices(sample['bones']);desired=placement@expected[order]
                    for j,n in enumerate(order):
                        if observed_run['extracted'] and n not in desc:desired[j]=placement@motion@expected[n]
                    error=max(error,float(np.abs(actual_bones-desired).max()));root_error=max(root_error,float(np.abs(matrices(sample['motion'])-motion).max()),float(np.abs(matrices(sample['accumulated_delta'])-motion).max()))
                    # Independent skinning of observed engine bones; no assumed engine vertex ordering.
                    actual_world=expected.copy();actual_world[order]=np.linalg.inv(placement)@actual_bones
                    skin_error=max(skin_error,float(np.linalg.norm(rig.vertices(actual_world)-rig.vertices(expected),axis=1).max()))
                assert max(error,skin_error,root_error)<1e-4,(case['id'],observed_run['extracted'],error,skin_error,root_error)
                events=observed_run['events']
                assert len(events)==len(expected_events),(case['id'],observed_run['stride'],events,expected_events)
                serialization_error=0.
                for got,wanted in zip(events,expected_events):
                    assert abs(got['time_s']-wanted['time_s'])<1e-6
                    for key,value in wanted.items():
                        if key!='time_s':serialization_error=max(serialization_error,payload_error(got[key],value))
                assert observed_run['silent_seek'] and observed_run['rejected_invalid_steps']
                runchecks.append(dict(extracted=observed_run['extracted'],stride=observed_run['stride'],samples=len(observed_run['frames']),max_transform_error=error,max_cpu_skin_error_m=skin_error,max_root_transform_error=root_error,marker_count=len(events),max_payload_json_number_error=serialization_error,silent_seek=True))
            checks.append(dict(id=case['id'],glb_sha256=sha256(case['path']),reference_sha256=case['repeated_sha256'],runs=runchecks))
        for case in cases:
            target=out/case['id'];shutil.copyfile(ROOT/'scripts/godot_cycle_demo.gd',target/'godot_cycle_demo.gd')
            (target/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep cycle preview"\nrun/main_scene="res://main.tscn"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
            (target/'main.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://godot_cycle_demo.gd" id="1"]\n[node name="StrepCyclePreview" type="Node3D"]\nscript = ExtResource("1")\n',encoding='utf8')
            log_path=out/(case['id']+'-demo.log')
            with log_path.open('w',encoding='utf8') as log:
                demo=subprocess.run([str(engine),'--headless','--path',str(target),'--fixed-fps','60','--quit-after','240'],stdout=log,stderr=subprocess.STDOUT,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
            message=log_path.read_text(encoding='utf8')
            if demo.returncode or 'STREP_CYCLE_READY' not in message or 'STREP_MARKER cycle_boundary 1' not in message or 'ERROR:' in message:raise ValueError('Packaged demo did not start and play its first boundary: '+str(log_path))
        verification=dict(created_at=now(),engine=actual['engine'],checks=checks,packaged_demo='Headless main scene at fixed 60Hz for 240 frames; started and dispatched first cycle boundary.',implementation={n:sha256(ROOT/'scripts'/n) for n in ('godot_cycle_adapter.gd','godot_cycle_audit.gd','godot_cycle_demo.gd','rig_runtime_cycle.py','run_godot_cycles.py')},scope='Actual Godot single-cycle playback in world/extracted modes at half-frame, coarse and multi-cycle strides; compare transforms and CPU-skinned engine bones against frozen repeated GLBs. Synthetic event probes, silent seeks, restarts and rejected invalid steps. Not GPU, game collision or realism approval.')
        save(out/'verification.json',verification)
        for case in cases:
            target=out/case['id'];shutil.copyfile(out/'verification.json',target/'runtime-verification.json');files=[f for f in target.iterdir() if f.is_file()];package=target/'godot-cycle.zip'
            with zipfile.ZipFile(package,'x',zipfile.ZIP_DEFLATED) as z:
                for f in files:z.write(f,f.name)
            with zipfile.ZipFile(package) as z:
                assert z.testzip() is None
                for f in files:assert z.read(f.name)==f.read_bytes()
            save(target/'package.json',dict(sha256=sha256(package),glb_sha256=sha256(case['path']),files={f.name:sha256(f) for f in files}))
        save(out/'pipeline.json',dict(status='complete'));print(checks)
    except Exception as e:
        save(out/'pipeline.json',dict(status='failed',error=str(e)));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('jobs',nargs='+');a=p.parse_args();run(a.output,a.jobs)
