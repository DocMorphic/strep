"""Local static-prop intake and immutable source-bound surface selections.

This authoring store does not certify grasping or integrate triangle props with
the primitive scene solver. No filename or user license text grants provenance.
"""
import hashlib,json,re,threading,uuid
from pathlib import Path
from static_prop_asset import StaticPropAsset,MAX_BYTES
from strep import ROOT,read,save,now

ASSETS=ROOT/'reports/prop-assets'
STORE_LOCK=threading.RLock()


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):
        raise ValueError('Invalid prop or grip identifier')
    return value


def bounded_path(asset_id,name):
    base=ASSETS.resolve();folder=(base/identifier(asset_id)).resolve()
    if folder.parent!=base:
        raise ValueError('Prop folder escapes local asset store')
    path=(folder/name).resolve()
    if not path.is_relative_to(folder):
        raise ValueError('Prop member escapes asset folder')
    return path


def loaded(asset_id):
    path=bounded_path(asset_id,'prop.glb')
    if not path.is_file():raise ValueError('Prop asset not found')
    prop=StaticPropAsset.load(path)
    if prop.source_sha256!=asset_id:raise ValueError('Stored prop payload changed')
    metadata=read(bounded_path(asset_id,'asset.json'))
    if metadata.get('id')!=asset_id or metadata.get('geometry_sha256')!=prop.geometry_sha256:
        raise ValueError('Stored prop metadata changed')
    inventory=read(bounded_path(asset_id,'inventory.json'))
    if inventory!=prop.inventory():raise ValueError('Stored prop inventory changed')
    return prop,metadata


def details(asset_id):
    prop,metadata=loaded(asset_id)
    return dict(**metadata,inventory=prop.inventory(),
        glb_url=f'/files/prop-assets/{asset_id}/prop.glb',
        grip_ids=[p.stem for p in sorted(bounded_path(asset_id,'grips').glob('*.json'))],
        scene_solver_integrated=False,quality_approved=False,release_approved=False)


def import_bytes(data,filename,license_note=''):
    if type(data) is not bytes or not data or len(data)>MAX_BYTES:
        raise ValueError('Choose a self-contained static GLB up to 32 MiB')
    if not isinstance(filename,str) or len(filename)>1000:
        raise ValueError('Prop filename required')
    if not isinstance(license_note,str) or len(license_note)>2000:
        raise ValueError('License note must be text up to 2,000 characters')
    name=filename.replace('\\','/').split('/')[-1][:160] or 'Prop.glb'
    digest=hashlib.sha256(data).hexdigest()
    with STORE_LOCK:
        folder=bounded_path(digest,'prop.glb').parent
        if folder.exists():
            return details(digest)
        ASSETS.mkdir(parents=True,exist_ok=True)
        temporary=ASSETS/('_incoming-'+uuid.uuid4().hex+'.glb')
        created=False
        try:
            temporary.write_bytes(data)
            prop=StaticPropAsset.load(temporary)
            if prop.source_sha256!=digest:raise ValueError('Upload snapshot changed')
            folder.mkdir(exist_ok=False);created=True
            temporary.replace(folder/'prop.glb')
            save(folder/'inventory.json',prop.inventory())
            save(folder/'asset.json',dict(id=digest,name=name,bytes=len(data),
                imported_at=now(),geometry_sha256=prop.geometry_sha256,
                license_note=license_note,license_note_source='User supplied; rights not verified'))
        finally:
            temporary.unlink(missing_ok=True)
            # Only known files created by this operation, never recursive cleanup.
            if created and not (folder/'asset.json').is_file():
                for member in ('prop.glb','inventory.json','inventory.json.tmp','asset.json.tmp'):
                    (folder/member).unlink(missing_ok=True)
                folder.rmdir()
        return details(digest)


def surface_preview(payload):
    if not isinstance(payload,dict) or set(payload)!={'asset_id','geometry_sha256','face','barycentric'}:
        raise ValueError('Choose a source-bound prop triangle and barycentric point')
    prop,_=loaded(payload['asset_id'])
    if payload['geometry_sha256']!=prop.geometry_sha256:
        raise ValueError('Selected prop geometry changed')
    return prop.surface_point(payload['face'],payload['barycentric'])


def save_grip(payload):
    if not isinstance(payload,dict) or set(payload)!={'asset_id','geometry_sha256','face','barycentric','label'}:
        raise ValueError('Explicit labeled prop surface selection required')
    label=payload['label']
    if not isinstance(label,str) or not label.strip() or len(label)>120:
        raise ValueError('Grip label must be nonempty text up to 120 characters')
    with STORE_LOCK:
        point=surface_preview({k:v for k,v in payload.items() if k!='label'})
        record=dict(schema='strep-prop-grip-selection-v1',label=label,**point)
        raw=(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
        digest=hashlib.sha256(raw).hexdigest()
        path=bounded_path(payload['asset_id'],f'grips/{digest}.json')
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            if path.read_bytes()!=raw:raise ValueError('Saved grip selection changed')
        else:
            temporary=path.parent/(uuid.uuid4().hex+'.tmp')
            try:
                temporary.write_bytes(raw);temporary.replace(path)
            finally:temporary.unlink(missing_ok=True)
        return dict(grip_id=digest,selection=record,
            url=f'/files/prop-assets/{payload["asset_id"]}/grips/{digest}.json')


def grip(asset_id,grip_id):
    identifier(grip_id)
    path=bounded_path(asset_id,f'grips/{grip_id}.json')
    if not path.is_file():raise ValueError('Grip selection not found')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=grip_id:raise ValueError('Saved grip selection changed')
    record=json.loads(raw)
    if (not isinstance(record,dict) or set(record)!={'schema','label','face','barycentric',
            'position_m','winding_normal','source_sha256','geometry_sha256','space',
            'outward_normal_verified','contact_verified'} or not isinstance(record['label'],str)
            or not record['label'].strip() or len(record['label'])>120):
        raise ValueError('Malformed saved grip selection')
    expected=surface_preview(dict(asset_id=asset_id,geometry_sha256=record['geometry_sha256'],
        face=record['face'],barycentric=record['barycentric']))
    if record!={'schema':'strep-prop-grip-selection-v1','label':record['label'],**expected}:
        raise ValueError('Saved grip does not reproduce its source triangle')
    return record


def served_file(url):
    if not isinstance(url,str):return None
    match=re.fullmatch('/files/prop-assets/([a-f0-9]{64})/(prop.glb|grips/([a-f0-9]{64})\\.json)',url)
    if not match:return None
    asset_id,member,grip_id=match.groups()
    if grip_id:grip(asset_id,grip_id)
    else:loaded(asset_id)
    return bounded_path(asset_id,member)
