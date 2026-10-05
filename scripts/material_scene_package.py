"""Portable explicit material-contact authoring and native scene execution.

Preparation transports paths and copies complete inputs; it edits no animation.
Engine execution is separate, diagnostic, and preserves every failed condition.
"""
import argparse
import copy
from pathlib import Path
import shutil
from material_patch_bundle import verify as patch_verify, files, fields, sha_binding, MAXIMUM_ASSET_BYTES
from material_patch_revision import revise, METHODS as REVISION_METHODS, SCHEMA as SELECTION_SCHEMA
from rig_material_identity import digest
from rig_material_patch import require
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for
from native_object_hold_fit import request_for
from native_scene_authoring_job import plan,run as engine_run,METHODS as ENGINE_METHODS
from action_worker_lock import worker_busy
from strep import ROOT,read,save,sha256,now

METHODS = tuple(dict.fromkeys(REVISION_METHODS+ENGINE_METHODS+(
    'verify_native_actor_scene_engine.py','material_scene_package.py')))
SCHEMA = 'strep-material-scene-package-v1'
DEFAULT_PAYLOAD_BYTES = 512*1024**2
MAXIMUM_PAYLOAD_BYTES = 8*1024**3
DERIVED = ('baseline.json','selection.json','draft.json','material-proof.json','contacts.json','geometry-policy.json')
SCOPE = ('Portable explicit selected-skin contact intent with exact original draft/specification and actor bytes. '
         'Only actor/bundle paths and dependent JSON bindings are transported. No anatomical/contact-target, '
         'motion, engine, rights/training, human-quality or release approval from preparation.')


def budget(value):
    require(type(value) is int and 1 <= value <= MAXIMUM_PAYLOAD_BYTES,'Explicit bounded integer payload budget required')


def bounded(path,maximum):
    require(path.is_file() and 0 < path.stat().st_size <= maximum,'Bounded regular source file required')


def references(spec):
    fields(spec,('schema','baseline_sha256','edits'),'source material revision')
    sha_binding(spec['baseline_sha256'],'source original draft binding')
    require(spec['schema']==SELECTION_SCHEMA and isinstance(spec['edits'],list)
            and 1<=len(spec['edits'])<=64,'Explicit bounded material revision required')
    result=[]
    for edit in spec['edits']:
        fields(edit,('id','source','partner'),'material contact edit')
        for name in ('source','partner'):
            entry=edit[name]
            if entry is None:continue
            fields(entry,('bundle','result_sha256','patch_id','vertex_indices','reduction'),'material patch reference')
            require(isinstance(entry['bundle'],str) and bool(entry['bundle']),'Explicit material bundle path required')
            sha_binding(entry['result_sha256'],'source material result binding')
            key=entry['bundle'],entry['result_sha256']
            if key not in result:result.append(key)
    return result


def transport(original,selection,actors,materials):
    """No motion or contact inference; transport only declared file references."""
    baseline=copy.deepcopy(original);spec=copy.deepcopy(selection)
    expected=[]
    for i,(name,actor) in enumerate(original['scene']['actors'].items()):
        expected.append(dict(actor=name,source_glb=actor['glb'],snapshot=f'input/actors/actor-{i}.glb',sha256=actor['sha256']))
    require(digest(actors)==digest(expected),'Complete unchanged actor byte/selection population required')
    pairs=references(selection)
    require(len(materials)==len(pairs),'Complete declared material bundle population required')
    mapping={}
    for i,(item,(path,h)) in enumerate(zip(materials,pairs)):
        fields(item,('source_bundle','result_sha256','snapshot','files_sha256'),'material package source')
        require(item['source_bundle']==path and item['result_sha256']==h
                and item['snapshot']==f'input/materials/bundle-{i}','Exact declared material order/reference required')
        mapping[(path,h)]=item['snapshot']
    for item in actors:baseline['scene']['actors'][item['actor']]['glb']=item['snapshot']
    for edit in spec['edits']:
        for side in ('source','partner'):
            entry=edit[side]
            if entry is not None:entry['bundle']=mapping[(entry['bundle'],entry['result_sha256'])]
    return baseline,spec


def portable_proof(proof,folder):
    proof=copy.deepcopy(proof)
    for item in proof['material_bindings']:
        item['bundle']=Path(item['bundle']).resolve().relative_to(folder).as_posix()
    proof['original_actor_sha256']={Path(p).resolve().relative_to(folder).as_posix():h
                                   for p,h in proof['original_actor_sha256'].items()}
    return proof


