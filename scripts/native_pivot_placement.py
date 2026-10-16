"""Explicit bounded per-actor rotations around a declared world-space pivot.

Defines a new placement request. Source clips, contacts, objects and geometry
limits are preserved; actor-attached targets follow the new placements. No
collision, joint-world displacement, engine or animation-quality pass is implied.
"""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from native_scene_contacts import SceneContacts,fields,pose,scalar,vector
from native_scene_geometry import policy_for,METHODS as GEOMETRY_METHODS
from strep import ROOT,read,save,sha256

SCHEMA='strep-native-pivot-placement-v1'
METHODS=tuple(dict.fromkeys(('native_pivot_placement.py',*GEOMETRY_METHODS)))


def apply(original,angles_degrees,permission):
    fields(permission,('axis_world','pivot_world_m','actors'),'pivot placement permission')
    names=list(original['actors'])
    if (not 1<=len(names)<=8 or not isinstance(angles_degrees,dict) or set(angles_degrees)!=set(names)
            or not isinstance(permission['actors'],dict) or set(permission['actors'])!=set(names)):
        raise ValueError('Explicit angle and permission for every original actor required')
    axis=vector(permission['axis_world'],3,'world pivot axis');norm=float(np.linalg.norm(axis))
    if abs(norm-1)>1e-8:raise ValueError('Unit world pivot axis required')
    axis=axis/norm;pivot=vector(permission['pivot_world_m'],3,'world pivot')
    derived=copy.deepcopy(original);changes={}
    for name in names:
        bound=permission['actors'][name]
        fields(bound,('maximum_degrees','maximum_origin_displacement_m'),'actor pivot permission')
        maximum=scalar(bound['maximum_degrees'],0,180,'pivot rotation limit')
        displacement=scalar(bound['maximum_origin_displacement_m'],0,100,'actor origin displacement limit')
        angle=scalar(angles_degrees[name],-maximum,maximum,'pivot rotation')
        position,orientation=pose(original['actors'][name]['placement'])
        rotation=Rotation.from_rotvec(axis*np.deg2rad(angle)).as_matrix()
        moved=pivot+rotation@(position-pivot) if angle else position.copy()
        distance=float(np.linalg.norm(moved-position))
        if distance>displacement:raise ValueError('Pivot rotation exceeds explicit actor-origin displacement bound')
        transform=np.eye(4);transform[:3,:3]=rotation;transform[:3,3]=pivot-rotation@pivot
        if angle:
            derived['actors'][name]['placement']=dict(translation_m=moved.tolist(),
                rotation_xyzw=Rotation.from_matrix(rotation@orientation).as_quat().tolist())
            pose(derived['actors'][name]['placement'])
        changes[name]=dict(angle_degrees=angle,origin_displacement_m=distance,
            world_delta=transform.tolist(),original_world_placement_preserved=angle==0)
    return derived,dict(axis_world_used=axis.tolist(),pivot_world_m=pivot.tolist(),actors=changes,
        permission=copy.deepcopy(permission),world_placement_amendment_declared=True,
        original_root_world_placement_contract_preserved=all(angles_degrees[n]==0 for n in names),
        local_animation_edited=False,target_declarations_changed=False,object_poses_changed=False,
        actor_attached_targets_follow_placements=True,joint_world_displacement_checked=False,
        geometry_limits_changed=False,original_selected=True,quality_approved=False,release_approved=False,
        scope='Explicit per-actor rigid placement variant only. Actor origin bounds do not bound every joint. '
            'Contact, support, native world bounds, geometry, engine and human quality require fresh checks.')


def _pin(entry,base):
    fields(entry,('path','sha256'),'original source binding')
    if (type(entry['path']) is not str or not entry['path'] or type(entry['sha256']) is not str or len(entry['sha256'])!=64
            or any(c not in '0123456789abcdef' for c in entry['sha256'])):raise ValueError('Exact original file hash required')
    path=(base/entry['path']).resolve()
    if sha256(path)!=entry['sha256']:raise ValueError('Original pivot placement input changed')
    return path


def _source(path):
    path=Path(path).resolve();binding=sha256(path);request=read(path)
    fields(request,('schema','source_contacts','source_geometry','label','angles_degrees','permission'),'native pivot placement amendment')
    if request['schema']!=SCHEMA or type(request['label']) is not str or not 1<=len(request['label'].strip())<=100:
        raise ValueError('Named explicit pivot placement amendment required')
    cp=_pin(request['source_contacts'],path.parent);gp=_pin(request['source_geometry'],path.parent)
    original=read(cp);policy=read(gp);scene=SceneContacts(original,cp.parent)
    clock=policy_for(policy,scene,sha256(cp))[0];canonical=copy.deepcopy(original)
    for actor in canonical['actors'].values():actor['glb']=str((cp.parent/actor['glb']).resolve())
    derived,meta=apply(canonical,request['angles_degrees'],request['permission'])
    pins={str(path):binding,str(cp):request['source_contacts']['sha256'],str(gp):request['source_geometry']['sha256'],**scene.inputs}
    if any(sha256(p)!=h for p,h in pins.items()):raise ValueError('Pivot placement source changed during validation')
    return request,cp,gp,scene,clock,derived,policy,meta,pins


