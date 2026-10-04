"""One reproducible offline object/character authoring and engine-audit job.

Any supplied action is accepted by its rig/contact schema, without an action
whitelist. This is not prompt generation or automatic physical interaction.
Optional object edits require the existing explicit two-grip bounded contract.
"""
import argparse
import re
import shutil
from pathlib import Path
from strep import ROOT, read, save, sha256, now
from action_worker_lock import worker_busy
from native_scene_contacts import SceneContacts, fields, run as contact_run
from native_scene_geometry import policy_for
from native_object_hold_fit import request_for, run as fit_run, METHODS as FIT_METHODS
from native_object_asset import run as asset_run, run_engine as object_run
from native_scene_engine import run as actor_run
from native_object_scene_engine import prepare as clock_prepare, run as combined_run, METHODS as COMBINED_METHODS
from verify_native_object_scene_engine import run as replay_run

METHODS=tuple(dict.fromkeys(FIT_METHODS+COMBINED_METHODS+('verify_native_object_scene_engine.py','native_scene_authoring_job.py')))
DIGEST=re.compile(r'[0-9a-f]{64}')


def method_names(scene):
    return METHODS if scene.objects else METHODS+('verify_native_actor_scene_engine.py',)


def require(condition, message):
    if not condition: raise ValueError(message)


def binding(path):
    path=Path(path).resolve(); return dict(path=str(path),sha256=sha256(path))


def validated(recipe_path):
    recipe_path=Path(recipe_path).resolve(); value=read(recipe_path)
    fields(value,('schema','contacts','geometry_policy','engine','object_edit'),'native scene job')
    require(value['schema']=='strep-native-scene-authoring-job-v1','Unknown native scene job schema')
    paths={}; receipts={str(recipe_path):sha256(recipe_path)}
    for name in ('contacts','geometry_policy','engine','object_edit'):
        entry=value[name]
        if name=='object_edit' and entry is None: continue
        fields(entry,('path','sha256'),'job input binding')
        require(isinstance(entry['path'],str) and bool(entry['path'].strip()),'Input path required')
        require(isinstance(entry['sha256'],str) and DIGEST.fullmatch(entry['sha256']),'Input SHA256 required')
        path=(recipe_path.parent/entry['path']).resolve()
        require(path.is_file() and sha256(path)==entry['sha256'],'Changed job input: '+name)
        paths[name]=path; receipts[str(path)]=entry['sha256']
    scene=SceneContacts(read(paths['contacts']),paths['contacts'].parent)
    require(bool(scene.objects) or 'object_edit' not in paths,'Object edits require a declared object')
    policy_for(read(paths['geometry_policy']),scene,sha256(paths['contacts']))
    if 'object_edit' in paths:request_for(scene,read(paths['object_edit']),sha256(paths['contacts']))
    receipts.update(scene.inputs)
    return value,paths,scene,receipts


def plan(contacts,policy,engine,output,object_edit=None):
    output=Path(output).resolve(); require(not output.exists(),'Fresh recipe path required')
    value=dict(schema='strep-native-scene-authoring-job-v1', contacts=binding(contacts),
        geometry_policy=binding(policy),engine=binding(engine),object_edit=None if object_edit is None else binding(object_edit))
    # Validate in memory through the same checks before publishing a recipe.
    scene=SceneContacts(read(contacts),Path(contacts).resolve().parent)
    require(bool(scene.objects) or object_edit is None,'Object edits require a declared object')
    policy_for(read(policy),scene,sha256(contacts))
    if object_edit is not None:request_for(scene,read(object_edit),sha256(contacts))
    scene.check_inputs(); output.parent.mkdir(parents=True,exist_ok=True); save(output,value)
    validated(output); return value


