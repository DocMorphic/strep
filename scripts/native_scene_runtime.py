"""Build and verify finite actor/object/event runtime from a native game ZIP.

Whole scene, every original clock sample, marker-time callbacks and raw CPU skin.
Preserves the original ZIP entries and resources; no geometry requery or models.
"""
import argparse,copy,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now,offline_environment
from native_scene_contacts import SceneContacts
from native_scene_game_tracks import event_plan,crossed
from native_engine_clock import check_clock_wire,clock_echo_matches
from native_engine_contacts import matrices
from native_scene_engine import OBJECT_TOLERANCE,POSE_TOLERANCE,SKIN_POSITION_TOLERANCE
from audit_native_root_runtime import validate as validate_root,evaluate as evaluate_root,METHODS as ROOT_METHODS
from native_scene_imported_skin import ImportedSceneSkin
from native_object_asset import ObjectAsset,METHODS as OBJECT_METHODS
from native_runtime_affine_skin import compare as affine_skin_compare

GDS=('godot_native_scene_player.gd','godot_native_object_player.gd','godot_native_scene_loader.gd',
    'godot_native_scene_observations.gd','godot_native_scene_runtime_audit.gd','godot_native_scene_boot.gd',
    'godot_native_root_adapter.gd','native_godot_preview.gd','godot_scene_game_events.gd','native_engine_clock.gd')
METHODS=tuple(dict.fromkeys(ROOT_METHODS+OBJECT_METHODS+GDS+('native_scene_runtime.py','native_scene_game_tracks.py','native_runtime_affine_skin.py')))


def require(condition,message):
    if not condition:raise ValueError(message)


def package_members(archive):
    names=archive.namelist()
    require(len(names)==len(set(n.casefold() for n in names)) and len(names)<=256,'Unique complete ZIP entries required')
    for name in names:
        p=PurePosixPath(name)
        require(name and not p.is_absolute() and '\\' not in name and ':' not in name and all(part not in ('','.','..') for part in name.split('/')),'Portable relative package paths required')
    require(sum(i.file_size for i in archive.infolist())<=1024**3,'Whole runtime package exceeds 1 GiB budget; no partial extraction')
    value=json.loads(archive.read('package.json'))
    require(value['schema']=='strep-native-scene-game-package-v1' and value['root_removed_from_character_clips'] is False
        and value['root_application_mode']=='reference-only-motion-remains-embedded','Original embedded native game package required')
    require(value['original_selected'] is True and all(value[k] is False for k in ('quality_approved','physics_verified','release_approved','animation_runtime_playback_verified')),'Original game decisions required')
    require(set(names)==set(value['files_sha256'])|{'package.json'},'Complete original game ZIP population required')
    for name,digest in value['files_sha256'].items():
        observed=hashlib.sha256()
        with archive.open(name) as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):observed.update(chunk)
        require(observed.hexdigest()==digest,'Game ZIP entry changed: '+name)
    return value


