"""Successive crossfades with cumulative placement and recycled source donors."""
import argparse
from pathlib import Path
import shutil
import subprocess
import traceback
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from run_godot_cycles import matrices,payload_error
from run_cycle_blend_audit import periodic,blend_worlds,expected_events


def verify(case,actual):
    assert actual['id']==case['id'] and len(actual['runs'])==6
    assert {(r['extracted'],r['stride']) for r in actual['runs']}=={(e,s) for e in [False,True] for s in [.5,11.,100.]}
    rigs={k:RigAsset.load(case[k]['path']) for k in ['a','b']}
    samplers={k:AnimationSampler(r.document,r.binary,0) for k,r in rigs.items()}
    metadata={k:read(case[k]['metadata']) for k in ['a','b']}
    rig=rigs['a'];root=metadata['a']['root_node'];desc=metadata['a']['descendant_nodes']
    assert np.array_equal(rig.parents,rigs['b'].parents)
    anchor=periodic(samplers['a'],metadata['a'],case['initial_frame'])[root]
    names={n.get('name'):i for i,n in enumerate(rig.document['nodes'])};checks=[];cache={}
    for run in actual['runs']:
        assert len(run['stages'])==len(case['stages'])
        placement=matrices(run['placement']);order=[names[n] for n in run['bone_names']]
        assert set(order)==set(rig.joints)
        alignment=np.eye(4);current='a';source_frame=case['initial_frame'];stage_checks=[]
        for index,(stage,got) in enumerate(zip(case['stages'],run['stages'])):
            target=stage['target'];a=samplers[current];b=samplers[target];ma=metadata[current];mb=metadata[target]
            at_start=alignment@periodic(a,ma,source_frame)[root]
            incoming_alignment=at_start@np.linalg.inv(periodic(b,mb,stage['target_frame'])[root])
            destinations=[];cursor=0.
            while cursor<stage['total_frames']:cursor=min(cursor+run['stride'],stage['total_frames']);destinations.append(cursor)
            assert [s['at_frame'] for s in got['frames']]==destinations
            assert got['start_preserved_state'] and abs(got['target_clock_s']-(stage['target_frame']+stage['total_frames'])/30.)<1e-12
            error=root_error=skin_error=0.
            for sample in got['frames']:
                frame=sample['at_frame'];key=(index,frame)
                if key not in cache:
                    world_a=periodic(a,ma,source_frame+frame);world_a[desc]=alignment@world_a[desc]
                    world_b=periodic(b,mb,stage['target_frame']+frame)
                    blended=blend_worlds(rig.parents,[world_a,world_b],root,incoming_alignment,min(1.,frame/stage['duration_frames']))
                    cache[key]=(blended,blended[root]@np.linalg.inv(anchor))
                expected,motion=cache[key];desired=placement@expected[order]
                if run['extracted']:
                    for j,node in enumerate(order):
                        if node not in desc:desired[j]=placement@motion@expected[node]
                found=matrices(sample['bones']);error=max(error,float(np.abs(found-desired).max()))
                root_error=max(root_error,float(np.abs(matrices(sample['motion'])-motion).max()),float(np.abs(matrices(sample['accumulated'])-motion).max()))
                observed=expected.copy();observed[order]=np.linalg.inv(placement)@found
                skin_error=max(skin_error,float(np.linalg.norm(rig.vertices(observed)-rig.vertices(expected),axis=1).max()))
            assert max(error,root_error,skin_error)<1e-4,(case['id'],index,run['extracted'],run['stride'],error,root_error,skin_error)
            event_case=dict(a=case[current],b=case[target],start_a=source_frame,start_b=stage['target_frame'],duration_frames=stage['duration_frames'],total_frames=stage['total_frames'])
            events=expected_events(event_case,stage['policy'])
            for event in events:event['source_clip']=current if event['source_clip']=='a' else target
            payload_error(got['events'],events)
            stage_checks.append(dict(stage=index,target=target,policy=stage['policy'],samples=len(destinations),markers=len(events),max_transform_error=error,max_root_error=root_error,max_cpu_skin_error_m=skin_error))
            alignment=incoming_alignment;current=target;source_frame=stage['target_frame']+stage['total_frames']
        assert run['reentrant_rejections']==sum(s['markers'] for s in stage_checks)
        checks.append(dict(extracted=run['extracted'],stride=run['stride'],stages=stage_checks,reentrant_rejections=run['reentrant_rejections']))
    return dict(id=case['id'],runs=checks)


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);project=output/'project';project.mkdir();(output/'implementation').mkdir()
    names=['godot_chained_blend_audit.gd','godot_cycle_blend_audit.gd','godot_cycle_blend.gd','godot_cycle_adapter.gd','run_chained_blends.py','run_cycle_blend_audit.py','run_godot_cycles.py','rig_asset.py','rig_clip_import.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    def phase(status,**details):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**details));print(status,flush=True)
    try:
        previous=ROOT/'reports/runtime-crossfade-v3';proof=read(previous/'verification.json')
        assert sha256(previous/'request.json')==proof['request_sha256']
        cases=[]
        for old in read(previous/'request.json')['cases']:
            for label in ['a','b']:
                for key,digest in [('path','glb_sha256'),('metadata','metadata_sha256')]:assert sha256(old[label][key])==old[label][digest]
            cases.append(dict(id=old['id'],a=old['a'],b=old['b'],initial_frame=old['start_a'],stages=[
                dict(target='b',target_frame=old['start_b'],duration_frames=20,total_frames=45,policy='dominant'),
                dict(target='a',target_frame=11,duration_frames=15,total_frames=40,policy='incoming'),
                dict(target='b',target_frame=2,duration_frames=12,total_frames=50,policy='silent')]))
        save(output/'request.json',dict(at=now(),cases=cases,predecessor_verification_sha256=sha256(previous/'verification.json'),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False))
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep chained crossfades"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        for name in names:
            if name.endswith('.gd'):shutil.copyfile(ROOT/'scripts'/name,project/name)
        phase('engine');engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
        with (output/'engine.log').open('w',encoding='utf8') as log:
            process=subprocess.run([str(engine),'--headless','--path',str(project),'--script','godot_chained_blend_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        if process.returncode or 'ERROR:' in (output/'engine.log').read_text(encoding='utf8'):raise ValueError('Godot failed; inspect engine.log')
        phase('verifying');actual=read(output/'engine-output.json');assert len(actual['cases'])==len(cases)
        checks=[verify(case,got) for case,got in zip(cases,actual['cases'])]
        for name,digest in read(output/'request.json')['implementation'].items():assert sha256(ROOT/'scripts'/name)==digest
        save(output/'verification.json',dict(at=now(),checks=checks,request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json'),engine=actual['engine'],engine_exe_sha256=sha256(engine),quality_approved=False,scope='Three chained forward handovers with recycled donors and varied policies, complete local bone/root/CPU skin comparison, coarse-step event oracle and reentrant-call rejection. No reverse blend, interruption, physics, GPU or motion-quality approval.'))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
