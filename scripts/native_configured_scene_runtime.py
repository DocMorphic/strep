"""Capture and audit the exact root-motion mask selected for scene export.

Embedded baseline and configured mode retain every original frame, actor,
object, event, preview, malformed-input and bootstrap check. Fixed alternating
root modes are not evidence for another selected configuration. CPU/finite
runtime evidence remains separate from geometry, GPU, physics and quality.
"""
import argparse
from collections.abc import Mapping
from pathlib import Path
import copy, hashlib, shutil, subprocess, zipfile
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now, offline_environment
import native_scene_runtime as original
from native_scene_runtime import (clock_echo_matches,evaluate_root,matrices,ImportedSceneSkin,
    POSE_TOLERANCE,SKIN_POSITION_TOLERANCE,OBJECT_TOLERANCE,affine_skin_compare,crossed)

AUDIT='godot_configured_scene_runtime_audit.gd'
GDS=tuple(n for n in original.GDS if n!='godot_native_scene_runtime_audit.gd')+(AUDIT,)
METHODS=tuple(dict.fromkeys(original.METHODS+('native_configured_scene_runtime.py',AUDIT)))
MODES=('embedded','configured')
SCHEMA='strep-configured-scene-runtime-mode-files-v1'
require=original.require


def compare(scene,times,events,actual,*,object_asset,root_modes):
    require(set(actual['modes'])==set(MODES),'Complete configured root-mode comparisons required')
    require(isinstance(root_modes,dict) and set(root_modes)==set(scene.actors)
        and all(v in ('embedded','extracted') for v in root_modes.values()),'Explicit root mode for every actor required')
    checks={};arrays={'times_s':times};all_pass=True
    baseline=actual['modes']['embedded']
    for mode,observed in actual['modes'].items():
        expected_modes={name:('embedded' if mode=='embedded' else root_modes[name]) for name in scene.actors}
        require(observed['root_modes']==expected_modes,'Actual captured root mask differs from selected configuration')
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
            if mode=='configured' and root_modes[name]=='extracted':
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
        require((object_asset is not None)==bool(scene.objects),'Exact declared object population required')
        object_channels=[] if object_asset is None else object_asset.channels
        require(len(observed['object_channels'])==len(object_channels),'Complete saved object channel population required')
        object_key_error=0.0
        for index,(source,target) in enumerate(zip(object_channels,observed['object_channels'])):
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
            require(set(preview['actors'])==set(scene.actors) and set(preview['objects'])==set(scene.objects),'Complete preview participant population required')
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
                require(set(snapshot['actors'])==set(scene.actors) and set(snapshot['objects'])==set(scene.objects),'Complete callback participant population required')
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
        all_pass=all_pass and callback_error<=POSE_TOLERANCE and observed['malformed_configs']==11 and all(observed[k] is True for k in ('invalid_rejected','late_participant_rejected','reentrant_rejected','malformed_configs_rejected'))
        checks[mode]=dict(actors=actor_checks,objects=objects,callbacks=len(expected),callback_scenarios=len(traces),
            maximum_callback_pose_difference=callback_error,invalid_clocks_rejected=observed['invalid_rejected'],
            late_participant_rejected=observed['late_participant_rejected'],reentrant_rejected=observed['reentrant_rejected'],malformed_configs=observed['malformed_configs'],
            maximum_object_native_key_value_difference=object_key_error,maximum_object_preview_difference=preview_error)
    initial=[e['id'] for e in crossed(events,None,float(times[-1])) if e['sample_index']==0]
    boot=actual['bootstrap']
    require(boot['parent_ready_listener'] is True and boot['initial_event_ids']==initial and boot['frames']>=3
        and boot['valid_clock'] is True,'Exported bootstrap must advance and deliver initial events to a parent-ready listener')
    return dict(modes=checks,bootstrap=boot,all_sampled_runtime_conditions_pass=bool(all_pass),samples=len(times),
        configured_root_modes=dict(root_modes),configured_mode_observed=True),arrays