def derive(folder,request):
    original=read(folder/'input/source-draft.json');selection=read(folder/'input/source-selection.json')
    require(selection['baseline_sha256']==sha256(folder/'input/source-draft.json'),'Original material specification binds another draft')
    baseline,spec=transport(original,selection,request['actors'],request['materials'])
    require(digest(read(folder/'baseline.json'))==digest(baseline),'Portable baseline changes protected original authoring fields')
    spec['baseline_sha256']=sha256(folder/'baseline.json')
    require(digest(read(folder/'selection.json'))==digest(spec),'Portable selection changes explicit material intent')
    revised,proof=revise(baseline,spec,specification_base=folder,scene_base=folder,
                         baseline_sha256=sha256(folder/'baseline.json'))
    scene=SceneContacts(revised['scene'],folder)
    fields(revised['geometry'],('clock','limits','planes'),'complete declared geometry')
    geometry=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(folder/'contacts.json'),
                  **copy.deepcopy(revised['geometry']))
    policy_for(geometry,scene,geometry['contacts_sha256'])
    edit=None
    if revised['object_edit'] is not None:
        require(bool(scene.objects),'Object editing requires a declared object')
        edit=dict(contacts_sha256=geometry['contacts_sha256'],**copy.deepcopy(revised['object_edit']))
        request_for(scene,edit,geometry['contacts_sha256'])
    scene.check_inputs()
    return revised,portable_proof(proof,folder),geometry,edit


