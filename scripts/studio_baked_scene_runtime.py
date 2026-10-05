"""Source-bound Studio export of saved actor/prop scenes; no new live physics."""
import argparse,json,os,shutil,zipfile
from pathlib import Path
import numpy as np
import baked_scene_runtime as sdk
import studio_scene_prop_bake as bake
from studio_native_scene import NAME
from native_scene_contacts import fields
from native_engine_clock import clock_wire
from strep import ROOT,read,save,sha256,now

NAMESPACE='baked-scene-jobs'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(sdk.METHODS+bake.METHODS+('studio_baked_scene_runtime.py',)))
DOWNLOADS=('runtime/baked-runtime.zip','runtime/result.json','audit/result.json','request.json','result.json')
CONDITIONS=('source_scene_conditions_pass','root_samples_pass','exact_physical_event_timing_pass','maximum_application_delay_s','floor_sampled_screen_pass','held_grip_sampled_conditions_pass','default_30fps_import_pass')


def require(value,message):
    if not value:raise ValueError(message)


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid saved scene job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Saved scene job escapes namespace');return folder


def source(job):
    try:m=bake.manifest(job)
    except zipfile.BadZipFile as exc:raise ValueError('Selected baked source ZIP is invalid') from exc
    require(m['status']=='complete','Select a completed prop animation bake')
    return bake.folder_for(job),m


def metadata(job):
    folder,m=source(job)
    return dict(bake_job=job,source_result_sha256=sha256(folder/'result.json'),source_baked_zip_sha256=sha256(folder/'bake/baked-assets.zip'),
        **{k:m[k] for k in CONDITIONS},original_selected=True,quality_approved=False,release_approved=False)


def validate_request(payload):
    fields(payload,('bake_job','source_result_sha256'),'selected saved-scene bake')
    folder,m=source(payload['bake_job']);require(payload['source_result_sha256']==sha256(folder/'result.json'),'Selected bake result changed')
    return folder,m


def prepare(payload,folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh saved-scene job required')
    original,m=validate_request(payload);methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};folder.mkdir(parents=True)
    save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        save(folder/'request.json',payload);implementation=folder/'implementation';implementation.mkdir()
        for n in methods:shutil.copyfile(SCRIPT_ROOT/n,implementation/n)
        digest=sha256(original/'bake/baked-assets.zip');shutil.copyfile(original/'bake/baked-assets.zip',folder/'source-baked-assets.zip')
        require(sha256(folder/'source-baked-assets.zip')==digest,'Bake changed during snapshot')
        save(folder/'prepared.json',dict(schema='strep-studio-baked-scene-prepared-v1',request_sha256=sha256(folder/'request.json'),source_result_sha256=sha256(original/'result.json'),
            source_baked_zip_sha256=digest,implementation_sha256=methods,conditions={k:m[k] for k in CONDITIONS},original_selected=True,quality_approved=False,release_approved=False))
        frozen(folder);save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False))
    except Exception as exc:save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder,*,current_methods=True):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound saved-scene folder required')
    p=read(folder/'prepared.json');payload=read(folder/'request.json');original,m=validate_request(payload)
    require(p['schema']=='strep-studio-baked-scene-prepared-v1' and p['request_sha256']==sha256(folder/'request.json') and p['source_result_sha256']==sha256(original/'result.json'),'Saved-scene preparation changed')
    require(p['source_baked_zip_sha256']==sha256(original/'bake/baked-assets.zip')==sha256(folder/'source-baked-assets.zip'),'Original baked snapshot changed')
    require(p['conditions']=={k:m[k] for k in CONDITIONS} and p['original_selected'] is True and all(p[k] is False for k in ('quality_approved','release_approved')),'Original bake decisions changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete saved-scene method archive required')
    for n,h in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/n)==h,'Archived saved-scene method changed')
        if current_methods:require(sha256(SCRIPT_ROOT/n)==h,'Saved-scene implementation changed during worker')
    return p,m