def configure(folder,manifest,modes):
    spec=read(folder/'scene.json');scene=SceneContacts(spec,folder)
    roots=read(folder/'root-motion.json');request=read(folder/'game-tracks-request.json');events=read(folder/'events.json');contacts=read(folder/'contacts.json')
    times=np.asarray(roots['times_s'],dtype='<f8');check_clock_wire(events['clock'],times)
    require(set(modes)==set(scene.actors) and all(v in ('embedded','extracted') for v in modes.values()),'Explicit embedded/extracted mode for every actor required')
    require(roots['schema']=='strep-native-scene-root-references-v1' and roots['application_mode']=='reference-only-motion-remains-embedded'
        and set(roots['actors'])==set(scene.actors),'Complete embedded root references required')
    digest=sha256(folder/'scene.json')
    require(roots['portable_scene_sha256']==events['portable_scene_sha256']==contacts['portable_scene_sha256']==digest,'Scene/track source binding changed')
    require(contacts['schema']=='strep-native-scene-contact-tracks-v1' and contacts['continuous_contact_certified'] is False
        and all(contacts[k] is False for k in ('quality_approved','physics_verified','release_approved')),'Original contact scope required')
    require([c['intent'] for c in contacts['contacts']]==spec['contacts'] and all(c['runtime_dispatch_allowed'] is False for c in contacts['contacts']),'Complete unchanged non-dispatchable contact intent required')
    measured=dict(contacts=[c['measurement'] for c in contacts['contacts']])
    expected,_=event_plan(scene,request,times,measured);expected['portable_scene_sha256']=digest
    require(expected==events,'Event timing/confirmation differs from original scene intent')
    entries=[]
    def asset(name):
        require(name in manifest['files_sha256'] and sha256(folder/name)==manifest['files_sha256'][name],'Bound runtime file missing')
        return dict(path=name,sha256=manifest['files_sha256'][name])
    require(manifest['selected_animations']=={n:a['animation_index'] for n,a in scene.actors.items()},'Selected animations changed')
    for name,actor in scene.actors.items():
        node=request['actors'][name]['root_node'];p,r=actor['placement'];placement=np.eye(4);placement[:3,:3]=r;placement[:3,3]=p
        validate_root(actor['rig'],actor['animation_index'],node,times,placement)
        require(roots['actors'][name]['root_node']==node and roots['actors'][name]['character_glb_sha256']==spec['actors'][name]['sha256']
            and roots['actors'][name]['animation_index']==actor['animation_index'],'Root selection changed')
        entries.append(dict(id=name,asset=asset(spec['actors'][name]['glb']),resource=asset('animations/'+name+'.res'),
            animation_index=actor['animation_index'],root_bone=actor['rig'].document['nodes'][node]['name'],
            placement=placement.tolist(),extract=modes[name]=='extracted'))
    require(bool(scene.objects),'At least one declared object required')
    config=dict(schema='strep-native-scene-runtime-v1',actors=entries,
        objects=dict(asset=asset('objects.glb'),resource=asset('animations/objects.res'),names=list(scene.objects)),events=asset('events.json'))
    return config,scene,times,events


