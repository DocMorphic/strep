"""Source-bound Studio scene drafts and offline native authoring jobs."""
import argparse
import copy
import os
from pathlib import Path
import re
import shutil
import zipfile
import hashlib
import json
import numpy as np
from urllib.parse import urlsplit
from strep import ROOT,read,save,sha256,now
from native_scene_contacts import SceneContacts,fields
from native_scene_geometry import policy_for
from native_object_hold_fit import request_for
from native_scene_authoring_job import plan,run as author,validated,METHODS as AUTHOR_METHODS,method_names as author_methods

NAMESPACE='native-scene-jobs'
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(AUTHOR_METHODS+('studio_native_scene.py','native_contact_revision.py','native_correction_lineage.py')))
ASSET_PREFIXES=('/files/rig-jobs/','/files/character-assets/','/files/native-correction-previews/','/files/native-support-jobs/','/files/native-scene-jobs/','/files/native-scene-fit-jobs/')


def require(condition,message):
    if not condition:raise ValueError(message)


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid native scene job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Native scene job escapes namespace');return folder


def actor_metadata(job,variant):
    from studio_native_support import metadata
    result=metadata(job,variant)
    return {k:result[k] for k in ('source_job','variant','label','source_url','glb_sha256','duration_s','animation_index')}


def validate_request(payload,resolver,*,require_objects=False):
    from native_contact_revision import validate
    ordinary,revision=validate(payload)
    if revision is not None:validate_request(revision['baseline'],resolver,require_objects=require_objects)
    payload=ordinary
    require(payload['schema']=='strep-studio-native-scene-v1','Studio native scene schema required')
    spec=copy.deepcopy(payload['scene'])
    fields(spec,('schema','duration_s','actors','objects','contacts'),'native scene')
    require(isinstance(spec['actors'],dict) and 1<=len(spec['actors'])<=8,'Choose 1-8 actors')
    sources={}
    for name,entry in spec['actors'].items():
        fields(entry,('glb','sha256','animation_index','placement'),'Studio actor')
        url=entry['glb'];require(isinstance(url,str),'Served actor URL required')
        parsed=urlsplit(url)
        require(not parsed.scheme and not parsed.netloc and not parsed.query and not parsed.fragment
            and parsed.path==url and url.startswith(ASSET_PREFIXES),'Choose a served character clip')
        path=resolver(url)
        require(path is not None,'Character clip is not served')
        path=Path(path).resolve()
        require(path.is_relative_to((ROOT/'reports').resolve()) and path.suffix.lower()=='.glb'
            and path.is_file(),'Existing workspace character GLB required')
        require(sha256(path)==entry['sha256'],'Selected character clip changed')
        sources[name]=dict(url=url,path=str(path),sha256=entry['sha256'])
        entry['glb']=str(path)
    scene=SceneContacts(spec,ROOT)
    if require_objects:require(bool(scene.objects),'This asset builder requires at least one scene object; character-only contact previews are supported separately')
    fields(payload['geometry'],('clock','limits','planes'),'declared scene geometry')
    geometry=dict(schema='strep-native-scene-geometry-v1',contacts_sha256='draft',**copy.deepcopy(payload['geometry']))
    policy_for(geometry,scene,'draft')
    edit=copy.deepcopy(payload['object_edit'])
    if edit is not None:
        fields(edit,('schema','object','contact_ids','edit_window_s','maximum_translation_m',
            'maximum_rotation_degrees','maximum_keys'),'explicit object edit')
        request_for(scene,dict(contacts_sha256='draft',**edit),'draft')
    scene.check_inputs()
    return spec,geometry,edit,sources


def method_names(payload,*,corrections=None):
    result=METHODS if payload['scene']['objects'] else METHODS+('verify_native_actor_scene_engine.py',)
    if corrections is None:
        from native_correction_lineage import has_origins
        corrections=has_origins(payload)
    if corrections:
        from studio_native_scene_fit import METHODS as CORRECTION_METHODS
        result=tuple(dict.fromkeys(result+CORRECTION_METHODS+('native_correction_lineage.py',)))
    return result


