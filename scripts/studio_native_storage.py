"""Original-bound storage fitting contracts and retained Studio evidence."""
import copy,re
from pathlib import Path
from native_scene_boundary_edit import BoundarySceneEdits,SCHEMA as BOUNDARY
from native_rotation_storage_repair import authoring_digest,SCHEMA as REPAIR
from native_storage_continuation import StorageContinuationEdits,fingerprint
from strep import read,sha256

METHODS={'studio_native_storage.py','native_scene_boundary_edit.py','native_rotation_storage_repair.py',
    'native_rotation_storage_search.py','native_storage_continuation.py','native_fit_storage.py'}
FITTER_METHODS=METHODS-{'studio_native_storage.py'}
SCHEMA='strep-studio-native-scene-fit-v3'
COMPONENT_SCHEMA='strep-studio-native-scene-fit-v4'


def components(payload):return isinstance(payload,dict) and payload.get('schema')==COMPONENT_SCHEMA


def method_names(payload,*,fitter=False):
    names=set(FITTER_METHODS if fitter else METHODS)
    if components(payload):
        from native_fit_component_storage import METHODS as COMPONENT_METHODS
        names.update(COMPONENT_METHODS)
    return names


def boundary(permissions,payload=None):
    return dict(schema=BOUNDARY,permissions=copy.deepcopy(permissions),
        boundary_keys=copy.deepcopy(payload['boundary_keys']) if components(payload) else {n:dict(start='preserve',end='preserve') for n in permissions['actors']},
        acknowledge_changed_boundary_compatibility=payload['acknowledge_changed_boundary_compatibility'] if components(payload) else False)


def policy(edits,payload=None):
    extra={};schema=REPAIR
    if components(payload):
        from native_component_storage_repair import SCHEMA as COMPONENT_REPAIR
        schema=COMPONENT_REPAIR;extra=dict(allowed_paths=['rotation','translation'])
    return dict(schema=schema,authoring_sha256=authoring_digest(edits),**extra,maximum_component_steps=1,
        maximum_corrections=64,acknowledge_storage_adjustment=True)


def checked(root,relative,digest):
    root=Path(root).resolve();value=Path(relative)
    if value.is_absolute() or '..' in value.parts:raise ValueError('Contained storage evidence required')
    path=(root/value).resolve()
    if not path.is_relative_to(root) or sha256(path)!=digest:raise ValueError('Stored fitting evidence changed')
    return path


def validate_fit(fit,scene,permissions,*,payload=None):
    """Read-only archive checks; no inherited geometry or motion approval."""
    fit=Path(fit).resolve();request=read(fit/'request.json');result=read(fit/'result.json')
    digest=sha256(fit/'contacts.json');body=BoundarySceneEdits(boundary(permissions,payload),scene,digest,
        rotation_storage_policy=request['rotation_storage_policy'])
    repair=policy(body,payload)
    for filename,key,expected in [('boundary-edit.json','boundary_edit_sha256',body.request),
            ('storage-repair-policy.json','storage_repair_policy_sha256',repair)]:
        checked(fit,filename,request[key])
        if read(fit/filename)!=expected:raise ValueError('Original stored authoring or repair policy changed')
    if result.get('original_storage_reference_retained') is not True:
        raise ValueError('Original-bound stored fit required')
    checked(fit,'source-rate-caps.npz',result['source_rate_caps_sha256'])
    if result['source_rate_tolerance']!=1e-5 or result['source_rate_bins']!=4:
        raise ValueError('Original source-rate contract changed')
    checked(fit,'final-storage-continuation.json',result['final_storage_continuation_sha256'])
    state=read(fit/'final-storage-continuation.json')
    for i,name in enumerate(scene.actors):
        if name not in body.actors:continue
        actor=state['actors'].get(name)
        expected=(fit/'proposal'/f'actor-{i}.glb').resolve()
        if actor is None or (fit/actor['path']).resolve()!=expected:
            raise ValueError('Canonical final stored actor required')
    continuation_type=StorageContinuationEdits
    if components(payload):
        from native_component_storage_continuation import ComponentContinuationEdits
        continuation_type=ComponentContinuationEdits
    final=continuation_type(body,repair,state,fit)
    final_record=next(p for p in result['probes'] if p['label']=='final')
    if state['controls']!=final_record['controls']:raise ValueError('Final stored controls changed')
    for probe in result['probes']:
        label=probe['label']
        if not isinstance(label,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',label):
            raise ValueError('Contained native probe label required')
        folder=fit/'probes'/label
        checked(folder,'storage-repair.json',probe['storage_repair_sha256'])
        receipt=read(folder/'storage-repair.json')
        if (receipt['original_authoring_sha256']!=authoring_digest(body)
                or receipt['storage_policy_sha256']!=fingerprint(repair)
                or any(receipt[k] is not False for k in ('geometry_assessed','quality_approved','release_approved'))):
            raise ValueError('Unapproved original-bound storage receipt required')
        checked(folder,'unrounded-observations.npz',receipt['unrounded_observations_sha256'])
        if receipt['search_result_sha256'] is not None:checked(folder,'storage-search/search-result.json',receipt['search_result_sha256'])
        seen=receipt['native_probe_receipts_sha256']
        if not isinstance(seen,dict) or not seen or len(seen)>513:
            raise ValueError('Complete bounded native search population required')
        for native_label,checksum in seen.items():
            if not isinstance(native_label,str) or not re.fullmatch(r'start|storage-[0-7]-(?:[0-9]|[1-5][0-9]|6[0-3])',native_label):
                raise ValueError('Contained finite storage-search label required')
            raw=folder/'storage-search'/native_label;checked(raw,'probe.json',checksum);record=read(raw/'probe.json')
            checked(raw,'observations.npz',record['observations_sha256'])
            if set(record['files'])!=set(body.actors):raise ValueError('Complete edited-actor storage population required')
            for i,(name,actor) in enumerate(record['files'].items()):
                if actor['path']!=f'actor-{i}.glb':raise ValueError('Canonical native search asset required')
                checked(raw,actor['path'],actor['sha256'])
        selected=receipt['selected_native_label']
        if selected not in seen:raise ValueError('Selected native search receipt missing')
        selected_record=read(folder/'storage-search'/selected/'probe.json')
        if receipt['corrections']!=selected_record['corrections']:
            raise ValueError('Selected storage corrections changed')
        for name,actor in selected_record['files'].items():
            if sha256(folder/(name+'.glb'))!=actor['sha256']:raise ValueError('Selected native export changed')
        reused=receipt.get('reused_repair')
        if reused is not None:
            path=Path(reused['path']).resolve()
            if not path.is_relative_to(fit/'probes') or path.name!='storage-repair.json' or sha256(path)!=reused['sha256']:
                raise ValueError('Bound reused repair changed')
    final.check_continuation()
    return body,final