def compare(scene,times,events,actual,*,object_asset):
    require(set(actual['modes'])=={'embedded','extracted','mixed'},'Complete root-mode comparisons required')
    checks={};arrays={'times_s':times};all_pass=True
    baseline=actual['modes']['embedded']
    for mode,observed in actual['modes'].items():
        frames=observed['frames'];require(len(frames)==len(times),'Complete simultaneous scene clock required')
        require(set(observed['actors'])==set(scene.actors),'Complete simultaneous actor population required')
        for t,f in zip(times,frames):
            require(clock_echo_matches(t,f['pose_time_s']) and clock_echo_matches(t,f['playback_time_s'])
                and set(f['actors'])==set(scene.actors) and set(f['objects'])==set(scene.objects),'All participants must share the exact authored clock')
        actor_checks={}
        for index,(name,actor) in enumerate(scene.actors.items()):
            p,r=actor['placement'];placement=np.eye(4);placement[:3,:3]=r;placement[:3,3]=p
            root_observed=copy.deepcopy(observed['actors'][name])
            root_observed.update(embedded=[f['actors'][name] for f in baseline['frames']],
                extracted=[f['actors'][name] for f in frames],preview=[f['actors'][name] for f in observed['previews']],
                invalid_rejected=observed['invalid_rejected'],malformed_bindings_rejected=observed['malformed_configs_rejected'],malformed_bindings=observed['malformed_configs'])
            if mode=='extracted' or (mode=='mixed' and index%2==0):
                result,values=evaluate_root(actor['rig'],actor['sampler'],times,placement,root_observed)
                actor_checks[name]=result;all_pass=all_pass and result['sampled_runtime_conditions_pass']
                for key,value in values.items():arrays[f'{mode}_actor_{index}_{key}']=value
            else:
                skin=ImportedSceneSkin(actor['rig'],observed['actors'][name])
                world=matrices([f['actors'][name]['bones'] for f in frames])[:,np.argsort(skin.bone_map)]
                expected=placement@np.array([actor['sampler'].sample(float(t))[actor['rig'].joints] for t in times])
                error=float(abs(world-expected).max());arrays[f'{mode}_actor_{index}_world']=world
                actor_checks[name]=dict(maximum_pose_element_error=error,passed=error<=POSE_TOLERANCE,imported_skin=skin.report)
                all_pass=all_pass and error<=POSE_TOLERANCE
            affine,values=affine_skin_compare(baseline['actors'][name],observed['actors'][name],
                [f['actors'][name] for f in baseline['frames']],[f['actors'][name] for f in frames],
                [f['actors'][name] for f in observed['previews']],times,SKIN_POSITION_TOLERANCE)
            actor_checks[name]['affine_skin']=affine;all_pass=all_pass and affine['passed']
            for key,value in values.items():arrays[f'{mode}_actor_{index}_{key}']=value
        require(len(observed['object_channels'])==len(object_asset.channels),'Complete saved object channel population required')
        object_key_error=0.0
        for index,(source,target) in enumerate(zip(object_asset.channels,observed['object_channels'])):
            require(target['target_name']==source['node_name'] and target['type']=={'translation':1,'rotation':2,'scale':3}[source['path']]
                and np.array_equal(target['times_s'],source['times_s']),'Saved object native key times, targets or channels changed')
            expected_values=np.asarray(source['values'],dtype='<f8');values=np.asarray(target['values'],dtype='<f8')
            if source['path']=='rotation':expected_values/=np.linalg.norm(expected_values,axis=1)[:,None]
            require(values.shape==expected_values.shape and np.isfinite(values).all(),'Complete finite object native key values required')
            object_key_error=max(object_key_error,float(abs(values-expected_values).max()))
            arrays[f'{mode}_object_track_{index}_times']=np.asarray(target['times_s'],dtype='<f8');arrays[f'{mode}_object_track_{index}_values']=values
        all_pass=all_pass and object_key_error<=1e-6
        objects={}
        for index,name in enumerate(scene.objects):
            world=matrices([f['objects'][name] for f in frames]);p,r=scene.object_poses(name,times)
            position=float(np.linalg.norm(world[:,:3,3]-p,axis=1).max());basis=float(abs(world[:,:3,:3]-r).max())
            arrays[f'{mode}_object_{index}_world']=world
            objects[name]=dict(maximum_position_error_m=position,maximum_basis_error=basis,limit=OBJECT_TOLERANCE,passed=max(position,basis)<=OBJECT_TOLERANCE)
            all_pass=all_pass and objects[name]['passed']
        preview_error=0.0
        for preview in observed['previews']:
            ids=[i for i,t in enumerate(times) if clock_echo_matches(t,preview['pose_time_s'])]
            require(len(ids)==1 and clock_echo_matches(times[-1],preview['playback_time_s']),'Preview must retain the playback cursor and one exact pose time')
            for name in scene.objects:preview_error=max(preview_error,float(abs(matrices(preview['objects'][name])-matrices(frames[ids[0]]['objects'][name])).max()))
        all_pass=all_pass and preview_error<=OBJECT_TOLERANCE
        expected=crossed(events,None,float(times[-1]));traces=[observed['events']]+list(observed['traces'].values())
        require(set(observed['traces'])=={'whole-clip','skipped','repeated'},'Complete event-clock traversal scenarios required')
        callback_error=0.0
        for trace in traces:
            require(len(trace)==len(expected),'Complete confirmed gameplay marker population required')
            for wanted,callback in zip(expected,trace):
                entry=callback['event'];sample_index=wanted['sample_index'];t=float(times[sample_index]);snapshot=callback['scene']
                require({k:v for k,v in entry.items() if k!='time_s'}=={k:v for k,v in wanted.items() if k!='time_s'}
                    and clock_echo_matches(t,entry['time_s']) and clock_echo_matches(t,snapshot['pose_time_s'])
                    and clock_echo_matches(t,snapshot['playback_time_s']),'Callbacks must observe scene at exact marker time, including skipped frames')
                reference=frames[sample_index]
                for name in scene.actors:
                    callback_error=max(callback_error,float(abs(matrices(snapshot['actors'][name]['bones'])-matrices(reference['actors'][name]['bones'])).max()))
                    for key in ('actor_world','skeleton_world'):
                        callback_error=max(callback_error,float(abs(matrices(snapshot['actors'][name][key])-matrices(reference['actors'][name][key])).max()))
                    require(set(snapshot['actors'][name]['mesh_world'])==set(reference['actors'][name]['mesh_world']),'Complete callback mesh world population required')
                    for node in reference['actors'][name]['mesh_world']:
                        callback_error=max(callback_error,float(abs(matrices(snapshot['actors'][name]['mesh_world'][node])-matrices(reference['actors'][name]['mesh_world'][node])).max()))
                for name in scene.objects:callback_error=max(callback_error,float(abs(matrices(snapshot['objects'][name])-matrices(reference['objects'][name])).max()))
        all_pass=all_pass and callback_error<=POSE_TOLERANCE and observed['malformed_configs']>=7 and all(observed[k] is True for k in ('invalid_rejected','late_participant_rejected','reentrant_rejected','malformed_configs_rejected'))
        checks[mode]=dict(actors=actor_checks,objects=objects,callbacks=len(expected),callback_scenarios=len(traces),
            maximum_callback_pose_difference=callback_error,invalid_clocks_rejected=observed['invalid_rejected'],
            late_participant_rejected=observed['late_participant_rejected'],reentrant_rejected=observed['reentrant_rejected'],malformed_configs=observed['malformed_configs'],
            maximum_object_native_key_value_difference=object_key_error,maximum_object_preview_difference=preview_error)
    initial=[e['id'] for e in crossed(events,None,float(times[-1])) if e['sample_index']==0]
    boot=actual['bootstrap']
    require(boot['parent_ready_listener'] is True and boot['initial_event_ids']==initial and boot['frames']>=3
        and boot['valid_clock'] is True,'Exported bootstrap must advance and deliver initial events to a parent-ready listener')
    return dict(modes=checks,bootstrap=boot,all_sampled_runtime_conditions_pass=bool(all_pass),samples=len(times)),arrays