class ModeFiles(Mapping):
    """Only the embedded baseline is cached. No mode or sample is omitted."""
    def __init__(self, folder, header):
        self.folder=Path(folder).resolve();self.baseline=None
        require(isinstance(header,dict) and set(header)=={'schema','engine','modes','bootstrap'}
            and header['schema']==SCHEMA,'Complete mode-file header required')
        require(isinstance(header['modes'],dict) and set(header['modes'])==set(MODES),'Embedded and exact configured root modes required')
        self.entries={}
        for name in MODES:
            entry=header['modes'][name]
            require(isinstance(entry,dict) and set(entry)=={'path','sha256'}
                and entry['path']==f'engine-mode-{name}.json','Fixed relative mode file required')
            digest=entry['sha256']
            require(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'Exact mode hash required')
            path=(self.folder/entry['path']).resolve()
            require(path.parent==self.folder and path.is_file(),'Mode file must stay inside its audit folder')
            self.entries[name]=(path,digest)
        require(sum(p.stat().st_size for p,_ in self.entries.values())<=1024**3,'Complete mode observations exceed 1 GiB; no partial reads')
        self.verify()

    def verify(self):
        for path,digest in self.entries.values():require(sha256(path)==digest,'Raw mode observations changed')

    def __iter__(self):return iter(MODES)
    def __len__(self):return len(MODES)
    def __getitem__(self,name):
        if name not in self.entries:raise KeyError(name)
        if name=='embedded' and self.baseline is not None:return self.baseline
        path,digest=self.entries[name]
        require(sha256(path)==digest,'Raw mode observations changed')
        value=read(path)
        require(sha256(path)==digest,'Raw mode observations changed during read')
        if name=='embedded':self.baseline=value
        return value