def artifacts(folder,packaged):
    return ['runtime/project/'+n for n in packaged['files_sha256']]+['runtime/project/baked-runtime-v1/package.json','runtime/result.json','runtime/baked-runtime.zip',
        'runtime/source-baked-assets.zip','audit/result.json','audit/request.json','audit/actual.json','audit/source-baked-runtime.zip']


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound saved-scene folder required')
    require(read(folder/'pipeline.json')['status']=='starting' and not any((folder/n).exists() for n in ('worker.json','runtime','audit','completion.json')),'Fresh saved-scene worker required')
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        p,m=frozen(folder);save(folder/'pipeline.json',dict(status='processing',stage='saved-scene-package-and-headless-audit',original_selected=True,quality_approved=False))
        packaged=sdk.package(folder/'source-baked-assets.zip',folder/'runtime');audited=sdk.audit(folder/'runtime/baked-runtime.zip',folder/'audit');frozen(folder)
        save(folder/'execution.json',dict(schema='strep-studio-baked-scene-execution-v1',artifacts_sha256={n:sha256(folder/n) for n in artifacts(folder,packaged)},quality_approved=False,release_approved=False))
        result=dict(schema='strep-studio-baked-scene-job-v1',status='complete',source_bake_job=read(folder/'request.json')['bake_job'],prepared_sha256=sha256(folder/'prepared.json'),execution_sha256=sha256(folder/'execution.json'),
            source_result_sha256=p['source_result_sha256'],source_baked_zip_sha256=p['source_baked_zip_sha256'],package_sha256=packaged['package_sha256'],conditions=p['conditions'],
            scene_playback_verified=audited['scene_playback_verified'],exported_main_scene_verified=audited['exported_main_scene_verified'],samples=audited['samples'],callback_observations=audited['callback_observations'],
            maximum_pose_component_error=audited['maximum_pose_component_error'],source_end_hold_duration_s=audited['source_end_hold_duration_s'],source_bytes_unchanged=True,studio_selection_changed=False,original_selected=True,
            live_prop_physics=False,renderer_executed=False,human_reviewed=False,quality_approved=False,release_approved=False,files_sha256={n:sha256(folder/n) for n in DOWNLOADS if n!='result.json'})
        save(folder/'result.json',result);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False));return result
    except Exception as exc:save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def verify_output(folder,p):
    packaged=read(folder/'runtime/result.json');project=folder/'runtime/project';m=read(project/'baked-runtime-v1/package.json')
    require((folder/'audit/project/baked-runtime-v1/package.json').read_bytes()==(project/'baked-runtime-v1/package.json').read_bytes(),'Saved audit manifest differs')
    require(packaged==dict(**m,package_sha256=sha256(folder/'runtime/baked-runtime.zip')) and m['schema']=='strep-baked-scene-runtime-package-v1' and m['status']=='complete','Saved runtime manifest changed')
    require(m['source_baked_zip_sha256']==p['source_baked_zip_sha256']==sha256(folder/'runtime/source-baked-assets.zip') and m['source_bytes_unchanged'] is True,'Saved runtime source differs')
    require(all(m[k] is False for k in ('engine_executed','live_prop_physics','animation_quality_approved','release_approved')),'Saved runtime scope changed')
    require(m['methods_sha256']=={n:p['implementation_sha256'][n] for n in sdk.METHODS} and m['runtime_methods_sha256']=={n:p['implementation_sha256'][n] for n in sdk.GDS},'Saved runtime methods differ')
    with zipfile.ZipFile(folder/'runtime/baked-runtime.zip') as z,zipfile.ZipFile(folder/'source-baked-assets.zip') as original:
        names=z.namelist();require(len(names)==len(set(n.casefold() for n in names)) and len(names)<=512 and sum(i.file_size for i in z.infolist())<=1024**3,'Complete bounded saved runtime ZIP required')
        require(all(bake.portable(n) for n in names) and set(names)==set(m['files_sha256'])|{'baked-runtime-v1/package.json'} and z.read('baked-runtime-v1/package.json')==(project/'baked-runtime-v1/package.json').read_bytes(),'Complete saved runtime population required')
        require(all(sdk.member_hash(z,n)==h==sha256(project/n)==sha256(folder/'audit/project'/n) for n,h in m['files_sha256'].items()),'Saved runtime bytes changed')
        require(all(original.read(n)==z.read(n) for n in original.namelist()),'Original complete baked bytes changed')
    for n in sdk.GDS:require(m['files_sha256']['baked-runtime-v1/'+n]==p['implementation_sha256'][n],'Saved runtime SDK differs')
    config,scene,asset,clock,events=sdk.configure_bake(project,read(project/'package.json'))
    require(config==read(project/'baked-runtime-v1/runtime.json'),'Saved runtime composition differs')
    queries=np.unique(np.r_[clock,(clock[:-1]+clock[1:])/2,np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8'),scene.duration])
    request=read(folder/'audit/request.json');require(request==dict(config=config,folder=str(folder/'audit/project'),clock=clock_wire(queries)),'Exact saved-scene audit request changed')
    actual=read(folder/'audit/actual.json');require(actual['request_sha256']==sha256(folder/'audit/request.json'),'Saved-scene observation request changed')
    checked=sdk.evaluate(actual,config,scene,asset,queries,events);audited=read(folder/'audit/result.json')
    expected=dict(schema='strep-baked-scene-playback-result-v1',status='complete',at=audited['at'],source_runtime_zip_sha256=sha256(folder/'runtime/baked-runtime.zip'),engine_sha256=sdk.ENGINE_SHA256,
        actual_sha256=sha256(folder/'audit/actual.json'),**checked,renderer_executed=False,human_reviewed=False)
    require(audited==expected and sha256(folder/'audit/source-baked-runtime.zip')==audited['source_runtime_zip_sha256'],'Saved-scene playback evidence differs')
    return packaged,audited


def manifest(job):
    folder=folder_for(job);state=read(folder/'pipeline.json');data=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],quality_approved=False,release_approved=False)
    if state['status']!='complete':return data
    p,m=frozen(folder,current_methods=False);r=read(folder/'result.json')
    require(r['schema']=='strep-studio-baked-scene-job-v1' and r['status']=='complete' and read(folder/'completion.json')['result_sha256']==sha256(folder/'result.json') and r['prepared_sha256']==sha256(folder/'prepared.json'),'Saved-scene completion changed')
    require(r['source_bake_job']==read(folder/'request.json')['bake_job'] and r['source_result_sha256']==p['source_result_sha256'] and r['source_baked_zip_sha256']==p['source_baked_zip_sha256'] and r['conditions']==p['conditions'],'Saved-scene source/decisions changed')
    require(all(r[k] is True for k in ('source_bytes_unchanged','original_selected','scene_playback_verified','exported_main_scene_verified')) and all(r[k] is False for k in ('studio_selection_changed','live_prop_physics','renderer_executed','human_reviewed','quality_approved','release_approved')),'Saved-scene scope changed')
    execution=read(folder/'execution.json');packaged=read(folder/'runtime/result.json')
    require(0<len(packaged['files_sha256'])<512 and all(bake.portable(n) for n in packaged['files_sha256']),'Complete portable saved-scene artifact map required')
    require(r['execution_sha256']==sha256(folder/'execution.json') and execution['schema']=='strep-studio-baked-scene-execution-v1' and set(execution['artifacts_sha256'])==set(artifacts(folder,packaged))
        and all(sha256(folder/n)==h for n,h in execution['artifacts_sha256'].items()) and all(execution[k] is False for k in ('quality_approved','release_approved')),'Recorded saved-scene artifacts changed')
    require(set(r['files_sha256'])==set(DOWNLOADS)-{'result.json'} and all(sha256(folder/n)==h for n,h in r['files_sha256'].items()),'Complete fixed saved-scene downloads changed')
    packaged,audited=verify_output(folder,p)
    require(r['package_sha256']==packaged['package_sha256'] and all(r[k]==audited[k] for k in ('scene_playback_verified','exported_main_scene_verified','samples','callback_observations','maximum_pose_component_error','source_end_hold_duration_s')),'Saved-scene result differs')
    data.update(**{k:r[k] for k in ('source_bake_job','scene_playback_verified','exported_main_scene_verified','samples','callback_observations','maximum_pose_component_error','source_end_hold_duration_s','live_prop_physics')},**r['conditions'])
    data['downloads']=[dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=sha256(folder/n)) for n in DOWNLOADS];return data


def listing():
    return dict(jobs=[dict(id=p.name,status=read(p/'pipeline.json')['status']) for p in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True) if p.is_dir() and NAME.fullmatch(p.name) and (p/'pipeline.json').is_file()])


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve();require(target.is_relative_to(folder),'Saved-scene download escapes job')
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,TypeError,KeyError,OSError,zipfile.BadZipFile):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