def revision_preview(payload,resolver):
    """Read-only exact intent comparison and endpoint positions, not a hold audit."""
    from native_contact_revision import validate,portable_record
    _,revision=validate(payload)
    require(revision is not None,'Explicit contact revision required')
    digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    methods={n:sha256(SCRIPT_ROOT/n) for n in method_names(payload)}
    spec,_,_,sources=validate_request(payload,resolver,require_objects=False)
    original_spec,_,_,_=validate_request(revision['baseline'],resolver,require_objects=False)
    original=SceneContacts(original_spec,ROOT);changed=SceneContacts(spec,ROOT);observations=[]
    def inspect(scene,entry):
        row=entry['authored'];times=np.unique(row['interval_s']);target=row['target']
        points=scene.actor_points(row['actor'],entry['ids'],times)
        if row['reduction']=='centroid':points=points.mean(axis=1,keepdims=True)
        if target['space']=='actor':
            goal=scene.actor_points(target['actor'],entry['target_ids'],times)
            if target['reduction']=='centroid':goal=goal.mean(axis=1,keepdims=True)
        elif target['space']=='world':goal=np.repeat(entry['target_ids'][None],len(times),axis=0)
        else:
            p,r=scene.object_poses(target['object'],times);goal=np.einsum('fij,vj->fvi',r,entry['target_ids'])+p[:,None]
        return dict(times_s=times.tolist(),source_world_m=points.tolist(),target_world_m=goal.tolist(),
            separation_m=np.linalg.norm(points-goal,axis=2).tolist())
    for edit in revision['edits']:
        before=next(e for e in original.rows if e['authored']['id']==edit['id'])
        after=next(e for e in changed.rows if e['authored']['id']==edit['id'])
        observations.append(dict(id=edit['id'],original_contact=before['authored'],authored_contact=after['authored'],
            original_endpoint_inspection=inspect(original,before),authored_endpoint_inspection=inspect(changed,after)))
    original.check_inputs();changed.check_inputs()
    require(all(sha256(SCRIPT_ROOT/n)==h for n,h in methods.items()),'Revision preview implementation changed')
    return dict(schema='strep-native-contact-revision-preview-v1',draft_sha256=digest(payload),
        baseline_sha256=digest(revision['baseline']),implementation_sha256=methods,
        actor_sha256={n:s['sha256'] for n,s in sources.items()},changes=observations,record=portable_record(payload),
        original_selected=True,animation_edited=False,anatomical_review_pending=True,quality_approved=False,
        training_admitted=False,release_approved=False,
        scope='Explicit new contact intent; start/end source pose inspection only, not whole-hold acceptance, fitting, collision or anatomical approval.')


