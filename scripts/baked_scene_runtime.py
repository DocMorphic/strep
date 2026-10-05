"""Package and audit saved actor/prop animation playback without live physics."""
import argparse,copy,json,shutil,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
from action_worker_lock import worker_lock
from native_scene_runtime import configure,METHODS as NATIVE_METHODS
from native_engine_clock import check_clock_wire,clock_wire
from native_object_asset import ObjectAsset
from scene_prop_runtime import matrix
from scene_prop_bake import ENGINE,ENGINE_SHA256,POSE_LIMIT,engine_run,decoded,member_hash,physical_clock
from strep import ROOT,read,save,sha256,now

GDS=('godot_baked_scene_player.gd','godot_baked_scene_loader.gd','godot_baked_scene_boot.gd','godot_baked_scene_audit.gd',
    'godot_native_scene_loader.gd','godot_native_scene_player.gd','godot_native_root_adapter.gd','godot_native_object_player.gd','godot_scene_game_events.gd','native_engine_clock.gd','native_godot_preview.gd')
METHODS=tuple(dict.fromkeys(NATIVE_METHODS+GDS+('baked_scene_runtime.py','scene_prop_bake.py','scene_prop_runtime.py','scene_prop_ownership.py','process_monitor.py','object_release.py','release_geometry.py','object_dynamics.py')))


def require(value,message):
    if not value:raise ValueError(message)


def unpack(source,destination,*,runtime=False):
    with zipfile.ZipFile(source) as z:
        names=z.namelist();require(len(names)==len(set(n.casefold() for n in names)) and len(names)<=512 and sum(i.file_size for i in z.infolist())<=1024**3,'Complete bounded unique baked ZIP required')
        require(all(n and not PurePosixPath(n).is_absolute() and '\\' not in n and ':' not in n and all(p not in ('','.','..') for p in n.split('/')) for n in names),'Portable baked ZIP paths required')
        manifest=json.loads(z.read('baked-runtime-v1/package.json' if runtime else 'package.json'))
        require(manifest['schema']==('strep-baked-scene-runtime-package-v1' if runtime else 'strep-baked-prop-assets-v1') and manifest['status']=='complete','Complete baked package required')
        manifest_name='baked-runtime-v1/package.json' if runtime else 'package.json'
        require(set(names)==set(manifest['files_sha256'])|{manifest_name},'Complete baked ZIP population required')
        require(all(member_hash(z,n)==h for n,h in manifest['files_sha256'].items()),'Baked ZIP member changed')
        destination.mkdir()
        for n in names:
            p=destination/n;p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(n) as src,p.open('xb') as dst:shutil.copyfileobj(src,dst)
    return manifest