def make_package(source,folder,result,config):
    extras={f'runtime-v1/{n}':folder/'implementation'/n for n in GDS if n!='godot_native_scene_runtime_audit.gd'}
    extras.update({'runtime-v1/scene-runtime.json':folder/'project/runtime-v1/scene-runtime.json',
        'runtime-v1/scene.tscn':folder/'project/runtime-v1/scene.tscn','project.godot':folder/'project/project.godot'})
    receipts={n:sha256(p) for n,p in extras.items()}
    with zipfile.ZipFile(source) as original,zipfile.ZipFile(folder/'runtime-assets.zip','x',compression=zipfile.ZIP_DEFLATED) as output:
        require(not set(original.namelist()).intersection(set(extras)|{'source-game-package.json'}),'Runtime package entry collision')
        for name in original.namelist():
            target='source-game-package.json' if name=='package.json' else name;digest=hashlib.sha256()
            with original.open(name) as src,output.open(target,'w',force_zip64=True) as dst:
                for chunk in iter(lambda:src.read(1024*1024),b''):digest.update(chunk);dst.write(chunk)
            receipts[target]=digest.hexdigest()
        for name,path in extras.items():output.write(path,name)
        manifest=dict(schema='strep-native-scene-runtime-package-v1',files_sha256=receipts,
            source_game_zip_sha256=sha256(source),root_removed_from_character_clips=False,
            runtime_root_modes={e['id']:'extracted' if e['extract'] else 'embedded' for e in config['actors']},
            finite_scene_controller_verified=result['all_sampled_runtime_conditions_pass'],
            real_time_playback_verified=False,original_selected=True,quality_approved=False,physics_verified=False,release_approved=False)
        save(folder/'package.json',manifest);output.write(folder/'package.json','package.json')
    with zipfile.ZipFile(folder/'runtime-assets.zip') as decoded:
        require(set(decoded.namelist())==set(receipts)|{'package.json'},'Complete runtime ZIP population required')
        for name in decoded.namelist():
            digest=hashlib.sha256()
            with decoded.open(name) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            require(digest.hexdigest()==(sha256(folder/'package.json') if name=='package.json' else receipts[name]),'Runtime ZIP readback changed')
    return manifest


