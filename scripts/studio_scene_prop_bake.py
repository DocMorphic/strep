"""Source-bound Studio jobs for finite offline editable prop animation bakes.

Preserves source decisions; successful import is not interaction approval.
"""
import argparse,json,os,shutil,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
import studio_scene_prop_runtime as prop
import scene_prop_bake as core
from studio_native_scene import NAME
from native_scene_contacts import fields
from native_object_asset import ObjectAsset
from gltf_tools import read_glb
from strep import ROOT,read,save,sha256,now

NAMESPACE='scene-prop-bake-jobs'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(core.METHODS+prop.METHODS+('studio_scene_prop_bake.py',)))
DOWNLOADS=('bake/baked-assets.zip','bake-request.json','bake/result.json','result.json')


def require(value,message):
    if not value:raise ValueError(message)


def portable(name):
    return isinstance(name,str) and bool(name) and not PurePosixPath(name).is_absolute() and '\\' not in name and ':' not in name and all(p not in ('','.','..') for p in name.split('/'))


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid prop bake job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Prop bake job escapes namespace');return folder


def source(job):
    manifest=prop.manifest(job);require(manifest['status']=='complete','Select a completed prop runtime package')
    folder=prop.folder_for(job);prepared,values=prop.frozen(folder,current_methods=False)
    return folder,manifest,prepared,values


def metadata(job):
    folder,manifest,_,values=source(job)
    return dict(runtime_job=job,source_result_sha256=sha256(folder/'result.json'),source_runtime_zip_sha256=sha256(folder/'runtime/prop-runtime-assets.zip'),
        physics_fps=values[4]['physics_fps'],source_scene_conditions_pass=manifest['source_scene_conditions_pass'],root_samples_pass=manifest['root_samples_pass'],
        original_selected=True,quality_approved=False,release_approved=False)


def validate_request(payload):
    fields(payload,('runtime_job','source_result_sha256','request'),'selected source-bound prop bake')
    folder,manifest,prepared,values=source(payload['runtime_job'])
    require(payload['source_result_sha256']==sha256(folder/'result.json'),'Selected prop runtime result changed')
    request=core.validate_request(payload['request'],sha256(folder/'runtime/prop-runtime-assets.zip'))
    return folder,manifest,prepared,values,request


