"""Assemble portable, source-bound mesh scenes and measure authored contacts.

No fitting, asset selection, collision clearance or quality approval occurs.
Call this inside the guarded worker, never in the HTTP request thread.
"""
import copy
from pathlib import Path
import shutil
import zipfile
import numpy as np
from strep import ROOT,save,sha256
from native_scene_contacts import fields,SceneContacts
from native_mesh_prop_scene import MeshPropScene
from studio_native_scene import validate_request
import studio_props


def assemble(payload,output,resolver):
    fields(payload,('schema','draft','props','contacts'),'Studio mesh scene')
    if payload['schema']!='strep-studio-mesh-scene-v1':raise ValueError('Studio mesh scene schema required')
    draft=payload['draft']
    if not isinstance(draft,dict) or draft.get('object_edit') is not None or 'contact_revision' in draft:
        raise ValueError('Save an ordinary scene without a pending object edit or contact revision first')
    spec,geometry,_,sources=validate_request(draft,resolver)
    props=payload['props'];contacts=payload['contacts']
    if not isinstance(props,dict) or not 1<=len(props)<=32:raise ValueError('Choose 1-32 mesh objects')
    if not isinstance(contacts,list) or not 1<=len(contacts)<=64:raise ValueError('Choose 1-64 explicit mesh contacts')
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'reports').resolve()) or output.exists():raise ValueError('Fresh report package directory required')
    output.mkdir(parents=True)
    save(output/'studio-draft.json',payload)
    save(output/'implementation.json',dict(request_sha256=sha256(output/'studio-draft.json'),
        methods_sha256={p.name:sha256(p) for p in sorted((ROOT/'scripts').glob('*.py'))},
        scope='Exact authoring request and Python source hashes; no model inference or weight update.'))
    inputs={};mesh=dict(schema='strep-native-mesh-prop-scene-v1',actor_scene='actor-scene.json',actor_scene_sha256=None,props={},mesh_contacts=[])
    def snapshot(source,relative,expected):
        source=Path(source);target=output/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        if sha256(source)!=expected or sha256(target)!=expected:raise ValueError('Source changed while making the scene snapshot')
        inputs[str(source)]=expected;return relative
    for name,entry in spec['actors'].items():
        entry['glb']=snapshot(sources[name]['path'],f'actors/{name}.glb',sources[name]['sha256'])
    for name,item in props.items():
        SceneContacts.name(name);fields(item,('asset_id','geometry_sha256','keyframes'),'saved mesh object')
        if name in spec['actors'] or name in spec['objects']:raise ValueError('Object and character names must be distinct')
        asset=studio_props.details(item['asset_id'])
        if item['geometry_sha256']!=asset['geometry_sha256']:raise ValueError('Object geometry selection changed')
        relative=snapshot(studio_props.bounded_path(asset['id'],'prop.glb'),f'props/{name}.glb',asset['id'])
        metadata=studio_props.bounded_path(asset['id'],'asset.json')
        snapshot(metadata,f'prop-metadata/{name}.json',sha256(metadata))
        mesh['props'][name]=dict(glb=relative,sha256=asset['id'],geometry_sha256=asset['geometry_sha256'],keyframes=copy.deepcopy(item['keyframes']))
    seen=set()
    for row in contacts:
        fields(row,('id','actor','vertices','reduction','prop','grip_id','mode','interval_s','limits'),'saved mesh contact')
        SceneContacts.name(row['id'])
        if row['id'] in seen:raise ValueError('Distinct mesh contact names required')
        seen.add(row['id'])
        if not isinstance(row['prop'],str) or row['prop'] not in props:raise ValueError('Choose an existing mesh object')
        asset_id=props[row['prop']]['asset_id'];grip_id=studio_props.identifier(row['grip_id'])
        studio_props.grip(asset_id,grip_id)
        relative=snapshot(studio_props.bounded_path(asset_id,f'grips/{grip_id}.json'),f'grips/{row["id"]}.json',grip_id)
        entry={k:copy.deepcopy(v) for k,v in row.items() if k!='grip_id'}
        entry.update(grip=relative,grip_sha256=grip_id);mesh['mesh_contacts'].append(entry)
    save(output/'actor-scene.json',spec);mesh['actor_scene_sha256']=sha256(output/'actor-scene.json');save(output/'mesh-scene.json',mesh)
    policy=dict(schema='strep-native-mesh-prop-geometry-v1',mesh_scene_sha256=sha256(output/'mesh-scene.json'),**{k:copy.deepcopy(geometry[k]) for k in ('clock','limits','planes')})
    save(output/'geometry-policy.json',policy)
    scene=MeshPropScene(output/'mesh-scene.json');report,observations=scene.contact_audit()
    # Validate the complete geometry policy structure without implying that its
    # expensive triangle/containment queries were executed by this contact job.
    from native_scene_geometry import policy_for
    policy_for(geometry,scene._scene,'draft')
    save(output/'contact-report.json',report);np.savez_compressed(output/'contact-observations.npz',**observations)
    scene.check_inputs()
    if any(sha256(path)!=digest for path,digest in inputs.items()):raise ValueError('Scene source changed during measurement')
    files={p.relative_to(output).as_posix():sha256(p) for p in sorted(output.rglob('*')) if p.is_file()}
    result=dict(schema='strep-studio-mesh-scene-result-v1',status='complete',files_sha256=files,
        inputs_sha256=inputs,all_declared_point_contacts_pass=report['all_declared_point_contacts_pass'],
        contacts=report['mesh_contacts'],original_selected=True,motion_fitted=False,
        geometry_evaluated=False,rotation_speed_evaluated=False,engine_export_evaluated=False,
        quality_approved=False,release_approved=False,
        scope='Complete declared point-contact clocks on unchanged supplied clips and authored object paths. Geometry policy, original draft and assets are preserved for subsequent bounded correction and validation. No grasp, anatomy, physics, collision, engine or human approval.')
    save(output/'result.json',result)
    with zipfile.ZipFile(output.parent/'scene-package.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in [*files,'result.json']:archive.write(output/name,name)
    return result
