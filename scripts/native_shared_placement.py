"""Explicit shared world-placement variants; original clips and targets stay fixed."""
import argparse,copy
from pathlib import Path
import shutil
import numpy as np
from native_scene_contacts import SceneContacts,fields,pose,scalar,vector
from native_scene_geometry import policy_for,METHODS as GEOMETRY_METHODS
from strep import ROOT,read,save,sha256

SCHEMA='strep-native-shared-placement-v1'
METHODS=tuple(dict.fromkeys(('native_shared_placement.py',*GEOMETRY_METHODS)))


def apply(original,translation_world_m,permission):
    fields(permission,('actors','lower_world_m','upper_world_m','maximum_displacement_m'),'shared placement permission')
    names=list(original['actors'])
    if (not names or not isinstance(permission['actors'],list) or permission['actors']!=names
            or any(type(name) is not str for name in names)):raise ValueError('Complete original actor order required for shared placement')
    delta=vector(translation_world_m,3,'world translation');lo=vector(permission['lower_world_m'],3,'world translation lower bound');hi=vector(permission['upper_world_m'],3,'world translation upper bound')
    maximum=scalar(permission['maximum_displacement_m'],0,100,'world translation norm bound')
    if (np.any(lo>hi) or np.any(lo>0) or np.any(hi<0) or np.any(delta<lo) or np.any(delta>hi) or np.linalg.norm(delta)>maximum):raise ValueError('Shared translation exceeds explicit original-relative permission')
    derived=copy.deepcopy(original)
    for name in names:
        p,_=pose(original['actors'][name]['placement']);derived['actors'][name]['placement']['translation_m']=(p+delta).tolist();pose(derived['actors'][name]['placement'])
    return derived,dict(actors=names,translation_world_m=delta.tolist(),translation_norm_m=float(np.linalg.norm(delta)),permission=copy.deepcopy(permission),
        original_root_world_placement_contract_preserved=bool(not np.any(delta)),world_placement_amendment_declared=True,local_animation_edited=False,targets_moved=False,geometry_limits_changed=False,
        original_selected=True,quality_approved=False,release_approved=False,
        scope='New explicitly bounded shared world-placement request. No actor is omitted, no local root/pose curve is edited and no target/object moves. Floor/contact/mesh/engine/quality acceptance remains separate.')


def _pin(entry,base):
    fields(entry,('path','sha256'),'original source binding')
    if (type(entry['path']) is not str or not entry['path'] or type(entry['sha256']) is not str or len(entry['sha256'])!=64
            or any(c not in '0123456789abcdef' for c in entry['sha256'])):raise ValueError('Exact original file hash required')
    p=(base/entry['path']).resolve()
    if sha256(p)!=entry['sha256']:raise ValueError('Original placement input changed')
    return p


def _source(path):
    path=Path(path).resolve();binding=sha256(path);request=read(path)
    fields(request,('schema','source_contacts','source_geometry','label','translation_world_m','permission'),'native shared placement amendment')
    if request['schema']!=SCHEMA or type(request['label']) is not str or not 1<=len(request['label'].strip())<=100:raise ValueError('Named explicit shared placement amendment required')
    cp=_pin(request['source_contacts'],path.parent);gp=_pin(request['source_geometry'],path.parent);original=read(cp);policy=read(gp);scene=SceneContacts(original,cp.parent)
    clock=policy_for(policy,scene,sha256(cp))[0];canonical=copy.deepcopy(original)
    for name,entry in canonical['actors'].items():entry['glb']=str((cp.parent/entry['glb']).resolve())
    derived,meta=apply(canonical,request['translation_world_m'],request['permission'])
    pins={str(path):binding,str(cp):request['source_contacts']['sha256'],str(gp):request['source_geometry']['sha256'],**scene.inputs}
    if any(sha256(p)!=h for p,h in pins.items()):raise ValueError('Placement source changed during validation')
    return request,cp,gp,scene,clock,derived,policy,meta,pins