def prepare(payload,folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh prop bake job required')
    values=validate_request(payload);methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};folder.mkdir(parents=True)
    save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        save(folder/'request.json',payload);save(folder/'bake-request.json',values[4])
        implementation=folder/'implementation';implementation.mkdir()
        for n in methods:shutil.copyfile(SCRIPT_ROOT/n,implementation/n)
        shutil.copyfile(values[0]/'runtime/prop-runtime-assets.zip',folder/'source-runtime.zip')
        require(sha256(folder/'source-runtime.zip')==values[4]['source_runtime_zip_sha256'],'Source runtime ZIP changed during snapshot')
        prepared=dict(schema='strep-studio-prop-bake-prepared-v1',request_sha256=sha256(folder/'request.json'),bake_request_sha256=sha256(folder/'bake-request.json'),
            source_result_sha256=sha256(values[0]/'result.json'),source_runtime_zip_sha256=sha256(folder/'source-runtime.zip'),implementation_sha256=methods,
            original_selected=True,quality_approved=False,release_approved=False)
        save(folder/'prepared.json',prepared);frozen(folder);save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False));return prepared
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder,*,current_methods=True):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound prop bake job folder required')
    p=read(folder/'prepared.json');payload=read(folder/'request.json')
    require(p['schema']=='strep-studio-prop-bake-prepared-v1' and p['request_sha256']==sha256(folder/'request.json') and p['bake_request_sha256']==sha256(folder/'bake-request.json'),'Bake preparation/request changed')
    require(p['original_selected'] is True and all(p[k] is False for k in ('quality_approved','release_approved')),'Bake preparation approval changed')
    values=validate_request(payload)
    require(read(folder/'bake-request.json')==values[4] and p['source_result_sha256']==sha256(values[0]/'result.json')
        and sha256(values[0]/'runtime/prop-runtime-assets.zip')==sha256(folder/'source-runtime.zip')==p['source_runtime_zip_sha256'],'Bake source snapshot changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete bake method archive required')
    for n,h in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/n)==h,'Archived bake implementation changed')
        if current_methods:require(sha256(SCRIPT_ROOT/n)==h,'Bake implementation changed during worker')
    return p,values


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound prop bake job folder required')
    require(read(folder/'pipeline.json')['status']=='starting' and not any((folder/n).exists() for n in ('worker.json','bake','completion.json')),'Fresh prepared bake worker required')
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        p,values=frozen(folder);save(folder/'pipeline.json',dict(status='processing',stage='offline-physical-prop-animation-bake',original_selected=True,quality_approved=False))
        baked=core.bake(folder/'source-runtime.zip',folder/'bake-request.json',folder/'bake');frozen(folder)
        execution_names=['bake/assets/'+n for n in baked['files_sha256']]+['bake/assets/package.json','bake/baked-assets.zip','bake/result.json',
            'bake/capture.json','bake/capture-audit.json','bake/capture-request.json','bake/import.json','bake/default-30fps.json']
        save(folder/'execution.json',dict(schema='strep-studio-prop-bake-execution-v1',artifacts_sha256={n:sha256(folder/n) for n in execution_names},quality_approved=False,release_approved=False))
        result=dict(schema='strep-studio-prop-bake-job-v1',status='complete',source_runtime_job=values[0].name,source_result_sha256=p['source_result_sha256'],
            prepared_sha256=sha256(folder/'prepared.json'),execution_sha256=sha256(folder/'execution.json'),package_sha256=baked['package_sha256'],source_bytes_unchanged=True,studio_selection_changed=False,original_selected=True,
            source_scene_conditions_pass=values[1]['source_scene_conditions_pass'],root_samples_pass=values[1]['root_samples_pass'],
            engine_import_verified=baked['engine_import_verified'],exact_physical_event_timing_pass=baked['exact_physical_event_timing_pass'],maximum_application_delay_s=baked['maximum_application_delay_s'],
            physics_quality_approved=False,quality_approved=False,release_approved=False,
            files_sha256={n:sha256(folder/n) for n in DOWNLOADS if n!='result.json'})
        save(folder/'result.json',result);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False));return result
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def verify_output(folder,p,values):
    """Whole ZIP/reference lineage and decoded tracks; no engine or skin query."""
    baked=read(folder/'bake/result.json');assets=folder/'bake/assets';m=read(assets/'package.json')
    extra={'package_sha256','methods_sha256','capture_sha256','capture_audit_sha256','renderer_executed','human_reviewed'}
    require(m=={k:v for k,v in baked.items() if k not in extra} and m['schema']=='strep-baked-prop-assets-v1' and m['status']=='complete','Baked manifest differs')
    require(m['source_runtime_zip_sha256']==p['source_runtime_zip_sha256'] and m['bake_request_sha256']==p['bake_request_sha256'],'Baked source/request differs')
    require(all(m[k] is True for k in ('source_actors_unchanged','source_mesh_payload_unchanged','engine_import_verified','original_selected'))
        and all(m[k] is False for k in ('studio_selection_changed','physics_quality_approved','animation_quality_approved','release_approved'))
        and all(baked[k] is False for k in ('renderer_executed','human_reviewed')),'Baked scope/approval changed')
    require(baked['methods_sha256']=={n:p['implementation_sha256'][n] for n in core.METHODS},'Baked method lineage differs')
    require(all(sha256(folder/'bake/methods'/n)==h for n,h in baked['methods_sha256'].items()),'Archived physical bake method changed')
    require(sha256(folder/'bake/source-runtime.zip')==p['source_runtime_zip_sha256'] and (folder/'bake/bake-request.json').read_bytes()==(folder/'bake-request.json').read_bytes(),'Baked input snapshot differs')
    require(sha256(folder/'bake/capture.json')==baked['capture_sha256'] and sha256(folder/'bake/capture-audit.json')==baked['capture_audit_sha256'],'Captured evidence changed')
    with zipfile.ZipFile(folder/'bake/baked-assets.zip') as z:
        names=z.namelist();require(len(names)==len(set(n.casefold() for n in names)) and len(names)<=512 and sum(i.file_size for i in z.infolist())<=1024**3,'Complete bounded baked ZIP required')
        require(all(n and not PurePosixPath(n).is_absolute() and '\\' not in n and ':' not in n and all(s not in ('','.','..') for s in n.split('/')) for n in names),'Portable bake paths required')
        require(set(names)==set(m['files_sha256'])|{'package.json'} and z.read('package.json')==(assets/'package.json').read_bytes(),'Complete baked ZIP manifest required')
        for n,h in m['files_sha256'].items():require(core.member_hash(z,n)==sha256(assets/n)==h,'Baked member changed')
    with zipfile.ZipFile(folder/'source-runtime.zip') as source_zip:
        source_manifest=json.loads(source_zip.read('package.json'))
        require(all(sha256(folder/'bake/capture-project'/n)==h==core.member_hash(source_zip,n) for n,h in source_manifest['files_sha256'].items()),'Original capture-project source changed')
        original=json.loads(source_zip.read('source-game-package.json'))
        expected_refs={'reference/'+n for n in original['files_sha256']}|{'reference/source-game-package.json'}
        require({n for n in m['files_sha256'] if n.startswith('reference/')}==expected_refs,'Complete original reference population required')
        for n in expected_refs:require(sha256(assets/n)==core.member_hash(source_zip,n.removeprefix('reference/')),'Original reference bytes changed')
        source_doc,source_binary=read_glb(folder/'bake/capture-project/objects.glb')
        require(sha256(folder/'bake/capture-project/objects.glb')==core.member_hash(source_zip,'objects.glb'),'Original prop asset changed')
    doc,binary=read_glb(assets/'objects.glb')
    require(binary[:len(source_binary)]==source_binary and doc['meshes']==source_doc['meshes'] and doc.get('materials')==source_doc.get('materials'),'Original baked prop mesh/material changed')
    config=read(values[0]/'runtime/project/ownership-v1/prop-runtime.json');scene,events=values[3][2],values[3][3]
    capture_request=read(folder/'bake/capture-request.json');clock=core.physical_clock(scene.duration,config['physics_fps'])
    require(capture_request==dict(asset_folder=str(folder/'bake/capture-project'),config=config,parent_world_transform=values[4]['parent_world_transform'],floor=values[4]['floor'],last_tick=len(clock)-1),'Physical capture request differs')
    audit,poses=core.audit_capture(read(folder/'bake/capture.json'),config,scene,events,values[4],sha256(folder/'bake/capture-request.json'))
    require(audit==read(folder/'bake/capture-audit.json')==read(assets/'bake-audit.json'),'Physical capture audit differs')
    clock=core.physical_clock(scene.duration,config['physics_fps']);queries=np.unique(np.r_[clock,(clock[:-1]+clock[1:])/2,np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')])
    asset=ObjectAsset(assets/'objects.glb');original_asset=ObjectAsset(folder/'bake/capture-project/objects.glb')
    require(set(asset.objects)==set(scene.objects),'Complete baked prop population required')
    for n,mode in config['object_modes'].items():
        expected=core.interpolated(clock,poses[n],queries) if mode=='grip-physics' else original_asset.object_poses(n,queries)
        actual=asset.object_poses(n,queries)
        require(max(float(abs(a-b).max()) for a,b in zip(expected,actual))<=core.POSE_LIMIT,'Baked tracks differ from captured/source motion')
        if mode=='authored':require([c for c in asset.channels if c['object']==n]==[c for c in original_asset.channels if c['object']==n],'Authored prop channels changed')
    storage_queries=np.unique(np.r_[clock,(clock[:-1]+clock[1:])/2]);tracks={};clocks={}
    for n,mode in config['object_modes'].items():
        expected=core.interpolated(clock,poses[n],storage_queries) if mode=='grip-physics' else original_asset.object_poses(n,storage_queries)
        actual=asset.object_poses(n,storage_queries);error=max(float(abs(a-b).max()) for a,b in zip(expected,actual))
        tracks[n]=dict(samples=len(storage_queries),maximum_pose_component_error=error,passed=error<=core.POSE_LIMIT,authored_channels_preserved=mode=='authored')
        if mode=='grip-physics':clocks[n]=core.stored_clock(clock)[1]
    require(read(assets/'bake-storage.json')==dict(clock_storage=clocks,decoded_tracks=tracks,original_mesh_payload_unchanged=True,quality_approved=False,release_approved=False),'Baked storage conditions changed')
    require(core.audit_baked_motion(asset,queries,config,scene,audit['applications'],values[4])==read(assets/'baked-motion-audit.json'),'Baked grip/floor conditions differ')
    imported=read(folder/'bake/import.json');errors=core.import_errors(imported,asset,queries);recorded=read(assets/'import-audit.json')
    payload=dict(asset_path=str(assets/'objects.glb'),resource_path=str(assets/'objects.res'),import_bake_fps=config['physics_fps'],payload=dict(channels=asset.channels,duration_s=float(clock[-1]),sample_times_s=queries.tolist(),sample_clock=core.clock_wire(queries)))
    require(read(folder/'bake/import-request.json')==payload and read(folder/'bake/default-30fps-request.json')=={**payload,'resource_path':str(folder/'bake/default-30fps-objects.res'),'import_bake_fps':30},'Bound engine import request changed')
    require(imported['import_bake_fps']==recorded['import_bake_fps']==config['physics_fps'] and errors==recorded['maximum_component_error'] and all(e<=core.POSE_LIMIT for e in errors.values()),'Configured engine import evidence differs')
    default=read(folder/'bake/default-30fps.json');default_errors=core.import_errors(default,asset,queries)
    require(default['import_bake_fps']==30 and default_errors==recorded['default_30fps_maximum_component_error'] and recorded['default_30fps_import_pass']==all(e<=core.POSE_LIMIT for e in default_errors.values()),'Default import failure changed')
    require(recorded['engine_sha256']==core.ENGINE_SHA256 and recorded['pose_component_limit']==core.POSE_LIMIT and recorded['engine_playback_verified'] is True and all(recorded[k] is False for k in ('quality_approved','release_approved')),'Import scope changed')
    require(m['exact_physical_event_timing_pass'] is audit['exact_physical_event_timing_pass'] and m['maximum_application_delay_s']==audit['maximum_application_delay_s'] and m['floor_sampled_screen_pass'] is audit['floor_sampled_screen_pass'],'Baked physical failures changed')
    composition=read(assets/'composition.json');spec=read(folder/'bake/capture-project/scene.json')
    actors={n:dict(**{**entry,'glb':'reference/'+entry['glb']},root_motion='original-embedded',end_policy='hold-original-end') for n,entry in spec['actors'].items()}
    require(composition==dict(schema='strep-baked-prop-composition-v1',duration_s=float(clock[-1]),source_duration_s=scene.duration,clock=audit['clock'],source_clock=audit['source_clock'],actors=actors,
        objects=dict(path='objects.glb',sha256=sha256(assets/'objects.glb'),modes=config['object_modes']),root_references='reference/root-motion.json',marker_intent='reference/events.json',contact_intent_scope='unchanged-authored-reference-only',parent_world_transform=values[4]['parent_world_transform'],floor_world=values[4]['floor'],quality_approved=False,release_approved=False),'Baked composition/source references changed')
    require(baked['package_sha256']==sha256(folder/'bake/baked-assets.zip'),'Baked ZIP changed')
    return baked,recorded,read(assets/'baked-motion-audit.json')


def manifest(job):
    folder=folder_for(job);state=read(folder/'pipeline.json');data=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],quality_approved=False,release_approved=False)
    if state['status']!='complete':return data
    p,values=frozen(folder,current_methods=False);r=read(folder/'result.json')
    require(r['schema']=='strep-studio-prop-bake-job-v1' and r['status']=='complete' and read(folder/'completion.json')['result_sha256']==sha256(folder/'result.json') and r['prepared_sha256']==sha256(folder/'prepared.json'),'Bake completion changed')
    require(r['source_runtime_job']==values[0].name and r['source_result_sha256']==p['source_result_sha256'] and r['source_bytes_unchanged'] is True and r['original_selected'] is True
        and all(r[k] is False for k in ('studio_selection_changed','physics_quality_approved','quality_approved','release_approved')),'Bake source/scope changed')
    require(r['source_scene_conditions_pass'] is values[1]['source_scene_conditions_pass'] and r['root_samples_pass'] is values[1]['root_samples_pass'],'Original source failures changed')
    execution=read(folder/'execution.json');baked_record=read(folder/'bake/result.json')
    require(isinstance(baked_record['files_sha256'],dict) and 0<len(baked_record['files_sha256'])<512 and all(portable(n) for n in baked_record['files_sha256']),'Portable complete baked output population required')
    execution_names={'bake/assets/'+n for n in baked_record['files_sha256']}|{'bake/assets/package.json','bake/baked-assets.zip','bake/result.json',
        'bake/capture.json','bake/capture-audit.json','bake/capture-request.json','bake/import.json','bake/default-30fps.json'}
    require(r['execution_sha256']==sha256(folder/'execution.json') and execution['schema']=='strep-studio-prop-bake-execution-v1' and set(execution['artifacts_sha256'])==execution_names
        and all(sha256(folder/n)==h for n,h in execution['artifacts_sha256'].items()) and all(execution[k] is False for k in ('quality_approved','release_approved')),'Recorded bake execution artifacts changed')
    require(set(r['files_sha256'])==set(DOWNLOADS)-{'result.json'} and all(sha256(folder/n)==h for n,h in r['files_sha256'].items()),'Complete fixed bake downloads changed')
    baked,imported,motion=verify_output(folder,p,values)
    require(r['package_sha256']==baked['package_sha256'] and r['engine_import_verified'] is baked['engine_import_verified'] and r['exact_physical_event_timing_pass'] is baked['exact_physical_event_timing_pass'] and r['maximum_application_delay_s']==baked['maximum_application_delay_s'],'Bake result conditions changed')
    data.update(source_runtime_job=r['source_runtime_job'],source_scene_conditions_pass=r['source_scene_conditions_pass'],root_samples_pass=r['root_samples_pass'],
        engine_import_verified=r['engine_import_verified'],exact_physical_event_timing_pass=r['exact_physical_event_timing_pass'],maximum_application_delay_s=r['maximum_application_delay_s'],
        floor_sampled_screen_pass=motion['floor_sampled_screen_pass'],held_grip_sampled_conditions_pass=motion['held_grip_sampled_conditions_pass'],
        default_30fps_import_pass=imported['default_30fps_import_pass'],source_bytes_unchanged=True)
    data['downloads']=[dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=sha256(folder/n)) for n in DOWNLOADS];return data


def listing():
    return dict(jobs=[dict(id=p.name,status=read(p/'pipeline.json')['status']) for p in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True) if p.is_dir() and NAME.fullmatch(p.name) and (p/'pipeline.json').is_file()])


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve();require(target.is_relative_to(folder),'Bake download escapes job')
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,TypeError,KeyError,OSError,zipfile.BadZipFile):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