def configure_bake(folder,manifest):
    require(manifest['original_selected'] is True and manifest['studio_selection_changed'] is False and all(manifest[k] is False for k in ('physics_quality_approved','animation_quality_approved','release_approved')),'Original unapproved baked source required')
    require(manifest['source_actors_unchanged'] is True and manifest['source_mesh_payload_unchanged'] is True and manifest['engine_import_verified'] is True,'Completed source-preserving bake required')
    composition=read(folder/'composition.json');original=read(folder/'reference/source-game-package.json')
    require(original['schema']=='strep-native-scene-game-package-v1' and original['original_selected'] is True and original['root_removed_from_character_clips'] is False
        and original['root_application_mode']=='reference-only-motion-remains-embedded' and all(original[k] is False for k in ('quality_approved','physics_verified','release_approved','animation_runtime_playback_verified')),'Original embedded game decisions required')
    require(set(n for n in manifest['files_sha256'] if n.startswith('reference/'))=={'reference/'+n for n in original['files_sha256']}|{'reference/source-game-package.json'},'Complete original references required')
    for n,h in original['files_sha256'].items():require(manifest['files_sha256']['reference/'+n]==h==sha256(folder/'reference'/n),'Original source file changed')
    spec=read(folder/'reference/scene.json');modes={n:'embedded' for n in spec['actors']}
    config,scene,times,events=configure(folder/'reference',original,modes)
    require(composition['schema']=='strep-baked-prop-composition-v1' and composition['source_duration_s']==scene.duration and all(composition[k] is False for k in ('quality_approved','release_approved')),'Original baked composition required')
    require(set(composition['objects']['modes'])==set(scene.objects) and all(v in ('authored','grip-physics') for v in composition['objects']['modes'].values()),'Complete baked prop choices required')
    actors={n:dict(**{**entry,'glb':'reference/'+entry['glb']},root_motion='original-embedded',end_policy='hold-original-end') for n,entry in spec['actors'].items()}
    require(composition['actors']==actors and composition['root_references']=='reference/root-motion.json' and composition['marker_intent']=='reference/events.json' and composition['contact_intent_scope']=='unchanged-authored-reference-only','Original actor/root/event/end references changed')
    parent=matrix(composition['parent_world_transform']);clock=np.frombuffer(bytes.fromhex(composition['clock']['bytes_hex']),dtype='<f8');check_clock_wire(composition['clock'],clock)
    rate=next((r for r in (60,120,240) if np.array_equal(clock,physical_clock(scene.duration,r))),None)
    require(rate is not None and composition['duration_s']==clock[-1],'Complete original physical clock required')
    check_clock_wire(composition['source_clock'],np.minimum(clock,scene.duration))
    require(composition['objects']['path']=='objects.glb' and composition['objects']['sha256']==manifest['files_sha256']['objects.glb']==sha256(folder/'objects.glb'),'Baked prop asset changed')
    asset=ObjectAsset(folder/'objects.glb');require(set(asset.objects)==set(scene.objects),'Complete saved baked prop population required')
    def relocated(entry):return dict(path='reference/'+entry['path'],sha256=entry['sha256'])
    entries=[]
    for item in config['actors']:entries.append({**item,'asset':relocated(item['asset']),'resource':relocated(item['resource'])})
    runtime=dict(schema='strep-baked-scene-runtime-v1',source_duration_s=scene.duration,duration_s=float(clock[-1]),physics_fps=rate,clock=clock_wire(clock),
        source_scene=relocated(config['scene']),events=relocated(config['events']),actors=entries,
        objects=dict(asset=dict(path='objects.glb',sha256=manifest['files_sha256']['objects.glb']),resource=dict(path='objects.res',sha256=manifest['files_sha256']['objects.res']),names=list(scene.objects)),parent_world_transform=parent,
        root_mode='original-embedded',actor_end_policy='hold-original-end',live_prop_physics=False,quality_approved=False,release_approved=False)
    return runtime,scene,asset,clock,events


def package(source,output):
    source=Path(source).resolve();output=Path(output).resolve();require(not output.exists(),'Fresh baked runtime output required')
    output.mkdir();save(output/'pipeline.json',dict(status='preparing',at=now()));methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
    try:
        source_digest=sha256(source);shutil.copyfile(source,output/'source-baked-assets.zip');require(sha256(output/'source-baked-assets.zip')==source_digest,'Baked source changed during snapshot');project=output/'project'
        original=unpack(output/'source-baked-assets.zip',project);config,_,_,_,_=configure_bake(project,original)
        runtime=project/'baked-runtime-v1';runtime.mkdir()
        for n in GDS:shutil.copyfile(ROOT/'scripts'/n,runtime/n)
        save(runtime/'runtime.json',config)
        (runtime/'scene.tscn').write_bytes(b'[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://baked-runtime-v1/godot_baked_scene_boot.gd" id="1"]\n[node name="StrepBaked" type="Node3D"]\nscript = ExtResource("1")\n')
        (project/'project.godot').write_bytes(b'config_version=5\n[application]\nrun/main_scene="res://baked-runtime-v1/scene.tscn"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        with zipfile.ZipFile(output/'source-baked-assets.zip') as z:
            require(all(sha256(project/n)==h for n,h in original['files_sha256'].items()) and sha256(project/'package.json')==member_hash(z,'package.json'),'Original baked assets changed')
        require(sha256(source)==sha256(output/'source-baked-assets.zip')==source_digest and all(sha256(ROOT/'scripts'/n)==h for n,h in methods.items()),'Baked source/methods changed')
        files={p.relative_to(project).as_posix():sha256(p) for p in project.rglob('*') if p.is_file()}
        require(len(files)<512 and sum((project/n).stat().st_size for n in files)<=1024**3,'Complete runtime package exceeds budget')
        m=dict(schema='strep-baked-scene-runtime-package-v1',status='complete',at=now(),source_baked_zip_sha256=source_digest,files_sha256=files,
            methods_sha256=methods,runtime_methods_sha256={n:methods[n] for n in GDS},source_bytes_unchanged=True,engine_executed=False,live_prop_physics=False,animation_quality_approved=False,release_approved=False)
        save(runtime/'package.json',m)
        with zipfile.ZipFile(output/'baked-runtime.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for n in list(files)+['baked-runtime-v1/package.json']:z.write(project/n,n)
        with zipfile.ZipFile(output/'baked-runtime.zip') as z:require(all(member_hash(z,n)==h for n,h in files.items()) and json.loads(z.read('baked-runtime-v1/package.json'))==m,'Runtime ZIP readback failed')
        result=dict(**m,package_sha256=sha256(output/'baked-runtime.zip'));save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
    except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=repr(exc),at=now()));raise