def run(source,output,modes,*,engine=None):
    source=Path(source).resolve();output=Path(output).resolve()
    require(not output.exists(),'Fresh native scene runtime output required')
    engine=Path(engine or ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe').resolve()
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (source,engine)};methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        with zipfile.ZipFile(source) as archive:manifest=package_members(archive)
        output.mkdir();save(output/'pipeline.json',dict(status='processing',original_selected=True,quality_approved=False))
        try:
            project=output/'project';project.mkdir();implementation=output/'implementation';implementation.mkdir()
            for n in METHODS:shutil.copyfile(ROOT/'scripts'/n,implementation/n)
            shutil.copyfile(source,output/'source-game-assets.zip')
            with zipfile.ZipFile(output/'source-game-assets.zip') as archive:
                require(package_members(archive)==manifest,'Game snapshot changed')
                for name in archive.namelist():
                    dest=project/name;dest.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(name) as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst)
            config,scene,times,events=configure(project,manifest,modes)
            runtime=project/'runtime-v1';runtime.mkdir()
            for n in GDS:shutil.copyfile(implementation/n,runtime/n)
            save(runtime/'scene-runtime.json',config)
            (runtime/'scene.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://runtime-v1/godot_native_scene_boot.gd" id="1"]\n[node name="Strep" type="Node3D"]\nscript = ExtResource("1")\n',encoding='utf8')
            (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep native scene runtime"\nrun/main_scene="res://runtime-v1/scene.tscn"\n',encoding='utf8')
            save(output/'request.json',dict(asset_folder=str(project),config=config,source_game_zip_sha256=bindings[str(source)]))
            with (output/'engine.log').open('w',encoding='utf8') as log:
                process=subprocess.run([str(engine),'--headless','--path',str(project),'--script','res://runtime-v1/godot_native_scene_runtime_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=300,env=offline_environment())
            require(process.returncode==0 and (output/'engine-output.json').exists(),'Actual complete scene runtime audit failed; preserved engine.log')
            asset=ObjectAsset(project/'objects.glb')
            require(set(asset.objects)==set(scene.objects) and all(np.isin(c['times_s'],times).all() for c in asset.channels),'Complete object identities and original native key clock required')
            actual=read(output/'engine-output.json');result,arrays=compare(scene,times,events,actual,object_asset=asset)
            np.savez_compressed(output/'observations.npz',**arrays)
            with np.load(output/'observations.npz',allow_pickle=False) as stored:
                require(set(stored.files)==set(arrays) and all(stored[k].dtype==v.dtype and stored[k].shape==v.shape and stored[k].tobytes()==v.tobytes() for k,v in arrays.items()),'Complete runtime arrays changed')
            for name,digest in manifest['files_sha256'].items():require(sha256(project/name)==digest,'Original game asset changed during runtime')
            for n,h in methods.items():require(sha256(ROOT/'scripts'/n)==sha256(implementation/n)==h,'Runtime method changed during study')
            for n in GDS:require(sha256(runtime/n)==methods[n],'Executed runtime helper changed')
            require(all(sha256(p)==h for p,h in bindings.items()) and sha256(output/'source-game-assets.zip')==bindings[str(source)],'Original source/engine/snapshot changed')
            make_package(output/'source-game-assets.zip',output,result,config)
            result.update(schema='strep-native-scene-runtime-audit-v1',status='complete',at=now(),engine=actual['engine'],
                input_sha256=bindings,implementation_sha256=methods,executed_script_sha256={n:sha256(runtime/n) for n in GDS},
                files_sha256={n:sha256(output/n) for n in ('source-game-assets.zip','request.json','engine-output.json','engine.log','observations.npz','runtime-assets.zip','package.json')},
                original_selected=True,source_bytes_unchanged=True,arrays_roundtrip_exact=True,
                real_time_playback_verified=False,quality_approved=False,physics_verified=False,training_admitted=False,release_approved=False,
                scope='Complete finite native actor/object/controller and confirmed gameplay event clock in actual headless Godot. Original clips/resources retained. No physics, blending, loops, geometry requery, fresh GPU rendering, frame-rate or human-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True,quality_approved=False));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('package');parser.add_argument('output');parser.add_argument('--modes',required=True,help='JSON file: actor name -> embedded or extracted');parser.add_argument('--engine');args=parser.parse_args()
    print(run(args.package,args.output,read(args.modes),engine=args.engine))