def prepare(baseline_path,specification_path,output,*,maximum_payload_bytes=DEFAULT_PAYLOAD_BYTES):
    baseline_path,specification_path,output=[Path(p).resolve() for p in (baseline_path,specification_path,output)]
    budget(maximum_payload_bytes);require(not output.exists(),'Fresh material scene package required')
    for p in (baseline_path,specification_path):bounded(p,8*1024**2)
    original,selection=read(baseline_path),read(specification_path)
    fields(original,('schema','scene','geometry','object_edit'),'original local native draft')
    fields(original['scene'],('schema','duration_s','actors','objects','contacts'),'complete scene')
    require(isinstance(original['scene']['actors'],dict) and 1<=len(original['scene']['actors'])<=8,'Explicit bounded actor population required')
    inputs={str(p):sha256(p) for p in (baseline_path,specification_path)}
    actors=[];actor_paths=[]
    for i,(name,entry) in enumerate(original['scene']['actors'].items()):
        require(isinstance(entry['glb'],str),'Explicit local actor file required')
        p=(baseline_path.parent/entry['glb']).resolve();bounded(p,MAXIMUM_ASSET_BYTES)
        require(sha256(p)==entry['sha256'],'Original actor bytes changed');inputs[str(p)]=entry['sha256'];actor_paths.append(p)
        actors.append(dict(actor=name,source_glb=entry['glb'],snapshot=f'input/actors/actor-{i}.glb',sha256=entry['sha256']))
    # Complete existing revision validation happens before publishing any output.
    revised,_=revise(original,selection,specification_base=specification_path.parent,scene_base=baseline_path.parent,
                     baseline_sha256=inputs[str(baseline_path)])
    scene=SceneContacts(revised['scene'],baseline_path.parent)
    fields(revised['geometry'],('clock','limits','planes'),'complete declared geometry')
    policy_for(dict(schema='strep-native-scene-geometry-v1',contacts_sha256='0'*64,
                    **copy.deepcopy(revised['geometry'])),scene,'0'*64)
    if revised['object_edit'] is not None:
        require(bool(scene.objects),'Object editing requires a declared object')
        request_for(scene,dict(contacts_sha256='0'*64,**copy.deepcopy(revised['object_edit'])),'0'*64)
    scene.check_inputs()
    methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};materials=[];material_paths=[]
    for i,(path,h) in enumerate(references(selection)):
        p=(specification_path.parent/path).resolve()
        patch_verify(p,expected_result_sha256=h)
        require(read(p/'pipeline.json')['status']=='complete','Completed original patch bundle required')
        require(not output.is_relative_to(p),'Package cannot be nested in an original material bundle')
        material_paths.append(p);materials.append(dict(source_bundle=path,result_sha256=h,
            snapshot=f'input/materials/bundle-{i}',files_sha256=files(p)))
    estimate=sum(p.stat().st_size for p in actor_paths)+(baseline_path.stat().st_size+specification_path.stat().st_size)
    estimate+=sum((p/n).stat().st_size for p,row in zip(material_paths,materials) for n in row['files_sha256'])
    estimate+=sum((ROOT/'scripts'/n).stat().st_size for n in METHODS)
    require(estimate<=maximum_payload_bytes,'Complete material package exceeds declared payload budget; no truncation')
    output.mkdir(parents=True)
    try:
        save(output/'pipeline.json',dict(status='processing',stage='portable-material-inputs'))
        (output/'input').mkdir();shutil.copyfile(baseline_path,output/'input/source-draft.json');shutil.copyfile(specification_path,output/'input/source-selection.json')
        for p,item in zip(actor_paths,actors):
            dest=output/item['snapshot'];dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
            require(sha256(dest)==item['sha256'],'Copied actor bytes changed')
        for p,item in zip(material_paths,materials):
            shutil.copytree(p,output/item['snapshot'])
            require(files(output/item['snapshot'])==item['files_sha256'],'Complete material bundle changed during copying')
        for n in METHODS:
            dest=output/'implementation'/n;dest.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'scripts'/n,dest)
        baseline,spec=transport(original,selection,actors,materials);save(output/'baseline.json',baseline)
        spec['baseline_sha256']=sha256(output/'baseline.json');save(output/'selection.json',spec)
        revised,proof=revise(baseline,spec,specification_base=output,scene_base=output,baseline_sha256=sha256(output/'baseline.json'))
        save(output/'draft.json',revised);save(output/'material-proof.json',portable_proof(proof,output));save(output/'contacts.json',revised['scene'])
        request=dict(schema=SCHEMA,at=now(),maximum_payload_bytes=maximum_payload_bytes,actors=actors,materials=materials,
            implementation_sha256=methods,payload_sha256={})
        _,_,geometry,edit=derive(output,request);save(output/'geometry-policy.json',geometry)
        if edit is not None:save(output/'object-edit.json',edit)
        require(all(sha256(p)==h for p,h in inputs.items()),'Original authoring input changed during packaging')
        for p,item in zip(material_paths,materials):require(files(p)==item['files_sha256'],'Original material bundle changed')
        require(all(sha256(ROOT/'scripts'/n)==h for n,h in methods.items()),'Material package method changed')
        request['payload_sha256']={n:h for n,h in files(output).items() if n!='pipeline.json'}
        require(sum((output/n).stat().st_size for n in request['payload_sha256'])<=maximum_payload_bytes,'Complete prepared payload exceeds declared budget')
        save(output/'request.json',request)
        save(output/'result.json',dict(schema=SCHEMA,status='complete',request_sha256=sha256(output/'request.json'),
            actors=len(actors),material_bundles=len(materials),revised_contacts=len(spec['edits']),
            explicit_vertex_correspondence=True,source_actor_bytes_unchanged=True,only_references_transported=True,
            anatomical_review_pending=True,animation_edited=False,motion_contacts_measured=False,engine_executed=False,
            quality_approved=False,training_admitted=False,release_approved=False,scope=SCOPE))
        save(output/'pipeline.json',dict(status='complete'));return verify(output)
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


