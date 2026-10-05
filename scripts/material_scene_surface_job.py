"""Explicit surface-facing acceptance for portable material scene authoring.

Run point/geometry authoring, imported surface auditing and replay serially.
Only the surface policy's contact-file binding changes after an object edit.
"""
import argparse
import copy
from pathlib import Path
import shutil
from action_worker_lock import worker_busy
from material_scene_package import verify as package_verify,run as package_run,METHODS as PACKAGE_METHODS
from material_patch_bundle import fields,sha_binding,files
from native_imported_surface_contact import run as surface_run,verify as surface_verify,METHODS as SURFACE_METHODS
from native_surface_contact import policy_for
from native_scene_contacts import SceneContacts
from rig_material_identity import digest
from rig_material_patch import require
from strep import ROOT,read,save,sha256,now

METHODS=tuple(dict.fromkeys(PACKAGE_METHODS+SURFACE_METHODS+('material_scene_surface_job.py',)))
SCHEMA='strep-material-scene-surface-job-v1'


def binding(path):
    path=Path(path).resolve();require(path.is_file(),'Explicit existing local input required')
    return dict(path=str(path),sha256=sha256(path))


def validated(recipe):
    recipe=Path(recipe).resolve();value=read(recipe)
    fields(value,('schema','package','surface_policy','engine','package_files_sha256','implementation_sha256'),'material surface job')
    require(value['schema']==SCHEMA,'Unknown material surface job schema')
    paths={}
    for name in ('package','surface_policy','engine'):
        fields(value[name],('path','sha256'),'explicit job input')
        require(isinstance(value[name]['path'],str) and bool(value[name]['path']),'Explicit local input path required')
        sha_binding(value[name]['sha256'],'job input binding')
        paths[name]=(recipe.parent/value[name]['path']).resolve()
        require(paths[name].is_file() and sha256(paths[name])==value[name]['sha256'],'Changed material surface input: '+name)
    require(paths['package'].name=='result.json','Bind the complete package result')
    folder=paths['package'].parent
    package_verify(folder,expected_result_sha256=value['package']['sha256'])
    require(files(folder)==value['package_files_sha256'],'Complete source package changed')
    require(0<paths['surface_policy'].stat().st_size<=8*1024**2,'Bounded explicit surface policy required')
    scene=SceneContacts(read(folder/'contacts.json'),folder)
    policy_for(read(paths['surface_policy']),scene,sha256(folder/'contacts.json'))
    require(set(value['implementation_sha256'])==set(METHODS),'Complete surface job methods required')
    for n,h in value['implementation_sha256'].items():
        require(sha256(ROOT/'scripts'/n)==h,'Surface job method changed')
    scene.check_inputs()
    return value,paths,scene


def plan(package,surface_policy,engine,output):
    package,surface_policy,engine,output=[Path(p).resolve() for p in (package,surface_policy,engine,output)]
    require(not output.exists() and not output.is_relative_to(package),'Fresh recipe outside the authoring package required')
    package_verify(package)
    require(surface_policy.is_file() and 0<surface_policy.stat().st_size<=8*1024**2,'Bounded explicit surface policy required')
    scene=SceneContacts(read(package/'contacts.json'),package)
    policy_for(read(surface_policy),scene,sha256(package/'contacts.json'))
    value=dict(schema=SCHEMA,package=binding(package/'result.json'),surface_policy=binding(surface_policy),engine=binding(engine),
        package_files_sha256=files(package),implementation_sha256={n:sha256(ROOT/'scripts'/n) for n in METHODS})
    scene.check_inputs();save(output,value);validated(output);return value


def active_scene(original,original_base,contacts,edit):
    """Protect all intent except the explicitly editable object's keyframes."""
    active=read(contacts);scene=SceneContacts(active,contacts.parent)
    left,right=copy.deepcopy(original),copy.deepcopy(active)
    require(set(left['actors'])==set(right['actors']),'Complete original actor population required')
    for name in left['actors']:
        expected=left['actors'][name]
        require(sha256(original_base/expected['glb'])==expected['sha256'],'Original actor changed')
        require(sha256(contacts.parent/right['actors'][name]['glb'])==expected['sha256'],'Active actor bytes changed')
        left['actors'][name].pop('glb');right['actors'][name].pop('glb')
    if edit is not None:
        name=edit['object'];require(name in left['objects'] and name in right['objects'],'Explicit edited object required')
        left['objects'][name].pop('keyframes');right['objects'][name].pop('keyframes')
    require(digest(left)==digest(right),'Active scene changes protected contact, actor, object or timing intent')
    scene.check_inputs();return scene


