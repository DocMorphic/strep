"""Actual shared scene playback, event ordering and transactional load audit."""
import argparse
import copy
from functools import lru_cache
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from scene_runtime import package
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from probe_godot_render import run_engine


@lru_cache(maxsize=12)
def sampler(path):
    doc,binary=read_glb(path)
    return doc,AnimationSampler(doc,binary,0)


def placement(value):
    matrix=np.eye(4);matrix[:3,:3]=Rotation.from_quat(value['rotation_xyzw']).as_matrix();matrix[:3,3]=value['translation_m'];return matrix


def verify(request,actual,output):
    checks=[];parent=np.eye(4);parent[:3,:3]=Rotation.from_euler('y',-.3).as_matrix();parent[:3,3]=[-1,.2,2]
    assert len(actual['cases'])==len(request['cases'])
    for item,case in zip(request['cases'],actual['cases']):
        assert item['id']==case['id'];folder=Path(item['folder']);data=read(folder/'scene-runtime.json')
        assert sha256(folder/'scene-runtime.json')==item['metadata_sha256']
        actor_errors={id:0. for id in data['actors']};object_errors={id:0. for id in data['objects']}
        records=case['records']+[e['observed'] for e in case['forward']+case['reverse']]
        for record in records:
            time=min(record['time_s'],(data['frames']-1)/30)
            assert set(record['actors'])==set(data['actors']) and set(record['objects'])==set(data['objects'])
            for id,entry in data['actors'].items():
                doc,sample=sampler(str(folder/entry['path']));world=sample.sample(time)
                names=[n.get('name') for n in doc['nodes']];order=[names.index(n) for n in case['bones'][id]]
                assert len(order)==len(set(order)) and set(order)==set(doc['skins'][0]['joints'])
                expected=parent@placement(entry['placement'])@world[order]
                actor_errors[id]=max(actor_errors[id],float(np.max(np.abs(np.array(record['actors'][id])-expected))))
            if data['objects']:
                doc,sample=sampler(str(folder/data['object_clip']['path']));world=sample.sample(time)
                for id,entry in data['objects'].items():
                    node=next(i for i,n in enumerate(doc['nodes']) if n.get('name')==entry['node_name'])
                    object_errors[id]=max(object_errors[id],float(np.max(np.abs(np.array(record['objects'][id])-parent@world[node]))))
        fwd=[e for e in case['forward'] if e['observed']['stage']=='forward']
        rev=[e for e in case['reverse'] if e['observed']['stage']=='reverse']
        expected=[e['id'] for e in data['markers']]
        events_ok=[e['id'] for e in fwd]==expected and [e['id'] for e in rev]==list(reversed(expected))
        events_ok &= all(abs(e['time_s']-e['frame']/30)<1e-12 and abs(e['observed_at_s']-e['observed']['time_s'])<1e-12 for e in fwd+rev)
        auto=[r['time_s'] for r in case['records'] if r['stage']=='automatic-forward']
        back=[r['time_s'] for r in case['records'] if r['stage']=='automatic-reverse']
        automation=bool(len(auto)>=10 and len(back)>=10 and np.allclose(np.diff(auto),1/60,rtol=0,atol=1e-10) and np.allclose(np.diff(back),-2/60,rtol=0,atol=1e-10) and case['paused_time_unchanged'] and case['automatic_reverse_silent'])
        passed=bool(max(actor_errors.values())<1e-4 and max(object_errors.values(),default=0)<1e-5 and events_ok and automation and case['silent_preview'] and case['no_terminal_repeat'] and case['unloaded'] and case['invalid_unchanged'] and all(case['invalid']) and all(e==44 for e in case['reentrant_errors']) and len([r for r in case['records'] if r['stage']=='forward'])==data['frames']*2+1)
        checks.append(dict(id=item['id'],passed=passed,actor_matrix_errors=actor_errors,object_matrix_errors=object_errors,pose_observations=len(records),event_order_passed=bool(events_ok),authored_events=len(expected),automatic_playback_passed=automation,callback_mutations_rejected=len(case['reentrant_errors']),unloaded=case['unloaded']))
    controls=actual['controls']
    controls_ok=len(controls)==len(request['controls']) and all(c['id']==e['id'] and c['error']!=0 and not c['bound'] and c['children']==0 and e['reason'] in c['reason'] for c,e in zip(controls,request['controls']))
    passed=bool(all(c['passed'] for c in checks) and controls_ok)
    save(output/'verification.json',dict(at=now(),passed=passed,checks=checks,controls=controls,control_rejection_passed=controls_ok,request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json'),quality_approved=False))
    return passed,checks


def run(output):
    output.mkdir(parents=True,exist_ok=False);project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep scene clock audit"\n',encoding='utf-8')
    implementation=output/'implementation';implementation.mkdir()
    names=['godot_scene_clock.gd','godot_scene_clock_audit.gd','scene_runtime.py','study_scene_runtime.py','rig_clip_import.py','gltf_tools.py','rig_asset.py','scene_object_export.py','scene_constraints.py','package_generated_scenes.py','strep.py','probe_godot_render.py']
    for name in names: shutil.copyfile(ROOT/'scripts'/name,implementation/name)
    for name in ('godot_scene_clock.gd','godot_scene_clock_audit.gd'): shutil.copyfile(ROOT/'scripts'/name,project/name)
    sources=[('paired',ROOT/'reports/frame-guarded-partner-v2/export/candidate.json'),('release',ROOT/'reports/scene-release-jobs/20260927-052950-518417bb/exports/trs-v1/portable-scene.json'),('platform',ROOT/'reports/scene-release-jobs/20260927-132952-35ac417f/portable-scene.json')]
    cases=[]
    for id,source in sources:
        folder=output/id;metadata=package(source,folder)
        cases.append(dict(id=id,folder=str(folder),frames=metadata['frames'],metadata_sha256=sha256(folder/'scene-runtime.json'),package_sha256=sha256(folder/'scene-runtime.zip')))
    controls=[]
    for fault,reason in [('actor_hash','Actor hash'),('object_owner','Object ownership'),('missing_node','Object node missing')]:
        target=output/('control-'+fault);shutil.copytree(output/'release',target)
        data=read(target/'scene-runtime.json')
        if fault=='actor_hash':next(iter(data['actors'].values()))['sha256']='0'*64
        if fault=='object_owner':next(iter(data['objects'].values()))['ownership']='live_physics'
        if fault=='missing_node':next(iter(data['objects'].values()))['node_name']='DeliberatelyMissing'
        save(target/'scene-runtime.json',data);controls.append(dict(id=fault,folder=str(target),reason=reason,deliberately_invalid=True))
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    if sha256(engine)!=read(engine.parent/'acquisition.json')['executables'][engine.name]:raise ValueError('Engine changed')
    command=[str(engine),'--headless','--path',str(project),'--fixed-fps','60','--script','godot_scene_clock_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')]
    request=dict(at=now(),cases=cases,controls=controls,command=command,engine_sha256=sha256(engine),implementation={n:sha256(implementation/n) for n in names},limits=dict(actor_matrix=1e-4,object_matrix=1e-5),scope='Three existing scene exports, placed actors and baked objects on one clock, transport/events/lifecycle. No live object physics, root extraction, rendering or contact quality approval.')
    save(output/'request.json',request);save(output/'pipeline.json',dict(at=now(),status='engine_running'))
    try: run_engine(command,output/'engine.log',timeout=120)
    except Exception as error:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(error)));raise
    passed,checks=verify(request,read(output/'engine-output.json'),output)
    save(output/'pipeline.json',dict(at=now(),status='complete' if passed else 'failed_comparison',passed=passed));print(dict(passed=passed,checks=checks))
    if not passed:raise ValueError('Scene runtime verification failed; retained evidence')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    run(parser.parse_args().output.resolve())