def prepare(payload,folder,resolver):
    folder=Path(folder).resolve()
    require(folder==folder_for(folder.name) and not folder.exists(),'Fresh Studio scene folder required')
    spec,geometry,edit,sources=validate_request(payload,resolver)
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    require(engine.is_file(),'Install the configured local Godot runtime before building scene assets')
    methods={n:sha256(SCRIPT_ROOT/n) for n in method_names(payload)}
    folder.mkdir(parents=True);save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        archive=folder/'implementation';archive.mkdir();inputs=folder/'input';inputs.mkdir()
        for n in methods:shutil.copyfile(SCRIPT_ROOT/n,archive/n)
        for i,(name,source) in enumerate(sources.items()):
            dest=inputs/f'actor-{i}.glb';shutil.copyfile(source['path'],dest)
            require(sha256(dest)==sha256(source['path'])==source['sha256'],'Scene actor changed during snapshot')
            source['snapshot']=dest.relative_to(folder).as_posix();spec['actors'][name]['glb']=str(dest)
        save(folder/'draft.json',payload);save(folder/'contacts.json',spec);digest=sha256(folder/'contacts.json')
        from native_correction_lineage import has_origins,snapshot
        correction_lineage=snapshot(payload,folder/'correction-lineage') if has_origins(payload) else None
        geometry['contacts_sha256']=digest;save(folder/'geometry-policy.json',geometry)
        edit_path=None
        if edit is not None:
            edit['contacts_sha256']=digest;edit_path=folder/'object-edit.json';save(edit_path,edit)
        plan(folder/'contacts.json',folder/'geometry-policy.json',engine,folder/'recipe.json',edit_path)
        names=['draft.json','contacts.json','geometry-policy.json','recipe.json']+(['object-edit.json'] if edit is not None else [])
        prepared=dict(schema='strep-studio-native-scene-prepared-v1',sources=sources,
            correction_lineage=correction_lineage,
            contact_revision_requested='contact_revision' in payload,
            files_sha256={n:sha256(folder/n) for n in names},implementation_sha256=methods,
            engine_path=str(engine),engine_sha256=sha256(engine),original_selected=True,quality_approved=False,
            training_admitted=False,release_approved=False,at=now())
        save(folder/'prepared.json',prepared);frozen(folder)
        save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False));return prepared
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder,*,current_methods=True):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Studio native scene folder required')
    p=read(folder/'prepared.json')
    require(p['schema']=='strep-studio-native-scene-prepared-v1' and p['original_selected'] is True
        and all(p[k] is False for k in ('quality_approved','training_admitted','release_approved')),'Unapproved source scene required')
    draft=read(folder/'draft.json')
    lineage=p.get('correction_lineage')
    from native_correction_lineage import has_origins,verify
    if current_methods:require((lineage is not None)==has_origins(draft),'Scene correction lineage selection changed')
    expected_methods=set(method_names(draft,corrections=lineage is not None))
    legacy=not current_methods and 'contact_revision' not in draft and 'native_contact_revision.py' not in p['implementation_sha256']
    if legacy:expected_methods.remove('native_contact_revision.py')
    if not current_methods and 'correction_lineage' not in p and 'native_correction_lineage.py' not in p['implementation_sha256']:
        expected_methods.remove('native_correction_lineage.py')
    require(set(p['implementation_sha256'])==expected_methods,'Complete Studio scene methods required')
    if lineage is not None:verify(draft,folder/'correction-lineage',lineage)
    require(p.get('contact_revision_requested',False)==('contact_revision' in draft),'Scene revision selection changed')
    for n,h in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/n)==h,'Scene method archive changed')
        if current_methods:require(sha256(SCRIPT_ROOT/n)==h,'Scene implementation changed')
    expected={'draft.json','contacts.json','geometry-policy.json','recipe.json'}
    edit=draft['object_edit']
    from native_contact_revision import validate
    validate(draft)
    if edit is not None:expected.add('object-edit.json')
    require(set(p['files_sha256'])==expected,'Complete scene draft receipts required')
    for n,h in p['files_sha256'].items():require(sha256(folder/n)==h,'Scene draft changed')
    spec=copy.deepcopy(draft['scene'])
    require(set(p['sources'])==set(spec['actors']),'Complete scene actor snapshots required')
    for i,(name,s) in enumerate(p['sources'].items()):
        require(spec['actors'][name]['glb']==s['url'] and spec['actors'][name]['sha256']==s['sha256'],'Scene source selection changed')
        saved=(folder/s['snapshot']).resolve()
        require(s['snapshot']==f'input/actor-{i}.glb' and saved.parent==folder/'input','Scene actor snapshot escapes input')
        require(sha256(s['path'])==sha256(saved)==s['sha256'],'Original or saved scene actor changed')
        spec['actors'][name]['glb']=str(saved)
    require(read(folder/'contacts.json')==spec,'Scene snapshot changes authoring inputs')
    expected_geometry=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(folder/'contacts.json'),**draft['geometry'])
    require(read(folder/'geometry-policy.json')==expected_geometry,'Scene geometry changes authoring limits')
    if edit is not None:require(read(folder/'object-edit.json')==dict(contacts_sha256=sha256(folder/'contacts.json'),**edit),'Scene object edit changes authoring bounds')
    value,paths,scene,_=validated(folder/'recipe.json')
    require(paths['contacts']==folder/'contacts.json' and paths['geometry_policy']==folder/'geometry-policy.json'
        and paths['engine']==Path(p['engine_path']) and sha256(paths['engine'])==p['engine_sha256'],'Scene recipe selects different inputs')
    require(paths.get('object_edit')==(folder/'object-edit.json' if edit is not None else None),'Scene edit selection changed')
    return p