def verify(folder):
    folder=Path(folder).resolve();receipt=read(folder/'provenance.json')
    if receipt['schema']!='strep-native-pivot-placement-receipt-v1':raise ValueError('Pivot placement receipt required')
    for path,h in receipt['inputs_sha256'].items():
        if sha256(path)!=h:raise ValueError('Original pivot placement binding changed')
    names={'contacts.json','geometry.json','source-contacts.json','source-geometry.json','amendment.json'}
    if set(receipt['files_sha256'])!=names:raise ValueError('Complete pivot placement artifacts required')
    for name,h in receipt['files_sha256'].items():
        if sha256(folder/name)!=h:raise ValueError('Pivot placement artifact changed')
    request,cp,gp,scene,clock,expected,policy,meta,pins=_source(receipt['amendment_path'])
    if any(receipt.get(key)!=value for key,value in meta.items()):raise ValueError('Pivot placement amendment metadata changed')
    if set(receipt['implementation_sha256'])!=set(METHODS) or pins!=receipt['inputs_sha256']:
        raise ValueError('Complete original pivot placement provenance required')
    for name,h in receipt['implementation_sha256'].items():
        if sha256(ROOT/'scripts'/name)!=h or sha256(folder/'implementation'/name)!=h:
            raise ValueError('Pivot placement helper changed')
    if (read(folder/'contacts.json')!=expected or read(folder/'amendment.json')!=request
            or sha256(folder/'source-contacts.json')!=sha256(cp) or sha256(folder/'source-geometry.json')!=sha256(gp)):
        raise ValueError('Pivot placement-only contract was changed')
    policy=copy.deepcopy(policy);policy['contacts_sha256']=sha256(folder/'contacts.json')
    if read(folder/'geometry.json')!=policy:raise ValueError('Original geometry clock, planes or limits changed')
    actual=SceneContacts(read(folder/'contacts.json'),folder)
    np.testing.assert_array_equal(clock,policy_for(policy,actual,sha256(folder/'contacts.json'))[0])
    scene.check_inputs();actual.check_inputs()
    if any(sha256(path)!=h for path,h in pins.items()):raise ValueError('Pivot placement source changed during replay')
    return dict(meta,source_bindings_exact=True,variant_contract_exact=True,geometry_clock_exact=True,
        asset_payloads_copied=False)


def stage(amendment_path,output):
    amendment_path=Path(amendment_path).resolve();output=Path(output).resolve()
    request,cp,gp,scene,clock,derived,policy,meta,pins=_source(amendment_path)
    if (output.exists() or any(Path(p).is_relative_to(output) for p in pins)
            or any((ancestor/'result.json').is_file() and output.is_relative_to(ancestor) for p in pins for ancestor in Path(p).parents)):
        raise ValueError('Fresh pivot placement output outside immutable source populations required')
    methods={name:sha256(ROOT/'scripts'/name) for name in METHODS};output.mkdir(parents=True)
    try:
        shutil.copyfile(cp,output/'source-contacts.json');shutil.copyfile(gp,output/'source-geometry.json');save(output/'amendment.json',request)
        save(output/'contacts.json',derived);policy=copy.deepcopy(policy);policy['contacts_sha256']=sha256(output/'contacts.json');save(output/'geometry.json',policy)
        archive=output/'implementation';archive.mkdir()
        for name in methods:shutil.copyfile(ROOT/'scripts'/name,archive/name)
        if any(sha256(p)!=h for p,h in pins.items()) or any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):
            raise ValueError('Pivot placement input or implementation changed')
        names=('contacts.json','geometry.json','source-contacts.json','source-geometry.json','amendment.json')
        save(output/'provenance.json',dict(schema='strep-native-pivot-placement-receipt-v1',amendment_path=str(amendment_path),
            inputs_sha256=pins,implementation_sha256=methods,files_sha256={name:sha256(output/name) for name in names},**meta))
        replay=verify(output);save(output/'result.json',dict(status='complete',label=request['label'].strip(),**replay))
        return read(output/'result.json')
    except Exception as exc:
        save(output/'result.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('amendment');parser.add_argument('output');args=parser.parse_args()
    result=stage(args.amendment,args.output)
    print({key:result[key] for key in ('status','label','original_root_world_placement_contract_preserved','quality_approved','release_approved')})
