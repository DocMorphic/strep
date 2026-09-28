"""Finite runtime clock and prop physics on existing diverse non-looping clips."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_runtime_finite import write
from rig_asset import RigAsset
from rig_events import edit
from study_godot_event_object import verify
from probe_godot_render import run_engine


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    project=output/'project';project.mkdir()
    sources=['godot_cycle_adapter.gd','godot_finite_adapter.gd','godot_event_object_body.gd','godot_event_object_audit.gd','godot_finite_event_audit.gd']
    implementation=output/'implementation';implementation.mkdir()
    dependencies=sources+['rig_runtime_finite.py','rig_events.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','study_godot_event_object.py','study_godot_finite_events.py','probe_godot_render.py','strep.py']
    for name in dependencies: shutil.copyfile(ROOT/'scripts'/name,implementation/name)
    for name in sources: shutil.copyfile(ROOT/'scripts'/name,project/name)
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep finite event study"\n[physics]\n3d/physics_engine="GodotPhysics3D"\ncommon/physics_ticks_per_second=60\n',encoding='utf-8')
    cases=[]
    for source_id,terminal in [('motion-036-rig-01',False),('motion-011-rig-02',False),('motion-006-rig-03',False),('motion-006-rig-03',True)]:
        source=ROOT/'reports/breadth-transfer-v1/takes'/source_id
        id=source_id+('-terminal' if terminal else '')
        target=output/id;target.mkdir()
        for name in ('character.glb','report.json'): shutil.copyfile(source/name,target/name)
        report=read(target/'report.json');frames=report['frames'];last=frames-1
        if sha256(target/'character.glb')!=report['glb_sha256']: raise ValueError('Source GLB changed')
        release=last if terminal else last*3//5;attach=max(1,release-20)
        events=edit(dict(events=[]),[dict(id=id,name=id,frame=f,confirmed=True) for id,f in [('test-start',0),('test-grasp',attach),('test-release',release)]],report['glb_sha256'],frames)
        events['fixture_scope']='Machine-authored integration test; not human-reviewed motion, grip or contact quality.'
        save(target/'events.json',events);metadata=write(target)
        rig=RigAsset.load(target/'character.glb');names=[n.get('name') for n in rig.document['nodes']]
        hand='hand_r' if 'hand_r' in names else 'Skeleton_arm_joint_R__3_'
        cases.append(dict(id=id,path=str(target/'character.glb'),metadata=str(target/'runtime-finite.json'),hand=hand,attach_frame=attach,release_frame=release,end_tick=last*2+240,terminal_release=terminal,glb_sha256=sha256(target/'character.glb'),metadata_sha256=sha256(target/'runtime-finite.json'),source=str(source),source_report_sha256=sha256(source/'report.json')))
    for item in list(cases):
        skeleton_case=copy.deepcopy(item);skeleton_case.update(id=item['id']+'-skeleton',extract=False)
        cases.append(skeleton_case)
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    if sha256(engine)!=read(engine.parent/'acquisition.json')['executables'][engine.name]: raise ValueError('Engine changed')
    command=[str(engine),'--headless','--path',str(project),'--fixed-fps','60','--script','godot_finite_event_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')]
    request=dict(at=now(),cases=cases,physics_fps=60,command=command,engine_sha256=sha256(engine),implementation={n:sha256(implementation/n) for n in dependencies},limits=dict(matrix=2e-5,held_matrix=1e-6,transport_matrix=1e-6,velocity_m_s=.002,spin_rad_s=.002,physics_step=.0001),scope='Three existing finite actions on three rigs plus terminal-sample release, each in extracted/skeleton root mode; authored test event intent only. All source motion quality limitations remain.',preflight_note='v1 found real small-angle spin bug, fixed in consumer. v2 passed extracted modes. v3 skeleton preview rotation roundoff 1.192093e-7 exceeded implicit 1e-7; v4 explicitly freezes transport matrix tolerance 1e-6, matching held pose. All original attempts retained.')
    save(output/'request.json',request);save(output/'pipeline.json',dict(at=now(),status='engine_running'))
    run_engine(command,output/'engine.log',timeout=120)
    actual=read(output/'engine-output.json');passed,checks=verify(request,actual,output)
    clock_checks=[]
    for case in actual['cases']:
        contract=case['clock_contract'];item=next(i for i in cases if i['id']==case['id'])
        metadata=read(item['metadata'])
        expected=[(m['event_id'],m['phase_frame']/30) for m in metadata['markers']]
        forwards=[(e['event_id'],e['time_s']) for e in contract['forward']]
        backwards=[(e['event_id'],e['time_s']) for e in contract['reverse']]
        drift=float(np.max(np.abs(np.array(contract['terminal_bones'])-contract['held_bones'])))
        end_hold=[r for r in case['records'] if r['time_s']>metadata['duration_s'] and r['transport']=='live']
        def same_events(actual,expected):
            return len(actual)==len(expected) and all(a[0]==e[0] and abs(a[1]-e[1])<1e-12 for a,e in zip(actual,expected))
        valid=bool(same_events(forwards,expected) and same_events(backwards,list(reversed(expected))) and all(e['direction']==-1 for e in contract['reverse']) and len(contract['finished'])==1 and contract['silent_seek'] and contract['invalid_unchanged'] and all(contract['invalid_errors']) and drift<2e-5 and len(end_hold)>100)
        clock_checks.append(dict(id=case['id'],passed=valid,bones_held=len(contract['terminal_bones']),maximum_terminal_bone_matrix_drift=drift,forward_events=forwards,reverse_events=backwards,post_clip_physics_callbacks=len(end_hold),terminal_release=item['terminal_release']))
    passed=bool(passed and all(c['passed'] for c in clock_checks))
    base=read(output/'verification.json');base.update(passed=passed,clock_checks=clock_checks)
    save(output/'verification.json',base)
    save(output/'pipeline.json',dict(at=now(),status='complete' if passed else 'failed_comparison',passed=passed))
    print(dict(passed=passed,physics_checks=checks,clock_checks=clock_checks))
    if not passed: raise ValueError('Finite integration check failed; retained outputs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    run(parser.parse_args().output.resolve())