def download_names(prepared):
    actors_only='verify_native_actor_scene_engine.py' in prepared['implementation_sha256']
    return ({'correction-lineage/record.json'} if prepared.get('correction_lineage') is not None else set()) | ({'exports/contact-revision.json'} if prepared.get('contact_revision_requested',False) else set()) | {f'input/actor-{i}.glb' for i in range(len(prepared['sources']))} | {
        'authoring/result.json','authoring/replay/result.json','assets.zip'} | ({'authoring/actors-engine/geometry.json'} if actors_only else {
        'authoring/objects-common/objects.glb','authoring/objects-engine/native-animation.res','authoring/combined-engine/geometry.json'}) | {
        f'authoring/actors-engine/{name}-animation.res' for name in prepared['sources']}


def package(folder,prepared,result):
    """Portable relative actor paths; geometry/contact limits and GLB bytes unchanged."""
    exports=folder/'exports';exports.mkdir()
    active=Path(result['artifacts']['active_contacts']).resolve()
    require(active.is_relative_to(folder/'authoring') or active==folder/'contacts.json','Scene packaging source escapes job')
    scene=read(active)
    for i,(name,source) in enumerate(prepared['sources'].items()):
        require(scene['actors'][name]['sha256']==source['sha256'],'Scene package changes actor bytes')
        scene['actors'][name]['glb']=f'actors/{i}.glb'
    save(exports/'scene.json',scene)
    policy=read(folder/'authoring/objects-common/common-policy.json' if scene['objects'] else folder/'geometry-policy.json');policy['contacts_sha256']=sha256(exports/'scene.json')
    save(exports/'geometry-policy.json',policy)
    files={'scene.json':exports/'scene.json','geometry-policy.json':exports/'geometry-policy.json'}
    if scene['objects']:
        files.update({'objects.glb':folder/'authoring/objects-common/objects.glb',
            'animations/objects.res':folder/'authoring/objects-engine/native-animation.res'})
    for i,(name,source) in enumerate(prepared['sources'].items()):
        files[f'actors/{i}.glb']=folder/source['snapshot']
        files[f'animations/{name}.res']=folder/f'authoring/actors-engine/{name}-animation.res'
    if 'contact_revision' in read(folder/'draft.json'):
        from native_contact_revision import portable_record
        record=portable_record(read(folder/'draft.json'))
        require(record['authored_contacts']==scene['contacts'],'Scene export changes revised contact intent')
        record['portable_scene_sha256']=sha256(exports/'scene.json');save(exports/'contact-revision.json',record)
        files['contact-revision.json']=exports/'contact-revision.json'
    if prepared.get('correction_lineage') is not None:
        from native_correction_lineage import verify,package_files
        verify(read(folder/'draft.json'),folder/'correction-lineage',prepared['correction_lineage'])
        files.update(package_files(folder/'correction-lineage',prepared['correction_lineage']))
    receipts={n:sha256(path) for n,path in files.items()}
    save(exports/'package.json',dict(schema='strep-native-scene-asset-package-v1',files_sha256=receipts,
        selected_animations={name:a['animation_index'] for name,a in scene['actors'].items()},
        source_result_sha256=sha256(folder/'authoring/result.json'),sampled_conditions_pass=result['sampled_conditions_pass'],
        original_selected=True,quality_approved=False,release_approved=False,root_event_tracks_included=False,
        scope='Unchanged supplied character clips, sampled native character/object resources and declared scene/contact geometry. Engine/runtime/human requirements remain separate; character licenses remain applicable.'))
    files['package.json']=exports/'package.json'
    with zipfile.ZipFile(folder/'assets.zip','x',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
        for name,path in files.items():archive.write(path,name)
    require(all(sha256(path)==h for n,h in receipts.items() for path in [files[n]]),'Scene package inputs changed')
    with zipfile.ZipFile(folder/'assets.zip') as archive:
        require(set(archive.namelist())==set(files),'Scene package population changed')
        for name,path in files.items():
            digest=hashlib.sha256()
            with archive.open(name) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            require(digest.hexdigest()==sha256(path),'Scene package bytes differ')
    return sha256(folder/'assets.zip')


def run(folder):
    folder=Path(folder).resolve()
    require(folder==folder_for(folder.name),'Studio native scene folder required')
    require(read(folder/'pipeline.json')['status']=='starting' and not (folder/'worker.json').exists()
        and not (folder/'authoring').exists() and not (folder/'completion.json').exists(),'Fresh prepared scene worker required')
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        prepared=frozen(folder);save(folder/'pipeline.json',dict(status='processing',original_selected=True,quality_approved=False))
        result=author(folder/'recipe.json',folder/'authoring');frozen(folder)
        require(read(folder/'authoring/result.json')==result and result['status']=='complete','Terminal saved scene authoring required')
        outputs={f'input/actor-{i}.glb':dict(label=f'Character clip: {name}',sha256=s['sha256'])
            for i,(name,s) in enumerate(prepared['sources'].items())}
        actor_only=not read(folder/'contacts.json')['objects']
        downloads=[('authoring/result.json','Measured result'),('authoring/replay/result.json','Replay verification')]
        downloads+= [('authoring/actors-engine/geometry.json','Scene geometry')] if actor_only else [
            ('authoring/objects-common/objects.glb','Object clip'),('authoring/objects-engine/native-animation.res','Godot object animation'),('authoring/combined-engine/geometry.json','Scene geometry')]
        for relative,label in downloads:
            outputs[relative]=dict(label=label,sha256=sha256(folder/relative))
        for name in prepared['sources']:
            relative=f'authoring/actors-engine/{name}-animation.res';outputs[relative]=dict(label=f'Godot character animation: {name}',sha256=sha256(folder/relative))
        outputs['assets.zip']=dict(label='Scene asset package',sha256=package(folder,prepared,result))
        if prepared.get('contact_revision_requested',False):
            outputs['exports/contact-revision.json']=dict(label='Original and revised contact intent',sha256=sha256(folder/'exports/contact-revision.json'))
        if prepared.get('correction_lineage') is not None:
            outputs['correction-lineage/record.json']=dict(label='Character correction provenance',sha256=sha256(folder/'correction-lineage/record.json'))
        frozen(folder)
        completion=dict(schema='strep-studio-native-scene-completion-v1',prepared_sha256=sha256(folder/'prepared.json'),
            result_sha256=sha256(folder/'authoring/result.json'),replay_sha256=sha256(folder/'authoring/replay/result.json'),
            downloads=outputs,samples=result['samples'],sampled_conditions_pass=result['sampled_conditions_pass'],
            original_selected=True,studio_selection_changed=False,quality_approved=False,training_admitted=False,release_approved=False)
        save(folder/'completion.json',completion);save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False))
        return completion
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False))
        raise


