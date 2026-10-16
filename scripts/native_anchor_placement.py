"""Bounded pivot rotation followed by explicit actor-specific world translation.

This authors a new placement contract. It does not edit animation or certify
contact, support, joint-world bounds, geometry, native playback or human quality.
"""
import copy,shutil
from pathlib import Path
import numpy as np
from native_pivot_placement import apply as pivot_apply,_pin,METHODS as PIVOT_METHODS
from native_scene_contacts import SceneContacts,fields,pose,scalar,vector
from native_scene_geometry import policy_for
from strep import ROOT,read,save,sha256

SCHEMA='strep-native-anchor-placement-v1'
METHODS=('native_anchor_placement.py',*PIVOT_METHODS)


def apply(original,angles_degrees,translations_world_m,permission):
    fields(permission,('pivot','actors'),'anchor placement permission')
    names=list(original['actors'])
    if (not isinstance(translations_world_m,dict) or set(translations_world_m)!=set(names)
            or not isinstance(permission['actors'],dict) or set(permission['actors'])!=set(names)):
        raise ValueError('Explicit translation and bounds for every actor required')
    derived,pivot=pivot_apply(original,angles_degrees,permission['pivot']);changes={}
    for name in names:
        bound=permission['actors'][name]
        fields(bound,('maximum_translation_m','maximum_origin_displacement_m'),'actor anchor permission')
        maximum=scalar(bound['maximum_translation_m'],0,100,'post-pivot translation limit')
        total=scalar(bound['maximum_origin_displacement_m'],0,100,'final actor origin displacement limit')
        shift=vector(translations_world_m[name],3,'post-pivot world translation');distance=float(np.linalg.norm(shift))
        if distance>maximum:raise ValueError('Post-pivot translation exceeds explicit bound')
        start,_=pose(original['actors'][name]['placement']);position,_=pose(derived['actors'][name]['placement'])
        moved=position+shift;final_distance=float(np.linalg.norm(moved-start))
        if final_distance>total:raise ValueError('Final actor origin exceeds explicit bound')
        if distance:derived['actors'][name]['placement']['translation_m']=moved.tolist()
        delta=np.array(pivot['actors'][name]['world_delta']);delta[:3,3]+=shift
        changes[name]=dict(angle_degrees=pivot['actors'][name]['angle_degrees'],translation_world_m=shift.tolist(),
            translation_norm_m=distance,pivot_origin_displacement_m=pivot['actors'][name]['origin_displacement_m'],
            origin_displacement_m=final_distance,world_delta=delta.tolist(),
            original_world_placement_preserved=derived['actors'][name]['placement']==original['actors'][name]['placement'])
    meta={k:v for k,v in pivot.items() if k not in ('actors','permission','scope','original_root_world_placement_contract_preserved')}
    meta.update(actors=changes,permission=copy.deepcopy(permission),translation_applied_after_world_pivot=True,
        original_root_world_placement_contract_preserved=all(v['original_world_placement_preserved'] for v in changes.values()),
        scope='Explicit bounded pivot-plus-translation variant. Actor-origin bounds do not bound every joint. '
            'Local curves, target declarations and geometry thresholds retained; all support/contact/native/engine/quality checks remain separate.')
    return derived,meta


def _source(path):
    path=Path(path).resolve();pin=sha256(path);request=read(path)
    fields(request,('schema','source_contacts','source_geometry','label','angles_degrees','translations_world_m','permission'),'native anchor placement amendment')
    if request['schema']!=SCHEMA or type(request['label']) is not str or not 1<=len(request['label'].strip())<=100:
        raise ValueError('Named explicit anchor placement amendment required')
    cp=_pin(request['source_contacts'],path.parent);gp=_pin(request['source_geometry'],path.parent)
    original=read(cp);policy=read(gp);scene=SceneContacts(original,cp.parent)
    clock=policy_for(policy,scene,sha256(cp))[0];canonical=copy.deepcopy(original)
    for actor in canonical['actors'].values():actor['glb']=str((cp.parent/actor['glb']).resolve())
    derived,meta=apply(canonical,request['angles_degrees'],request['translations_world_m'],request['permission'])
    pins={str(path):pin,str(cp):request['source_contacts']['sha256'],str(gp):request['source_geometry']['sha256'],**scene.inputs}
    if any(sha256(p)!=h for p,h in pins.items()):raise ValueError('Anchor placement source changed')
    return request,cp,gp,scene,clock,derived,policy,meta,pins