def evaluate(actual,config,scene,asset,queries,events):
    require(actual['schema']=='strep-baked-scene-audit-v1' and actual['faults']==[] and actual['collision_objects']==0 and actual['invalid_time_rejected'] and actual['moved_parent_rejected'],'Finite physics-free playback controls required')
    parent=np.asarray(config['parent_world_transform']);errors={'actor':0.,'object':0.};native=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')
    expected_events=[dict(id=e['id'],time_s=float(native[e['sample_index']])) for e in events['events'] if e['runtime_dispatch_allowed']]
    def roots_at(name,time):
        a=scene.actors[name];bone=next(e['root_bone'] for e in config['actors'] if e['id']==name)
        node=next(int(j) for j in a['rig'].joints if a['rig'].document['nodes'][int(j)]['name']==bone)
        return a['sampler'].sample(min(time,scene.duration))[node]@np.linalg.inv(a['sampler'].sample(0.)[node])
    def frame(row,time,previous=None):
        require(decoded(row['time_f64le'],1,'baked time')[0]==time and set(row['actors'])==set(scene.actors) and set(row['objects'])==set(asset.objects)
            and set(row['root_motion'])==set(scene.actors) and set(row['root_deltas'])==set(scene.actors),'Complete exact baked scene observation required')
        for n,a in scene.actors.items():
            observed=row['actors'][n];require(set(observed)=={a['rig'].document['nodes'][int(j)]['name'] for j in a['rig'].joints},'Complete source joint observation required')
            p,r=a['placement'];placement=np.eye(4);placement[:3,:3]=r;placement[:3,3]=p
            wanted=parent@placement@a['sampler'].sample(min(time,scene.duration))[a['rig'].joints]
            got=np.array([decoded(observed[a['rig'].document['nodes'][int(j)]['name']],16,'bone pose').reshape(4,4) for j in a['rig'].joints])
            errors['actor']=max(errors['actor'],float(abs(got-wanted).max()))
            root=roots_at(n,time);delta=np.linalg.inv(roots_at(n,0. if previous is None else previous))@root
            errors['actor']=max(errors['actor'],float(abs(decoded(row['root_motion'][n],16,'root motion').reshape(4,4)-root).max()),
                float(abs(decoded(row['root_deltas'][n],16,'root delta').reshape(4,4)-delta).max()))
        for n in asset.objects:
            p,r=asset.object_poses(n,[time]);pose=np.eye(4);pose[:3,:3]=r[0];pose[:3,3]=p[0];wanted=parent@pose
            errors['object']=max(errors['object'],float(abs(decoded(row['objects'][n],16,'object pose').reshape(4,4)-wanted).max()))
    require(len(actual['frames'])==len(queries),'Complete baked evaluation clock required')
    for i,(row,time) in enumerate(zip(actual['frames'],queries)):frame(row,time,None if i==0 else queries[i-1])
    require(actual['boot_bound'],'Exported main scene must bind')
    require(actual['object_key_envelope_s']==max(config['duration_s'],float(np.float32(config['duration_s']))),'Exact in-memory key envelope required')
    frame(actual['boot_frame'],config['duration_s'])
    for key in ('callbacks','skipped_callbacks','restart_callbacks','boot_callbacks'):
        require(len(actual[key])==len(expected_events),'Complete confirmed marker callback population required')
        for row,event in zip(actual[key],expected_events):
            require(row['id']==event['id'],'Marker order changed');index=int(np.searchsorted(queries,event['time_s']))
            frame(row,event['time_s'],queries[index-1] if key in ('callbacks','restart_callbacks') and index else None)
    require(actual['preview_silent'] and actual['repeat_silent'] and actual['repeat_root_delta_identity'] and actual['backward_rejected'] and actual['invalid_bindings_rejected']==12 and actual['no_binding_leaks'],'Preview/repeat/restart/rejection controls required')
    require(all(v<=POSE_LIMIT for v in errors.values()),'Saved composed actor/prop playback differs')
    return dict(samples=len(queries),callback_observations=len(expected_events)*4,maximum_pose_component_error=errors,pose_component_limit=POSE_LIMIT,exported_main_scene_verified=True,
        source_end_hold_duration_s=config['duration_s']-scene.duration,in_memory_object_key_envelope_s=actual['object_key_envelope_s'],live_prop_physics=False,scene_playback_verified=True,animation_quality_approved=False,release_approved=False)