def manifest(job):
    folder=folder_for(job);pipeline=read(folder/'pipeline.json')
    data=dict(id=job,status=pipeline['status'],error=pipeline.get('error'),original_selected=True,
        quality_approved=False,release_approved=False,downloads=[])
    child=folder/'authoring/pipeline.json'
    if child.is_file():
        progress=read(child);data['stage']=progress.get('stage');data['completed_stages']=progress.get('completed_stages',[])
    if pipeline['status']!='complete':return data
    prepared=frozen(folder,current_methods=False);c=read(folder/'completion.json');r=read(folder/'authoring/result.json')
    require(c['schema']=='strep-studio-native-scene-completion-v1' and c['prepared_sha256']==sha256(folder/'prepared.json')
        and c['result_sha256']==sha256(folder/'authoring/result.json') and c['replay_sha256']==sha256(folder/'authoring/replay/result.json'),'Scene completion changed')
    require(r['status']=='complete' and r['original_selected'] is True and c['original_selected'] is True
        and c['samples']==r['samples'] and c['sampled_conditions_pass'] is r['sampled_conditions_pass']
        and all(c[k] is False for k in ('studio_selection_changed','quality_approved','training_admitted','release_approved')),'Scene decisions changed')
    require(all(r[k] is False for k in ('studio_selection_changed','quality_approved','training_admitted','release_approved',
        'gpu_render_checked','physics_verified','real_time_playback_verified','human_review_submitted')),'Scene authoring approval changed')
    scene=SceneContacts(read(folder/'contacts.json'),folder)
    require(r['implementation_sha256']=={n:prepared['implementation_sha256'][n] for n in author_methods(scene)},'Scene authoring methods changed')
    require(r['recipe_sha256']==sha256(folder/'recipe.json') and r['object_edit_requested']==(read(folder/'draft.json')['object_edit'] is not None),'Scene authoring input selection changed')
    for path,digest in {**r['inputs_sha256'],**r['derived_inputs_sha256']}.items():
        require(sha256(path)==digest,'Scene authoring input changed')
    for name,digest in r['implementation_sha256'].items():
        require(sha256(folder/'authoring/implementation'/name)==digest,'Scene authoring method archive changed')
    expected_stages=['source-contacts']+(['object-edit'] if r['object_edit_requested'] else [])+(
        ['objects-source','objects-common','objects-engine','actors-engine','combined-engine','replay'] if scene.objects else ['actors-engine','replay'])
    require([s['id'] for s in r['stages']]==expected_stages,'Complete ordered scene stages required')
    for stage in r['stages']:
        require(stage['id'] in ('source-contacts','object-edit','objects-source','objects-common','objects-engine','actors-engine','combined-engine','replay')
            and sha256(folder/'authoring'/stage['id']/'result.json')==stage['result_sha256'],'Scene stage result changed')
        stage_folder=folder/'authoring'/stage['id'];record=read(stage_folder/'result.json')
        for relative,digest in record.get('files_sha256',{}).items():
            path=(stage_folder/relative).resolve();require(path.is_relative_to(stage_folder)
                and sha256(path)==digest,'Scene producer artifact changed')
        for name,digest in record.get('implementation_sha256',{}).items():
            method_folder=folder/'authoring/objects-common' if stage['id']=='objects-engine' else stage_folder
            require(name in prepared['implementation_sha256'] and digest==prepared['implementation_sha256'][name]
                and sha256(method_folder/'implementation'/name)==digest,'Scene producer method changed')
    actor_folder=folder/'authoring/actors-engine';actor_result=read(actor_folder/'result.json')
    for filename,key in [('engine-output.json','engine_output_sha256'),('raw-engine-receipt.json','raw_engine_receipt_sha256'),
            ('native-observations.npz','native_observations_sha256'),('imported-contact-observations.npz','imported_contact_observations_sha256'),('geometry.json','geometry_sha256')]:
        require(sha256(actor_folder/filename)==actor_result[key],'Scene actor observation changed')
    geometry=read(actor_folder/'geometry.json')
    require(sha256(actor_folder/'geometry-observations.npz')==geometry['observations_sha256']
        and sha256(actor_folder/'geometry-observations.npz.receipt.json')==geometry['observation_receipt_sha256'],'Scene actor geometry changed')
    replay=read(folder/'authoring/replay/result.json');producer='combined-engine' if scene.objects else 'actors-engine'
    combined=read(folder/'authoring'/producer/'result.json')
    require(replay['producer_implementation_sha256']==combined['implementation_sha256'],'Scene replay producer methods changed')
    verifier='verify_native_object_scene_engine.py' if scene.objects else 'verify_native_actor_scene_engine.py'
    require(sha256(folder/'authoring/replay/verifier.py')==prepared['implementation_sha256'][verifier],'Scene replay method changed')
    require(replay['status']=='complete' and replay['all_replayed_observations_exact'] is True
        and replay['recorded_sampled_conditions_pass'] is combined['all_sampled_conditions_pass']
        and replay['combined_files_sha256' if scene.objects else 'producer_files_sha256'].get(str(folder/'authoring'/producer/'result.json'))==sha256(folder/'authoring'/producer/'result.json'),
        'Scene replay binding changed')
    if not scene.objects:
        require(r['object_edit_requested'] is False and r['object_edit_conditions_pass'] is None
            and r['artifacts']['common_policy'] is None and r['artifacts']['objects_glb'] is None
            and r['artifacts']['object_animation_resource'] is None and r['artifacts']['combined_audit'] is None,'Actor-only job invents object artifacts')
        for path,digest in replay['producer_files_sha256'].items():require(sha256(path)==digest,'Actor-only replay source changed')
    require(r['samples']==combined['samples']==replay['samples'] and r['source_contact_conditions_pass'] is read(folder/'authoring/source-contacts/result.json')['passed'],'Scene source report differs')
    if r['object_edit_requested']:require(r['object_edit_conditions_pass'] is read(folder/'authoring/object-edit/result.json')['sampled_constraints_pass'],'Scene object edit decision differs')
    passed=bool(combined['all_sampled_conditions_pass'] and (r['object_edit_conditions_pass'] is None or r['object_edit_conditions_pass']))
    require(r['sampled_conditions_pass'] is passed,'Scene sampled decision differs')
    require(set(c['downloads'])==download_names(prepared),'Complete fixed scene download population required')
    for relative,entry in c['downloads'].items():
        path=(folder/relative).resolve();require(path.is_relative_to(folder) and path.suffix in ('.json','.glb','.res','.zip')
            and sha256(path)==entry['sha256'],'Scene download changed')
        data['downloads'].append(dict(label=entry['label'],url=f'/files/{NAMESPACE}/{job}/{relative}',sha256=entry['sha256']))
    data.update(samples=c['samples'],sampled_conditions_pass=c['sampled_conditions_pass'],
        source_contacts_pass=r['source_contact_conditions_pass'],object_edit_pass=r['object_edit_conditions_pass'],
        stages=r['stages'],result_sha256=c['result_sha256'],scope=r['scope'])
    return data


def listing():
    jobs=[];base=ROOT/'reports'/NAMESPACE
    for folder in sorted(base.glob('*'),reverse=True):
        if not folder.is_dir() or not NAME.fullmatch(folder.name) or not (folder/'pipeline.json').is_file():continue
        try:
            state=read(folder/'pipeline.json');jobs.append(dict(id=folder.name,status=state['status'],error=state.get('error'),quality_approved=False))
        except (ValueError,OSError,KeyError,TypeError) as exc:jobs.append(dict(id=folder.name,status='invalid',error=str(exc),downloads=[],quality_approved=False))
    return dict(jobs=jobs)


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve()
        if not target.is_relative_to(folder):return None
        data=manifest(parts[1])
        return target if any(entry['url']=='/files/'+relative for entry in data['downloads']) else None
    except (ValueError,OSError,KeyError,TypeError):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    run(parser.parse_args().folder)
