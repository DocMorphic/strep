"""Tiny generated GLB/native-resource package to actual shared prop runtime.

Uses explicit test fixture generators, never production assets/model inference.
Headless engine evidence remains separate from CPU package tests and quality.
"""
import argparse,copy,json,shutil,subprocess,sys,zipfile
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts
from native_scene_game_tracks import export
from native_godot_payload import payload
from native_object_asset import export as export_object,ObjectAsset
from native_scene_runtime import configure
from scene_prop_runtime import package,GDS
from object_release import ENGINE
from release_geometry import floor_gaps
from study_scene_prop_ownership import observed_matrix
from strep import ROOT,now,read,save,sha256,offline_environment
from prop_runtime_collision import profile_document,verify_actual
from scene_collision_profile import PROFILES

AUDIT='godot_scene_prop_package_audit.gd'


def verify_event_bits(observed,events,times):
    expected={e['id']:np.asarray([times[e['sample_index']]],dtype='<f8').tobytes().hex() for e in events['events'] if e['runtime_dispatch_allowed']}
    for e in observed:assert e['source_time_f64le']==e['pose_time_f64le']==expected[e['id']]


def execute_study(output,physics_fps=120,collision_profile=None):
    if type(physics_fps) is not int or physics_fps not in (60,120,240):raise ValueError('Supported physics rate required')
    if collision_profile is not None:profile_document(collision_profile,physics_fps)
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'reports').resolve()) or output.exists():raise ValueError('Fresh local report directory required')
    sys.path.insert(0,str(ROOT/'tests'))
    from test_native_scene_runtime import fixture
    output.mkdir();save(output/'pipeline.json',dict(status='preparing',at=now()))
    methods=output/'methods';methods.mkdir();names=list(GDS)+[AUDIT,'native_godot_tracks.gd','godot_native_scene_observations.gd']
    hashes={n:sha256(ROOT/'scripts'/n) for n in names}
    for n in names:shutil.copyfile(ROOT/'scripts'/n,methods/n)
    python_names=['study_scene_prop_runtime.py','scene_prop_runtime.py','scene_prop_ownership.py','native_scene_runtime.py','native_scene_contacts.py','native_scene_game_tracks.py','native_godot_payload.py','native_object_asset.py','object_geometry.py','release_geometry.py','study_scene_prop_ownership.py','action_worker_lock.py','strep.py','prop_runtime_collision.py','scene_collision_profile.py']
    python_hashes={n:sha256(ROOT/'scripts'/n) for n in python_names}
    for n in python_names:shutil.copyfile(ROOT/'scripts'/n,methods/n)
    fixture_methods=output/'fixture-methods';fixture_methods.mkdir()
    fixture_hashes={p.name:sha256(p) for p in (ROOT/'tests').glob('*.py')}
    for n in fixture_hashes:shutil.copyfile(ROOT/'tests'/n,fixture_methods/n)
    fixture_folder=output/'fixture';fixture_folder.mkdir()
    folder,_,_,_,_,_,_,_=fixture(fixture_folder)
    game=output/'game-source';game.mkdir();shutil.copytree(folder/'actors',game/'actors');(game/'animations').mkdir()
    spec=read(folder/'scene.json');spec['objects']['authored']=copy.deepcopy(spec['objects']['item'])
    for k in spec['objects']['authored']['keyframes']:k['translation_m'][2]+=3
    save(game/'scene.json',spec);scene=SceneContacts(spec,game)
    export_object(scene,game/'objects.glb');asset=ObjectAsset(game/'objects.glb')
    times=np.unique(np.concatenate([read(folder/'root-motion.json')['times_s'],[1.305]]))
    game_request=read(folder/'game-tracks-request.json');game_request['markers'] += [dict(id='receiver',name='receive',actor='B',time_s=.8,confirmed=True),dict(id='drop',name='drop',actor='B',time_s=1.305,confirmed=True)]
    report,_=scene.evaluate();worlds={n:np.array([a['sampler'].sample(t)[a['rig'].joints] for t in times]) for n,a in scene.actors.items()}
    tracks=output/'tracks';source_spec=copy.deepcopy(spec)
    for n in source_spec['actors']:source_spec['actors'][n]['glb']=str(game/source_spec['actors'][n]['glb'])
    export(scene,game_request,times,worlds,report,tracks,source_spec=source_spec,portable_scene_sha256=sha256(game/'scene.json'),contact_report_sha256='a'*64)
    for n in ('root-motion.json','root-observations.npz','contacts.json','events.json'):shutil.copyfile(tracks/n,game/n)
    shutil.copyfile(tracks/'request.json',game/'game-tracks-request.json')
    prep_project=output/'prepare-project';prep_project.mkdir()
    for n in names:shutil.copyfile(methods/n,prep_project/n)
    (prep_project/'project.godot').write_text('config_version=5\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
    prep=dict(mode='prepare',actors=[dict(asset_path=str(game/spec['actors'][n]['glb']),animation_index=a['animation_index'],payload=payload(a['rig'],a['sampler'],spec['actors'][n]['sha256']),resource_path=str(game/f'animations/{n}.res')) for n,a in scene.actors.items()],
              objects=dict(asset_path=str(game/'objects.glb'),resource_path=str(game/'animations/objects.res'),duration_s=scene.duration,channels=asset.channels))
    save(output/'prepare-request.json',prep)
    with worker_lock():
        with (output/'compile.log').open('w',encoding='utf8') as log:
            run=subprocess.run([str(ENGINE),'--headless','--path',str(prep_project),'--check-only','--script',AUDIT],stdout=log,stderr=subprocess.STDOUT,timeout=30,env=offline_environment())
        if run.returncode:save(output/'pipeline.json',dict(status='failed',stage='compile',exit_code=run.returncode));raise RuntimeError('Inspect compile.log')
        with (output/'prepare.log').open('w',encoding='utf8') as log:
            run=subprocess.run([str(ENGINE),'--headless','--path',str(prep_project),'--script',AUDIT,'--',str(output/'prepare-request.json'),str(output/'prepared.json')],stdout=log,stderr=subprocess.STDOUT,timeout=60,env=offline_environment())
        if run.returncode:save(output/'pipeline.json',dict(status='failed',stage='native-resource-preparation',exit_code=run.returncode));raise RuntimeError('Inspect prepare.log')
    manifest=dict(schema='strep-native-scene-game-package-v1',files_sha256={p.relative_to(game).as_posix():sha256(p) for p in game.rglob('*') if p.is_file()},selected_animations={n:a['animation_index'] for n,a in scene.actors.items()},original_selected=True,quality_approved=False,release_approved=False,physics_verified=False,animation_runtime_playback_verified=False,root_removed_from_character_clips=False,root_application_mode='reference-only-motion-remains-embedded')
    save(game/'package.json',manifest);source=output/'game-assets.zip'
    with zipfile.ZipFile(source,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for p in game.rglob('*'):
            if p.is_file():archive.write(p,p.relative_to(game).as_posix())
    modes={'A':'embedded','B':'extracted'};config,_,_,events=configure(game,manifest,modes)
    p,r=scene.object_poses('item',np.array([0.]));initial=np.eye(4);initial[:3,:3]=r[0];initial[:3,3]=p[0]
    grips={}
    for key,n in [('AL','A'),('AR','A'),('BL','B')]:
        a=scene.actors[n];node=int(a['rig'].joints[0]);ap,ar=a['placement'];place=np.eye(4);place[:3,:3]=ar;place[:3,3]=ap
        offset=np.linalg.inv(place@a['sampler'].sample(0)[node])@initial
        grips[key]=dict(actor=n,joint_node=node,prop_offsets={'item':offset.tolist()})
    commands=[dict(event_id=e,object='item',grip=g,action=a) for e,g,a in [('marker:initial','AL','acquire'),('marker:initial','AR','acquire'),('marker:fraction','AL','release'),('marker:grasp','AR','release'),('marker:receiver','BL','acquire'),('marker:drop','BL','release')]]
    authored=dict(schema='strep-scene-prop-runtime-request-v1',source_game_zip_sha256=sha256(source),root_modes=modes,object_modes={'item':'grip-physics','authored':'authored'},grips=grips,commands=commands,
                  physics={'item':dict(mass_kg=2,friction=.6,restitution=0,linear_damping=0,angular_damping=0,collision_layer=1,collision_mask=1)},physics_fps=physics_fps,history_capacity=80)
    if collision_profile is not None:authored['collision_profile']=collision_profile
    save(output/'ownership-request.json',authored);packaged=package(source,output/'ownership-request.json',output/'runtime')
    project=output/'runtime/project'
    for n in (AUDIT,'native_godot_tracks.gd','godot_native_scene_observations.gd'):shutil.copyfile(methods/n,project/'ownership-v1'/n)
    results=[]
    for id,pos,angle in [('placed',[0,2,0],0),('rotated',[1,2,-1],30)]:
        place=np.eye(4);place[:3,3]=pos;place[:3,:3]=Rotation.from_euler('y',angle,degrees=True).as_matrix()
        request=dict(mode='audit',asset_folder=str(project),config=read(project/'ownership-v1/prop-runtime.json'),placement=place.tolist())
        req=output/(id+'-request.json');raw=output/(id+'-engine.json');save(req,request)
        with worker_lock(),(output/(id+'-engine.log')).open('w',encoding='utf8') as log:
            run=subprocess.run([str(ENGINE),'--headless','--path',str(project),'--fixed-fps',str(physics_fps),'--script','ownership-v1/'+AUDIT,'--',str(req),str(raw)],stdout=log,stderr=subprocess.STDOUT,timeout=90,env=offline_environment(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if run.returncode:save(output/'pipeline.json',dict(status='failed',stage=id,exit_code=run.returncode));raise RuntimeError('Inspect '+id+'-engine.log')
        actual=read(raw);assert not actual['faults'] and actual['malformed_rejected']==(14 if collision_profile is not None else 10) and actual['visibility']=={'item':False,'authored':True} and actual['extraction']=={'A':False,'B':True}
        assert actual['continuous_cd']=={'item':True}
        if collision_profile is not None:verify_actual(profile_document(collision_profile,physics_fps),actual['collision_settings'],physics_fps)
        else:assert actual['collision_settings']=={}
        records=actual['records'];actions=actual['actions'];assert len(actions)==8
        wanted=[e['id'] for e in events['events'] if e['runtime_dispatch_allowed']]
        assert [e['id'] for e in actual['events']]==wanted+[e['id'] for e in events['events'] if e['runtime_dispatch_allowed'] and times[e['sample_index']]<=1.4]
        assert [(a['before'],a['after']) for a in actions]==[([],['AL','AR']),(['AL','AR'],['AR']),(['AR'],['BL']),(['BL'],[])]*2
        assert all(e['source_time_s']==e['pose_time_s'] for e in actual['events'])
        verify_event_bits(actual['events'],events,times)
        assert all(set(r['props'])=={'item'} and set(r['scene']['objects'])=={'item','authored'} and set(r['scene']['actors'])=={'A','B'} for r in records)
        assert any('floor' in r['props']['item']['contacts'] for r in records)
        held=[];authored_errors=[];root_errors=[];previous={n:np.eye(4) for n in scene.actors}
        for row in records:
            t=row['source_time_s'];mat=scene.actors['A']['sampler'].sample(t);a=scene.actors['A'];ap,ar=a['placement'];actor_place=np.eye(4);actor_place[:3,:3]=ar;actor_place[:3,3]=ap
            target=place@actor_place@mat[grips['AL']['joint_node']]@np.array(grips['AL']['prop_offsets']['item'])
            if row['modes']['item']=='held' and row['transport']=='live':held.append(float(abs(np.array(row['props']['item']['pose'])-target).max()))
            p,r=scene.object_poses('authored',np.array([t]));expected=np.eye(4);expected[:3,:3]=r[0];expected[:3,3]=p[0]
            authored_errors.append(float(abs(observed_matrix(row['scene']['objects']['authored'])-place@expected).max()))
            for n in scene.actors:
                current=observed_matrix(row['scene']['actors'][n]['root_motion'])
                delta=np.linalg.inv(previous[n])@current if row['transport']=='live' and row['command'] not in ('restart','resume') else np.eye(4)
                root_errors.append(float(abs(np.array(row['physics_root_deltas'][n])-delta).max()))
                if row['transport']=='live':previous[n]=current
        assert max(held)<=3e-5 and max(authored_errors)<=3e-5 and max(root_errors)<=3e-5
        live=[r for r in records if r['session']==0 and r['transport']=='live'];poses=np.array([r['props']['item']['pose'] for r in live]);gap=floor_gaps(scene.objects['item']['geometry'],poses[:,:3,3],poses[:,:3,:3]);depth=float(max(0,-gap.min()))
        results.append(dict(id=id,records=len(records),actions=len(actions),malformed_rejected=actual['malformed_rejected'],collision_settings=actual['collision_settings'],held_pose_error=max(held),authored_pose_error=max(authored_errors),whole_step_root_error=max(root_errors),max_application_delay_s=max(a['application_delay_s'] for a in actions),exact_physical_event_timing_passed=all(abs(a['application_delay_s'])<=1e-12 for a in actions),max_floor_penetration_m=depth,discrete_collision_depth_screen_passed=depth<=.01,raw_sha256=sha256(raw),quality_approved=False,release_approved=False))
    boot_request=output/'boot-request.json';boot_raw=output/'boot-engine.json';save(boot_request,dict(mode='boot'))
    with worker_lock(),(output/'boot-engine.log').open('w',encoding='utf8') as log:
        run=subprocess.run([str(ENGINE),'--headless','--path',str(project),'--fixed-fps',str(physics_fps),'--script','ownership-v1/'+AUDIT,'--',str(boot_request),str(boot_raw)],stdout=log,stderr=subprocess.STDOUT,timeout=90,env=offline_environment(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if run.returncode:save(output/'pipeline.json',dict(status='failed',stage='exported_boot',exit_code=run.returncode));raise RuntimeError('Inspect boot-engine.log')
    boot=read(boot_raw);assert boot['parent_ready'] and not boot['faults'] and boot['actions']==4 and boot['samples']==3*physics_fps+1 and boot['floor_contact'] and boot['final_source_time_s']==scene.duration
    assert boot['continuous_cd']=={'item':True}
    if collision_profile is not None:verify_actual(profile_document(collision_profile,physics_fps),boot['collision_settings'],physics_fps)
    else:assert boot['collision_settings']=={}
    assert set(boot['actors'])==set(scene.actors) and boot['props']==['item']
    assert [e['id'] for e in boot['events']]==[e['id'] for e in events['events'] if e['runtime_dispatch_allowed']]
    assert all(e['source_time_s']==e['pose_time_s'] and e['parent_ready'] for e in boot['events'])
    verify_event_bits(boot['events'],events,times)
    boot['raw_sha256']=sha256(boot_raw)
    assert all(sha256(ROOT/'scripts'/n)==sha256(methods/n)==h for n,h in {**hashes,**python_hashes}.items())
    assert all(sha256(ROOT/'tests'/n)==sha256(fixture_methods/n)==h for n,h in fixture_hashes.items())
    assert all(sha256(project/'ownership-v1'/n)==h for n,h in hashes.items())
    with zipfile.ZipFile(output/'runtime/prop-runtime-assets.zip') as archive:
        assert all(sha256(project/n)==h for n,h in packaged['files_sha256'].items())
        assert all(archive.read(n)==(project/n).read_bytes() for n in packaged['files_sha256'])
    result=dict(schema='strep-scene-prop-runtime-study-v1',status='complete',at=now(),physics_fps=physics_fps,collision_profile=collision_profile,cases=results,boot=boot,engine_sha256=sha256(ENGINE),methods_sha256={**hashes,**python_hashes},fixture_methods_sha256=fixture_hashes,source_game_zip_sha256=sha256(source),packaged_zip_sha256=packaged['package_sha256'],source_and_copy_current=True,actual_glb_import=True,actual_native_resources=True,actual_physics=True,original_contact_measurements_retained=True,physical_contact_quality_approved=False,renderer_executed=False,human_reviewed=False,quality_approved=False,release_approved=False)
    save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));print(json.dumps(result));return result


def study(output,physics_fps=120,collision_profile=None):
    try:return execute_study(output,physics_fps,collision_profile)
    except Exception as exc:
        p=Path(output).resolve()/'pipeline.json'
        if p.exists() and read(p).get('status')!='failed':save(p,dict(status='failed',stage='fixture_or_verification',error=repr(exc),at=now()))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--physics-fps',type=int,choices=(60,120,240),default=120);parser.add_argument('--collision-profile',choices=tuple(PROFILES));args=parser.parse_args();study(args.output,args.physics_fps,args.collision_profile)