def verify(folder):
    folder=Path(folder).resolve();receipt=read(folder/'provenance.json')
    if receipt['schema']!='strep-native-shared-placement-receipt-v1':raise ValueError('Shared placement receipt required')
    for p,h in receipt['inputs_sha256'].items():
        if sha256(p)!=h:raise ValueError('Original placement binding changed')
    for name,h in receipt['files_sha256'].items():
        if name not in ('contacts.json','geometry.json','source-contacts.json','source-geometry.json','amendment.json') or sha256(folder/name)!=h:raise ValueError('Complete placement artifact changed')
    if set(receipt['files_sha256'])!={'contacts.json','geometry.json','source-contacts.json','source-geometry.json','amendment.json'}:raise ValueError('Complete placement artifact population required')
    request,cp,gp,scene,clock,expected,policy,meta,pins=_source(Path(receipt['amendment_path']))
    for name,h in receipt['implementation_sha256'].items():
        if name not in METHODS or sha256(ROOT/'scripts'/name)!=h or sha256(folder/'implementation'/name)!=h:raise ValueError('Placement producer changed')
    if set(receipt['implementation_sha256'])!=set(METHODS) or pins!=receipt['inputs_sha256']:raise ValueError('Complete original placement provenance required')
    if (read(folder/'contacts.json')!=expected or read(folder/'amendment.json')!=request or sha256(folder/'source-contacts.json')!=sha256(cp)
            or sha256(folder/'source-geometry.json')!=sha256(gp)):raise ValueError('Placement-only contract was changed')
    policy=copy.deepcopy(policy);policy['contacts_sha256']=sha256(folder/'contacts.json')
    if read(folder/'geometry.json')!=policy:raise ValueError('Original geometry clock, planes or limits changed')
    actual=SceneContacts(read(folder/'contacts.json'),folder);observed=policy_for(policy,actual,sha256(folder/'contacts.json'))[0]
    np.testing.assert_array_equal(clock,observed);scene.check_inputs();actual.check_inputs()
    if any(sha256(p)!=h for p,h in pins.items()):raise ValueError('Placement source changed during replay')
    return dict(meta,source_bindings_exact=True,variant_contract_exact=True,geometry_clock_exact=True,asset_payloads_copied=False)


def stage(amendment_path,output):
    amendment_path=Path(amendment_path).resolve();output=Path(output).resolve()
    request,cp,gp,scene,clock,derived,policy,meta,pins=_source(amendment_path)
    if (output.exists() or any(Path(p).is_relative_to(output) for p in pins)
            or any((ancestor/'result.json').is_file() and output.is_relative_to(ancestor) for p in pins for ancestor in Path(p).parents)):
        raise ValueError('Fresh placement output outside immutable source populations required')
    methods={name:sha256(ROOT/'scripts'/name) for name in METHODS};output.mkdir(parents=True)
    try:
        shutil.copyfile(cp,output/'source-contacts.json');shutil.copyfile(gp,output/'source-geometry.json');save(output/'amendment.json',request)
        save(output/'contacts.json',derived);policy=copy.deepcopy(policy);policy['contacts_sha256']=sha256(output/'contacts.json');save(output/'geometry.json',policy)
        archive=output/'implementation';archive.mkdir()
        for name in methods:shutil.copyfile(ROOT/'scripts'/name,archive/name)
        if any(sha256(p)!=h for p,h in pins.items()) or any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Placement input or implementation changed')
        names=('contacts.json','geometry.json','source-contacts.json','source-geometry.json','amendment.json')
        save(output/'provenance.json',dict(schema='strep-native-shared-placement-receipt-v1',amendment_path=str(amendment_path),inputs_sha256=pins,implementation_sha256=methods,files_sha256={name:sha256(output/name) for name in names},**meta))
        replay=verify(output);save(output/'result.json',dict(status='complete',label=request['label'].strip(),**replay));return read(output/'result.json')
    except Exception as exc:
        save(output/'result.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('amendment',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();print(stage(args.amendment,args.output))