def run(recipe_path,output):
    output=Path(output).resolve(); require(not output.exists(),'Fresh native scene job output required')
    require(not worker_busy(),'Another local study worker is active')
    recipe,paths,scene,receipts=validated(recipe_path)
    require(not any(Path(p).is_relative_to(output) for p in receipts),'Job output contains its own input')
    methods={n:sha256(ROOT/'scripts'/n) for n in method_names(scene)}
    output.mkdir(parents=True); archive=output/'implementation'; snapshots=output/'input'; stages=[]; copies={}; derived={}
    save(output/'pipeline.json',dict(at=now(),status='processing',stage='input-snapshots',original_selected=True))
    try:
        archive.mkdir(); snapshots.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        for i,(path,digest) in enumerate(receipts.items()):
            if Path(path)==paths['engine']:continue  # Record executable hash; do not bundle its payload.
            dest=snapshots/f'{i}{Path(path).suffix}';shutil.copyfile(path,dest)
            require(sha256(dest)==digest,'Job input snapshot changed')
            copies[path]=dict(path=dest.relative_to(output).as_posix(),sha256=digest)
    except Exception as exc:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),completed_stages=stages,
            original_selected=True,quality_approved=False,release_approved=False));raise

    def unchanged():
        for p,h in receipts.items():require(sha256(p)==h,'Original job input changed')
        for n,h in methods.items():require(sha256(ROOT/'scripts'/n)==sha256(archive/n)==h,'Job implementation changed')
        for entry in copies.values():require(sha256(output/entry['path'])==entry['sha256'],'Job snapshot changed')
        for p,h in derived.items():require(sha256(p)==h,'Derived job input changed')
        for stage in stages:require(sha256(output/stage['id']/'result.json')==stage['result_sha256'],'Completed stage result changed')

    def execute(name,function,*args,**kwargs):
        unchanged(); require(not worker_busy(),'Another local study worker is active between job stages')
        save(output/'pipeline.json',dict(at=now(),status='processing',stage=name,completed_stages=stages,
            original_selected=True,quality_approved=False,release_approved=False))
        result=function(*args,**kwargs)
        if name=='source-contacts':
            # This synchronous audit deliberately has no execution-status field.
            require(result.get('status','complete')=='complete','Nonterminal stage: '+name)
            require(result.get('schema')=='strep-native-scene-contact-audit-v1'
                    and result.get('spec_sha256')==sha256(paths['contacts']) and type(result.get('passed')) is bool,
                    'Completed source contact audit schema required')
        else:require(result.get('status')=='complete','Nonterminal stage: '+name)
        require(read(output/name/'result.json')==result,'Returned stage result differs from saved evidence')
        stages.append(dict(id=name,result_sha256=sha256(output/name/'result.json')))
        unchanged(); return result

    try:
        execute('source-contacts',contact_run,paths['contacts'],output/'source-contacts')
        contacts,policy=paths['contacts'],paths['geometry_policy']; fit=None
        if 'object_edit' in paths:
            fit=execute('object-edit',fit_run,contacts,paths['object_edit'],policy,output/'object-edit')
            require(fit['actor_bytes_unchanged'] is True,'Object edit changed actor bytes')
            contacts,policy=output/'object-edit/proposal-contacts.json',output/'object-edit/geometry-policy.json'
            require(sha256(contacts)==fit['proposal_contacts_sha256'],'Object proposal differs from fit evidence')
            derived.update({str(p):sha256(p) for p in (contacts,policy)})
        if scene.objects:
            execute('objects-source',asset_run,contacts,output/'objects-source')
            execute('objects-common',clock_prepare,contacts,policy,output/'objects-source',output/'objects-common')
            common=output/'objects-common/common-policy.json'
            derived[str(common)]=sha256(common)
            execute('objects-engine',object_run,output/'objects-common',output/'objects-engine',paths['engine'])
        else:
            common=policy
        execute('actors-engine',actor_run,contacts,output/'actors-engine',geometry_policy=common,
                playback_mode='native-authoring',engine=paths['engine'])
        if scene.objects:
            combined=execute('combined-engine',combined_run,contacts,common,output/'actors-engine',output/'objects-engine',output/'combined-engine')
            replay=execute('replay',replay_run,contacts,common,output/'actors-engine',output/'objects-engine',output/'combined-engine',output/'replay')
            require(replay['combined_files_sha256'][str(output/'combined-engine/result.json')]==sha256(output/'combined-engine/result.json'), 'Replay belongs to another combined result')
        else:
            from verify_native_actor_scene_engine import run as actor_replay
            combined=read(output/'actors-engine/result.json')
            replay=execute('replay',actor_replay,contacts,common,output/'actors-engine',output/'replay')
            require(replay['producer_files_sha256'][str(output/'actors-engine/result.json')]==sha256(output/'actors-engine/result.json'), 'Replay belongs to another actor result')
        require(replay['recorded_sampled_conditions_pass'] is combined['all_sampled_conditions_pass'],'Replay decision differs')
        unchanged()
        # Completed jobs may contain failed numerical conditions. No automatic selection.
        passed=bool(combined['all_sampled_conditions_pass'] and (fit is None or fit['sampled_constraints_pass']))
        result=dict(at=now(),status='complete',schema='strep-native-scene-authoring-job-result-v1',
            recipe_sha256=sha256(recipe_path),inputs_sha256=receipts,derived_inputs_sha256=derived,source_snapshots=copies,implementation_sha256=methods,
            stages=stages,object_edit_requested=fit is not None,source_contact_conditions_pass=read(output/'source-contacts/result.json')['passed'],
            samples=combined['samples'],combined_conditions_pass=combined['all_sampled_conditions_pass'],
            object_edit_conditions_pass=None if fit is None else fit['sampled_constraints_pass'],sampled_conditions_pass=passed,
            artifacts=dict(active_contacts=str(contacts),active_policy=str(policy),common_policy='objects-common/common-policy.json' if scene.objects else None,
                objects_glb='objects-common/objects.glb' if scene.objects else None,object_animation_resource='objects-engine/native-animation.res' if scene.objects else None,
                actor_engine='actors-engine',combined_audit='combined-engine' if scene.objects else None,replay='replay'),
            original_selected=True,studio_selection_changed=False,quality_approved=False,training_admitted=False,release_approved=False,
            gpu_render_checked=False,physics_verified=False,real_time_playback_verified=False,human_review_submitted=False,
            scope='Supplied native rigs and declared objects/partners, optional explicit two-grip bounded object edit, actual headless sampled import and saved replay. No prompt generation, automatic rig transfer, physical attachment, real-time playback or human-quality approval.')
        save(output/'result.json',result);save(output/'pipeline.json',dict(at=now(),status='complete',completed_stages=stages,original_selected=True));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),completed_stages=stages,original_selected=True,
            quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('plan')
    for n in ('contacts','policy','engine','output'):q.add_argument(n,type=Path)
    q.add_argument('--object-edit',type=Path)
    q=sub.add_parser('run');q.add_argument('recipe',type=Path);q.add_argument('output',type=Path)
    a=p.parse_args()
    if a.command=='plan':plan(a.contacts,a.policy,a.engine,a.output,a.object_edit)
    else:run(a.recipe,a.output)
