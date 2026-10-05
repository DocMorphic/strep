"""Explicit picked vertices -> reviewed complete triangles -> portable region."""
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
import numpy as np
from urllib.parse import urlsplit
from material_patch_bundle import create, verify, source_binding, fields, sha_binding, METHODS as BUNDLE_METHODS, SELECTION_SCHEMA
from rig_material_patch import MaterialSurface, require
from strep import ROOT, read, save, sha256, now

SCHEMA='strep-studio-material-region-v1'
METHODS=tuple(dict.fromkeys(BUNDLE_METHODS+('studio_material_region.py',)))
PREFIXES=('/files/rig-jobs/','/files/character-assets/','/files/native-correction-previews/',
          '/files/native-support-jobs/','/files/native-scene-jobs/','/files/native-scene-fit-jobs/')
NAME=re.compile(r'[A-Za-z0-9_-]{1,64}')


def folder_for(name, namespace='material-region-previews'):
    require(isinstance(name,str) and NAME.fullmatch(name), 'Safe region ID required')
    require(namespace in ('material-region-previews','material-region-bundles'), 'Region namespace required')
    root=(ROOT/'reports'/namespace).resolve(); result=(root/name).resolve()
    require(result.parent==root and result.is_relative_to((ROOT/'reports').resolve()), 'Local region folder required')
    return result


def actor_path(actor,resolver):
    fields(actor,('glb','sha256'),'selected character');sha_binding(actor['sha256'],'character binding')
    url=actor['glb'];require(isinstance(url,str),'Served character URL required');p=urlsplit(url)
    require(not p.scheme and not p.netloc and not p.query and not p.fragment and p.path==url and url.startswith(PREFIXES),
            'Choose a served character clip')
    path=resolver(url);require(path is not None,'Selected character is not served');path=Path(path).resolve()
    require(path.is_relative_to((ROOT/'reports').resolve()) and path.suffix.lower()=='.glb' and path.is_file()
            and 0<path.stat().st_size<=128*1024**2,'Bounded existing workspace character required')
    require(sha256(path)==actor['sha256'],'Selected character changed');return path


def syntax(payload):
    fields(payload,('schema','actor','profile_json','profile_sha256','patch_id','role','vertices','selector'),'picked region')
    require(payload['schema']==SCHEMA,'Picked region schema required')
    require(isinstance(payload['profile_json'],str) and 0<len(payload['profile_json'].encode('utf8'))<=128*1024,
            'Supply a UTF-8 rig profile up to 128 KiB')
    require(isinstance(json.loads(payload['profile_json']),dict),'Rig profile JSON object required')
    sha_binding(payload['profile_sha256'],'rig profile binding')
    require(hashlib.sha256(payload['profile_json'].encode('utf8')).hexdigest()==payload['profile_sha256'],
            'Exact submitted UTF-8 profile bytes required')
    require(isinstance(payload['patch_id'],str) and NAME.fullmatch(payload['patch_id']),'Explicit safe patch ID required')
    require(isinstance(payload['role'],str) and 1<=len(payload['role'])<=64,'Explicit mapped role required')
    refs=payload['vertices']
    require(isinstance(refs,list) and 3<=len(refs)<=256 and all(isinstance(r,list) and len(r)==3
            and all(type(i) is int and i>=0 for i in r) for r in refs)
            and len({tuple(r) for r in refs})==len(refs),'Choose 3-256 distinct original mesh vertices')
    fields(payload['selector'],('include_children','minimum_weight','minimum_twice_area_m2','maximum_faces','maximum_vertices'),'explicit selector')


def selected_patch(material,payload):
    lookup={tuple(r):i for i,r in enumerate(material.skin.vertex_references.tolist())}
    require(all(tuple(r) in lookup for r in payload['vertices']),'Picked mesh vertex does not exist')
    selected={lookup[tuple(r)] for r in payload['vertices']}
    enclosed=np.all(np.isin(material.faces,list(selected)),axis=1);ids=np.flatnonzero(enclosed)
    require(0<len(ids)<=512,'Choose complete triangles within the 512-face budget')
    require(set(np.unique(material.faces[ids]).tolist())==selected,
            'Every picked vertex must belong to an enclosed triangle; no unused vertices are discarded')
    faces=material.face_references[ids].tolist()
    return material.patch(payload['role'],faces,**payload['selector'])


def preview(payload,resolver,name):
    """Caller owns the production lock. Failure snapshots are retained."""
    syntax(payload);source=actor_path(payload['actor'],resolver);folder=folder_for(name)
    require(not folder.exists(),'Fresh region preview required')
    methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
    folder.mkdir(parents=True);input_dir=folder/'input';input_dir.mkdir()
    try:
        save(folder/'pipeline.json',dict(status='processing'))
        save(folder/'request.json',payload)
        shutil.copyfile(source,input_dir/'character.glb')
        (input_dir/'rig-profile.json').write_bytes(payload['profile_json'].encode('utf8'))
        require(sha256(source)==sha256(input_dir/'character.glb')==payload['actor']['sha256'],'Selected character changed during snapshot')
        binding=source_binding(input_dir/'character.glb',input_dir/'rig-profile.json')
        material=MaterialSurface(input_dir/'character.glb',input_dir/'rig-profile.json',
                                 character_sha256=binding['character_sha256'],profile_sha256=binding['profile_sha256'])
        patch=selected_patch(material,payload);save(folder/'patch.json',patch)
        selection=dict(schema=SELECTION_SCHEMA,source=binding,patches=[dict(id=payload['patch_id'],role=payload['role'],
                           face_references=patch['face_references'],selector=copy.deepcopy(payload['selector']))])
        save(folder/'selection.json',selection);material.check_inputs()
        require(read(folder/'request.json')==payload and sha256(source)==payload['actor']['sha256']
                and all(sha256(ROOT/'scripts'/n)==h for n,h in methods.items()),
                'Source or region method changed during preview')
        result=dict(schema=SCHEMA,status='complete',id=name,at=now(),request_sha256=sha256(folder/'request.json'),
                    input_sha256={n:sha256(input_dir/n) for n in ('character.glb','rig-profile.json')},
                    patch_sha256=sha256(folder/'patch.json'),selection_sha256=sha256(folder/'selection.json'),
                    implementation_sha256=methods,all_picked_vertices_accounted=True,anatomical_review_pending=True,
                    animation_edited=False,motion_contacts_measured=False,engine_executed=False,human_reviewed=False,
                    quality_approved=False,training_admitted=False,release_approved=False)
        save(folder/'result.json',result);save(folder/'pipeline.json',dict(status='complete'))
        return dict(result,result_sha256=sha256(folder/'result.json'),request=copy.deepcopy(payload),patch=patch)
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),quality_approved=False,release_approved=False));raise