def audit(source,output):
    source=Path(source).resolve();output=Path(output).resolve();require(not output.exists(),'Fresh baked playback audit required');require(sha256(ENGINE)==ENGINE_SHA256,'Pinned headless engine changed')
    with worker_lock():
        output.mkdir();save(output/'pipeline.json',dict(status='preparing',at=now()));project=output/'project'
        try:
            source_digest=sha256(source);shutil.copyfile(source,output/'source-baked-runtime.zip');require(sha256(output/'source-baked-runtime.zip')==source_digest,'Runtime source changed during snapshot')
            m=unpack(output/'source-baked-runtime.zip',project,runtime=True)
            require(m['source_bytes_unchanged'] is True and all(m[k] is False for k in ('engine_executed','live_prop_physics','animation_quality_approved','release_approved')),'Unapproved physics-free runtime package required')
            require(set(m['methods_sha256'])==set(METHODS) and all(sha256(ROOT/'scripts'/n)==h for n,h in m['methods_sha256'].items()),'Current complete audit methods required')
            require(set(m['runtime_methods_sha256'])==set(GDS) and all(m['runtime_methods_sha256'][n]==m['files_sha256']['baked-runtime-v1/'+n]==sha256(ROOT/'scripts'/n) for n in GDS),'Current trusted runtime scripts required')
            config,scene,asset,clock,events=configure_bake(project,read(project/'package.json'));require(config==read(project/'baked-runtime-v1/runtime.json'),'Bound baked runtime differs')
            queries=np.unique(np.r_[clock,(clock[:-1]+clock[1:])/2,np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8'),scene.duration])
            request=dict(config=config,folder=str(project),clock=clock_wire(queries));save(output/'request.json',request)
            actual=engine_run(project,'baked-runtime-v1/godot_baked_scene_audit.gd',output/'request.json',output/'actual.json',output/'engine.log',120)
            require(actual['request_sha256']==sha256(output/'request.json'),'Playback audit request changed')
            checked=evaluate(actual,config,scene,asset,queries,events)
            require(sha256(source)==sha256(output/'source-baked-runtime.zip')==source_digest and all(sha256(project/n)==h for n,h in m['files_sha256'].items()) and all(sha256(ROOT/'scripts'/n)==h for n,h in m['methods_sha256'].items()),'Saved source or implementation changed')
            result=dict(schema='strep-baked-scene-playback-result-v1',status='complete',at=now(),source_runtime_zip_sha256=source_digest,engine_sha256=ENGINE_SHA256,actual_sha256=sha256(output/'actual.json'),**checked,renderer_executed=False,human_reviewed=False)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=repr(exc),at=now()));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['package','audit']);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path);a=parser.parse_args();print(json.dumps((package if a.mode=='package' else audit)(a.source,a.output)))