def verify(folder):
    folder=Path(folder).resolve();receipt=read(folder/'provenance.json')
    if receipt['schema']!='strep-native-anchor-placement-receipt-v1':raise ValueError('Anchor placement receipt required')
    names={'contacts.json','geometry.json','source-contacts.json','source-geometry.json','amendment.json'}
    if set(receipt['files_sha256'])!=names:raise ValueError('Complete anchor artifacts required')
    for path,h in receipt['inputs_sha256'].items():
        if sha256(path)!=h:raise ValueError('Original anchor binding changed')
    for name,h in receipt['files_sha256'].items():
        if sha256(folder/name)!=h:raise ValueError('Anchor placement artifact changed')
    request,cp,gp,scene,clock,expected,policy,meta,pins=_source(receipt['amendment_path'])
    if any(receipt.get(k)!=v for k,v in meta.items()):raise ValueError('Anchor placement metadata changed')
    if set(receipt['implementation_sha256'])!=set(METHODS) or pins!=receipt['inputs_sha256']:
        raise ValueError('Complete anchor implementation and source provenance required')
    for name,h in receipt['implementation_sha256'].items():
        if sha256(ROOT/'scripts'/name)!=h or sha256(folder/'implementation'/name)!=h:raise ValueError('Anchor helper changed')
    if (read(folder/'contacts.json')!=expected or read(folder/'amendment.json')!=request
            or sha256(folder/'source-contacts.json')!=sha256(cp) or sha256(folder/'source-geometry.json')!=sha256(gp)):
        raise ValueError('Placement-only authored contract changed')
    policy=copy.deepcopy(policy);policy['contacts_sha256']=sha256(folder/'contacts.json')
    if read(folder/'geometry.json')!=policy:raise ValueError('Original geometry clock or thresholds changed')
    actual=SceneContacts(read(folder/'contacts.json'),folder)
    np.testing.assert_array_equal(clock,policy_for(policy,actual,sha256(folder/'contacts.json'))[0])
    scene.check_inputs();actual.check_inputs()
    if any(sha256(p)!=h for p,h in pins.items()):raise ValueError('Anchor inputs changed during replay')
    return dict(meta,source_bindings_exact=True,variant_contract_exact=True,geometry_clock_exact=True,asset_payloads_copied=False)


def stage(amendment_path,output):
    amendment_path=Path(amendment_path).resolve();output=Path(output).resolve()
    request,cp,gp,scene,clock,derived,policy,meta,pins=_source(amendment_path)
    if (output.exists() or any(Path(p).is_relative_to(output) for p in pins)
            or any((a/'result.json').is_file() and output.is_relative_to(a) for p in pins for a in Path(p).parents)):
        raise ValueError('Fresh anchor output outside immutable source populations required')
    methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True)
    try:
        shutil.copyfile(cp,output/'source-contacts.json');shutil.copyfile(gp,output/'source-geometry.json');save(output/'amendment.json',request)
        save(output/'contacts.json',derived);policy=copy.deepcopy(policy);policy['contacts_sha256']=sha256(output/'contacts.json');save(output/'geometry.json',policy)
        archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        if any(sha256(p)!=h for p,h in pins.items()) or any(sha256(ROOT/'scripts'/n)!=sha256(archive/n) or sha256(archive/n)!=h for n,h in methods.items()):
            raise ValueError('Anchor placement inputs or implementation changed')
        names=('contacts.json','geometry.json','source-contacts.json','source-geometry.json','amendment.json')
        save(output/'provenance.json',dict(schema='strep-native-anchor-placement-receipt-v1',amendment_path=str(amendment_path),
            inputs_sha256=pins,implementation_sha256=methods,files_sha256={n:sha256(output/n) for n in names},**meta))
        result=dict(status='complete',label=request['label'].strip(),**verify(output));save(output/'result.json',result);return result
    except Exception as exc:
        save(output/'result.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False,release_approved=False));raise