def run(source,output,modes,*,engine=None):
    source=Path(source).resolve();output=Path(output).resolve()
    require(not output.exists(),'Fresh native scene runtime output required')
    engine=Path(engine or ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe').resolve()
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (source,engine)}
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        with zipfile.ZipFile(source) as archive:manifest=original.package_members(archive)
        output.mkdir();save(output/'pipeline.json',dict(status='processing',stage='source-snapshot',quality_approved=False))
        try:
            project=output/'project';project.mkdir();implementation=output/'implementation';implementation.mkdir()
            for n in METHODS:shutil.copyfile(ROOT/'scripts'/n,implementation/n)
            shutil.copyfile(source,output/'source-game-assets.zip')
            with zipfile.ZipFile(output/'source-game-assets.zip') as archive:
                require(original.package_members(archive)==manifest,'Game snapshot changed')
                for name in archive.namelist():
                    dest=project/name;dest.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(name) as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst)
            config,scene,times,events=original.configure(project,manifest,modes)
            runtime=project/'runtime-v1';runtime.mkdir()
            for n in GDS:shutil.copyfile(implementation/n,runtime/n)
            save(runtime/'scene-runtime.json',config)
            (runtime/'scene.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://runtime-v1/godot_native_scene_boot.gd" id="1"]\n[node name="Strep" type="Node3D"]\nscript = ExtResource("1")\n',encoding='utf8')
            (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep native scene runtime"\nrun/main_scene="res://runtime-v1/scene.tscn"\n',encoding='utf8')
            save(output/'request.json',dict(asset_folder=str(project),config=config,source_game_zip_sha256=bindings[str(source)]))
            runtime_bindings={str(p):sha256(p) for p in (runtime/'scene-runtime.json',runtime/'scene.tscn',
                project/'project.godot',output/'request.json')}
            save(output/'pipeline.json',dict(status='processing',stage='engine-root-modes',quality_approved=False))
            with (output/'engine.log').open('w',encoding='utf8') as log:
                process=subprocess.run([str(engine),'--headless','--path',str(project),'--script','res://runtime-v1/'+AUDIT,'--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=300,env=offline_environment(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            require(process.returncode==0 and (output/'engine-output.json').is_file(),'Actual scene mode audit failed; preserved engine.log')
            header=read(output/'engine-output.json');raw=ModeFiles(output,header)
            raw_hashes={'engine-output.json':sha256(output/'engine-output.json'),**{p.name:h for p,h in raw.entries.values()}}
            asset=original.ObjectAsset(project/'objects.glb') if scene.objects else None
            if asset is not None:require(set(asset.objects)==set(scene.objects) and all(np.isin(c['times_s'],times).all() for c in asset.channels),'Complete original object clock required')
            save(output/'pipeline.json',dict(status='processing',stage='configured-runtime-comparator',quality_approved=False))
            result,arrays=compare(scene,times,events,dict(engine=header['engine'],modes=raw,bootstrap=header['bootstrap']),object_asset=asset,root_modes=modes)
            np.savez_compressed(output/'observations.npz',**arrays)
            with np.load(output/'observations.npz',allow_pickle=False) as stored:
                require(set(stored.files)==set(arrays) and all(stored[k].dtype==v.dtype and stored[k].shape==v.shape and stored[k].tobytes()==v.tobytes() for k,v in arrays.items()),'Complete runtime arrays changed')
            raw.verify()
            require(all(sha256(output/n)==h for n,h in raw_hashes.items()),'Raw mode receipt changed')
            for name,digest in manifest['files_sha256'].items():require(sha256(project/name)==digest,'Original game asset changed during runtime')
            for n,h in methods.items():require(sha256(ROOT/'scripts'/n)==sha256(implementation/n)==h,'Runtime method changed during study')
            for n in GDS:require(sha256(runtime/n)==methods[n],'Executed runtime helper changed')
            require(all(sha256(p)==h for p,h in bindings.items()) and sha256(output/'source-game-assets.zip')==bindings[str(source)],'Original source/engine/snapshot changed')
            require(all(sha256(p)==h for p,h in runtime_bindings.items()),'Executed/exported runtime configuration changed')
            original.make_package(output/'source-game-assets.zip',output,result,config)
            with zipfile.ZipFile(output/'runtime-assets.zip') as exported:
                for name in ('runtime-v1/scene-runtime.json','runtime-v1/scene.tscn','project.godot'):
                    require(hashlib.sha256(exported.read(name)).hexdigest()==runtime_bindings[str(project/name)],
                        'Exported runtime configuration differs from executed selection')
            require(all(sha256(p)==h for p,h in runtime_bindings.items()),'Runtime configuration changed during packaging')
            result.update(schema='strep-configured-scene-runtime-audit-v1',status='complete',at=now(),engine=header['engine'],
                input_sha256=bindings,implementation_sha256=methods,executed_script_sha256={n:sha256(runtime/n) for n in GDS},
                raw_mode_files_sha256=raw_hashes,files_sha256={n:sha256(output/n) for n in ('source-game-assets.zip','request.json','engine.log','observations.npz','runtime-assets.zip','package.json')},
                original_comparison_checks_retained=True,complete_clock_retained=True,source_bytes_unchanged=True,arrays_roundtrip_exact=True,
                runtime_configuration_sha256=runtime_bindings,
                original_selected=True,real_time_playback_verified=False,quality_approved=False,physics_verified=False,training_admitted=False,release_approved=False,
                scope='Actual complete finite Godot scene with embedded baseline and the exact selected root mask, imported CPU skin and explicit confirmed event callbacks. Original checks retained with explicit per-actor mode selection. Smaller working set, not a fixed RAM guarantee. No physics, continuous geometry, GPU rendering, frame-rate or human-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',quality_approved=False));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('package');parser.add_argument('output');parser.add_argument('--modes',required=True);parser.add_argument('--engine');args=parser.parse_args()
    print(run(args.package,args.output,read(args.modes),engine=args.engine))