def run(recipe,output):
    recipe,output=[Path(p).resolve() for p in (recipe,output)]
    require(not worker_busy(),'Another production worker owns the lock')
    require(not output.exists(),'Fresh material surface execution required')
    value,paths,source=validated(recipe);package=paths['package'].parent
    require(not output.is_relative_to(package) and not any(p.is_relative_to(output) for p in paths.values()),
            'Execution cannot contain or mutate its own source inputs')
    inputs={str(recipe):sha256(recipe),**{str(p):sha256(p) for p in paths.values()}}
    output.mkdir(parents=True)
    try:
        save(output/'pipeline.json',dict(status='processing',stage='source-snapshots',original_selected=True))
        shutil.copyfile(recipe,output/'source-recipe.json');shutil.copyfile(paths['surface_policy'],output/'source-surface-policy.json')
        for n,h in value['implementation_sha256'].items():
            dest=output/'implementation'/n;dest.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'scripts'/n,dest)
            require(sha256(dest)==h,'Surface method changed during copying')
        save(output/'pipeline.json',dict(status='processing',stage='point-and-geometry-job',original_selected=True))
        execution=package_run(package,output/'authoring-execution',paths['engine'])
        execution_path=output/'authoring-execution/result.json';execution_hash=sha256(execution_path)
        require(digest(read(execution_path))==digest(execution),'Authoring execution receipt differs')
        require(execution['status']=='complete' and execution['original_selected'] and not execution['quality_approved']
                and not execution['release_approved'],'Completed diagnostic authoring execution required')
        job=output/'authoring-execution/engine-job';engine=read(job/'result.json')
        require(sha256(job/'result.json')==execution['engine_result_sha256'],'Authoring engine result binding differs')
        engine_hash=sha256(job/'result.json')
        contacts=Path(engine['artifacts']['active_contacts']).resolve()
        require(contacts.is_relative_to(output),'Active contacts must belong to this execution')
        edit=read(package/'draft.json')['object_edit']
        scene=active_scene(read(package/'contacts.json'),package,contacts,edit)
        effective=copy.deepcopy(read(paths['surface_policy']));effective['contacts_sha256']=sha256(contacts)
        policy_for(effective,scene,sha256(contacts));save(output/'effective-surface-policy.json',effective)
        common=(job/'objects-common/common-policy.json') if scene.objects else Path(engine['artifacts']['active_policy']).resolve()
        require(common.resolve().is_relative_to(output),'Active geometry policy must belong to this execution')
        save(output/'pipeline.json',dict(status='processing',stage='imported-surface-contacts',original_selected=True))
        surface=surface_run(contacts,output/'effective-surface-policy.json',common,job/'actors-engine',output/'surface-audit',
            object_dir=job/'objects-engine' if scene.objects else None)
        require(surface['status']=='complete','Completed imported surface diagnostic required')
        save(output/'pipeline.json',dict(status='processing',stage='surface-replay',original_selected=True))
        replay=surface_verify(output/'surface-audit')
        require(replay['status']=='complete' and replay['result_sha256']==sha256(output/'surface-audit/result.json'),
                'Complete bound surface replay required')
        save(output/'surface-replay.json',replay)
        require(type(execution['sampled_conditions_pass']) is bool and type(surface['native_and_imported_surface_contacts_pass']) is bool,
                'Explicit boolean diagnostic decisions required')
        require(all(sha256(p)==h for p,h in inputs.items()),'Original surface job input changed')
        validated(recipe)
        require(sha256(output/'source-recipe.json')==inputs[str(recipe)]
                and sha256(output/'source-surface-policy.json')==value['surface_policy']['sha256'],'Copied source intent changed')
        for n,h in value['implementation_sha256'].items():require(sha256(output/'implementation'/n)==h,'Archived surface job method changed')
        require(digest(read(output/'effective-surface-policy.json'))==digest(effective),'Effective authored normals or limits changed')
        require(sha256(execution_path)==execution_hash and sha256(job/'result.json')==engine_hash,
                'Authoring receipts changed during surface audit')
        result=dict(schema=SCHEMA,status='complete',at=now(),recipe_sha256=inputs[str(recipe)],
            authoring_execution_result_sha256=execution_hash,
            surface_result_sha256=sha256(output/'surface-audit/result.json'),surface_replay_sha256=sha256(output/'surface-replay.json'),
            point_and_geometry_conditions_pass=execution['sampled_conditions_pass'],
            native_and_imported_surface_conditions_pass=surface['native_and_imported_surface_contacts_pass'],
            sampled_conditions_pass=execution['sampled_conditions_pass'] and surface['native_and_imported_surface_contacts_pass'],
            surface_counts=surface['counts'],default_object_import_comparison_preserved=bool(scene.objects),
            original_selected=True,studio_selection_changed=False,anatomical_review_pending=True,
            gpu_render_checked=False,physics_verified=False,real_time_playback_verified=False,
            human_reviewed=False,quality_approved=False,training_admitted=False,release_approved=False)
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('plan')
    for n in ('package','surface_policy','engine','output'):p.add_argument(n,type=Path)
    p=sub.add_parser('run')
    for n in ('recipe','output'):p.add_argument(n,type=Path)
    args=parser.parse_args()
    if args.command=='plan':plan(args.package,args.surface_policy,args.engine,args.output)
    else:run(args.recipe,args.output)