def checked_preview(name,bound,resolver):
    folder=folder_for(name);sha_binding(bound,'preview binding')
    require(sha256(folder/'result.json')==bound,'Region preview differs from caller binding')
    result=read(folder/'result.json');request=read(folder/'request.json');syntax(request)
    fields(result,('schema','status','id','at','request_sha256','input_sha256','patch_sha256','selection_sha256',
                   'implementation_sha256','all_picked_vertices_accounted','anatomical_review_pending',
                   'animation_edited','motion_contacts_measured','engine_executed','human_reviewed',
                   'quality_approved','training_admitted','release_approved'),'region preview result')
    require(result['schema']==SCHEMA and result['status']=='complete' and result['id']==name
            and read(folder/'pipeline.json')=={'status':'complete'},'Complete region preview required')
    require(result['all_picked_vertices_accounted'] is True and result['anatomical_review_pending'] is True
            and all(result[k] is False for k in ('animation_edited','motion_contacts_measured','engine_executed','human_reviewed',
                                               'quality_approved','training_admitted','release_approved')), 'Unapproved region preview required')
    require(set(result['implementation_sha256'])==set(METHODS)
            and all(sha256(ROOT/'scripts'/n)==h for n,h in result['implementation_sha256'].items()), 'Region methods changed')
    files={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    require(files=={'input/character.glb','input/rig-profile.json','request.json','result.json','pipeline.json','patch.json','selection.json'},
            'Complete exact region preview file population required')
    require(all(not p.is_symlink() and p.resolve().is_relative_to(folder) for p in folder.rglob('*')),'Region preview must stay local')
    require(result['request_sha256']==sha256(folder/'request.json') and result['patch_sha256']==sha256(folder/'patch.json')
            and result['selection_sha256']==sha256(folder/'selection.json')
            and set(result['input_sha256'])=={'character.glb','rig-profile.json'}
            and all(sha256(folder/'input'/n)==h for n,h in result['input_sha256'].items()),'Region preview input changed')
    require((folder/'input/rig-profile.json').read_bytes()==request['profile_json'].encode('utf8')
            and result['input_sha256']['character.glb']==request['actor']['sha256'],'Exact declared profile and character required')
    actor_path(request['actor'],resolver)
    material=MaterialSurface(folder/'input/character.glb',folder/'input/rig-profile.json',
            character_sha256=result['input_sha256']['character.glb'],profile_sha256=result['input_sha256']['rig-profile.json'])
    patch=selected_patch(material,request);require(read(folder/'patch.json')==patch,'Complete region replay differs')
    selection=dict(schema=SELECTION_SCHEMA,source=dict(material.source),patches=[dict(id=request['patch_id'],role=request['role'],
                    face_references=patch['face_references'],selector=copy.deepcopy(request['selector']))])
    require(read(folder/'selection.json')==selection,'Reviewed triangle selection differs')
    material.check_inputs();require(sha256(folder/'result.json')==bound
            and result['request_sha256']==sha256(folder/'request.json')
            and result['patch_sha256']==sha256(folder/'patch.json')
            and result['selection_sha256']==sha256(folder/'selection.json'),'Region preview changed during replay')
    return folder,result,request,patch


def save_region(payload,resolver,name):
    fields(payload,('schema','id','preview_sha256'),'reviewed region save')
    require(payload['schema']==SCHEMA,'Reviewed region schema required')
    folder,result,request,patch=checked_preview(payload['id'],payload['preview_sha256'],resolver)
    output=folder_for(name,'material-region-bundles');require(not output.exists(),'Fresh saved region required')
    created=create(folder/'input/character.glb',folder/'input/rig-profile.json',folder/'selection.json',output)
    bound=sha256(output/'result.json');require(verify(output,expected_result_sha256=bound)==created,'Saved region bundle replay differs')
    checked_preview(payload['id'],payload['preview_sha256'],resolver)
    receipt=output.with_suffix('.authoring.json');require(not receipt.exists(),'Fresh region authoring receipt required')
    value=dict(schema=SCHEMA,status='complete',id=name,preview_id=payload['id'],preview_sha256=payload['preview_sha256'],
               bundle=f'material-region-bundles/{name}',result_sha256=bound,patch_id=request['patch_id'],
               character_sha256=request['actor']['sha256'],profile_sha256=result['input_sha256']['rig-profile.json'],
               faces=len(patch['face_references']),vertices=len(patch['vertices']),explicit_triangle_selection=True,
               original_selected=True,anatomical_review_pending=True,animation_edited=False,motion_contacts_measured=False,engine_executed=False,
               human_reviewed=False,quality_approved=False,training_admitted=False,release_approved=False)
    save(receipt,value);return value