def verify(folder,*,expected_result_sha256=None):
    folder=Path(folder).resolve()
    if expected_result_sha256 is not None:
        sha_binding(expected_result_sha256,'material scene result binding')
        require(sha256(folder/'result.json')==expected_result_sha256,'Material scene result differs from caller binding')
    snapshot=files(folder);request,result=read(folder/'request.json'),read(folder/'result.json')
    fields(request,('schema','at','maximum_payload_bytes','actors','materials','implementation_sha256','payload_sha256'),'material scene package request')
    require(request['schema']==SCHEMA and read(folder/'pipeline.json')['status']=='complete','Complete material scene package required')
    budget(request['maximum_payload_bytes']);require(set(request['implementation_sha256'])==set(METHODS),'Complete material scene methods required')
    for n,h in request['implementation_sha256'].items():
        require(sha256(ROOT/'scripts'/n)==sha256(folder/'implementation'/n)==h,'Archived/current material scene method changed')
    transport(read(folder/'input/source-draft.json'),read(folder/'input/source-selection.json'),request['actors'],request['materials'])
    expected=set(DERIVED)|{'input/source-draft.json','input/source-selection.json'}|{'implementation/'+n for n in METHODS}
    for row in request['actors']:
        bounded(folder/row['snapshot'],MAXIMUM_ASSET_BYTES)
        expected.add(row['snapshot']);require(sha256(folder/row['snapshot'])==row['sha256'],'Complete portable actor bytes changed')
    for row in request['materials']:
        path=folder/row['snapshot'];require(files(path)==row['files_sha256'],'Complete portable material parent population changed')
        patch_verify(path,expected_result_sha256=row['result_sha256'])
        expected.update(row['snapshot']+'/'+n for n in row['files_sha256'])
    revised,proof,geometry,edit=derive(folder,request)
    if edit is not None:expected.add('object-edit.json');require(digest(read(folder/'object-edit.json'))==digest(edit),'Explicit object edit changed')
    for name,value in (('draft.json',revised),('contacts.json',revised['scene']),('material-proof.json',proof),('geometry-policy.json',geometry)):
        require(digest(read(folder/name))==digest(value),'Replayed complete material scene differs: '+name)
    require(set(request['payload_sha256'])==expected,'Complete prepared material payload population required')
    require(sum((folder/n).stat().st_size for n in expected)<=request['maximum_payload_bytes'],'Material payload exceeds declared budget')
    for n,h in request['payload_sha256'].items():require(sha256(folder/n)==h,'Material package payload changed')
    rebuilt=dict(schema=SCHEMA,status='complete',request_sha256=sha256(folder/'request.json'),actors=len(request['actors']),
        material_bundles=len(request['materials']),revised_contacts=len(read(folder/'selection.json')['edits']),
        explicit_vertex_correspondence=True,source_actor_bytes_unchanged=True,only_references_transported=True,
        anatomical_review_pending=True,animation_edited=False,motion_contacts_measured=False,engine_executed=False,
        quality_approved=False,training_admitted=False,release_approved=False,scope=SCOPE)
    require(digest(result)==digest(rebuilt),'Material package result cannot change counts or grant approval')
    require(set(snapshot)==expected|{'pipeline.json','request.json','result.json'} and files(folder)==snapshot,'Immutable complete material package required')
    require(all(sha256(ROOT/'scripts'/n)==h for n,h in request['implementation_sha256'].items()),
            'Current material scene method changed during replay')
    return result


def run(package,output,engine):
    package,output,engine=[Path(p).resolve() for p in (package,output,engine)]
    require(not worker_busy(),'Another production worker owns the lock')
    require(not output.exists() and not output.is_relative_to(package),'Fresh separate material scene execution required')
    verified=verify(package);before=files(package);output.mkdir(parents=True)
    try:
        save(output/'pipeline.json',dict(status='processing',stage='material-package-snapshot'))
        shutil.copytree(package,output/'authoring');require(files(output/'authoring')==before,'Authoring package changed during copying')
        require(verify(output/'authoring')==verified,'Copied material package replay differs')
        edit=output/'authoring/object-edit.json';edit=edit if edit.exists() else None
        plan(output/'authoring/contacts.json',output/'authoring/geometry-policy.json',engine,output/'recipe.json',edit)
        result=engine_run(output/'recipe.json',output/'engine-job')
        require(result['status']=='complete' and result['original_selected'] and not result['quality_approved']
                and not result['release_approved'],'Completed diagnostic material scene job required')
        require(files(package)==before and files(output/'authoring')==before,'Material authoring lineage changed during execution')
        require(verify(package)==verified and verify(output/'authoring')==verified,'Material execution methods or lineage changed')
        value=dict(schema='strep-material-scene-execution-v1',status='complete',at=now(),
            authoring_result_sha256=sha256(output/'authoring/result.json'),engine_result_sha256=sha256(output/'engine-job/result.json'),
            sampled_conditions_pass=result['sampled_conditions_pass'],original_selected=True,studio_selection_changed=False,
            material_lineage_preserved=True,anatomical_review_pending=True,quality_approved=False,training_admitted=False,release_approved=False)
        save(output/'result.json',value);save(output/'pipeline.json',dict(status='complete'));return value
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    for n in ('baseline','specification','output'):p.add_argument(n,type=Path)
    p.add_argument('--maximum-payload-bytes',type=int,default=DEFAULT_PAYLOAD_BYTES)
    p=sub.add_parser('verify');p.add_argument('folder',type=Path);p.add_argument('--expected-result-sha256')
    p=sub.add_parser('run')
    for n in ('package','output','engine'):p.add_argument(n,type=Path)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.baseline,args.specification,args.output,maximum_payload_bytes=args.maximum_payload_bytes)
    elif args.command=='verify':verify(args.folder,expected_result_sha256=args.expected_result_sha256)
    else:run(args.package,args.output,args.engine)
