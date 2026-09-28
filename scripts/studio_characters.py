"""Local character storage and immutable rig profiles for Studio."""
import hashlib
import re
import shutil
import threading
import uuid
from pathlib import Path
from strep import ROOT, read, save, sha256, now

ASSETS = ROOT / 'reports/character-assets'
JOBS = ROOT / 'reports/rig-jobs'
MAX_UPLOAD = 32 * 1024 * 1024
STORE_LOCK = threading.Lock()


def bundled_fixture(digest):
    """Project-owned catalog only; an uploaded filename never grants provenance."""
    catalog=ROOT/'assets/characters/catalog.json'
    if not catalog.is_file():return None
    for fixture in read(catalog)['characters']:
        if fixture['sha256']!=digest:continue
        paths=[fixture['file'],fixture['profile'],*fixture['attachments'].values()]
        if any(not (ROOT/p).resolve().is_relative_to((ROOT/'assets/characters').resolve()) for p in paths):
            raise ValueError('Bundled fixture path escapes character assets')
        if sha256(ROOT/fixture['file'])!=digest:raise ValueError('Bundled fixture changed')
        return fixture
    return None


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('Invalid character/profile identifier')
    return value


def asset_folder(value):
    folder = ASSETS / identifier(value)
    if not (folder / 'asset.json').is_file():
        raise ValueError('Character not found')
    return folder


def profile_path(asset_id, profile_id):
    path = asset_folder(asset_id) / 'profiles' / (identifier(profile_id) + '.json')
    if not path.is_file() or sha256(path) != profile_id:
        raise ValueError('Saved rig profile is missing or changed')
    return path


def suggest_mapping(inventory):
    from retarget_rig import ROLE_PARENTS
    aliases = {'Hips': ['hips', 'pelvis'], 'Spine2': ['spine1', 'spine2', 'spine02'], 'Chest': ['chest', 'upperchest', 'spine03'],
        'Neck1': ['neck', 'neck1', 'neck01'], 'Head': ['head'],
        'LeftArm': ['leftarm', 'leftupperarm', 'upperarml'], 'RightArm': ['rightarm', 'rightupperarm', 'upperarmr'],
        'LeftForeArm': ['leftforearm', 'leftlowerarm', 'lowerarml'], 'RightForeArm': ['rightforearm', 'rightlowerarm', 'lowerarmr'],
        'LeftHand': ['lefthand', 'handl'], 'RightHand': ['righthand', 'handr'],
        'LeftLeg': ['leftupleg', 'leftleg', 'thighl'], 'RightLeg': ['rightupleg', 'rightleg', 'thighr'],
        'LeftShin': ['leftshin', 'leftlowerleg', 'calfl'], 'RightShin': ['rightshin', 'rightlowerleg', 'calfr'],
        'LeftFoot': ['leftfoot', 'footl'], 'RightFoot': ['rightfoot', 'footr'],
        'LeftToeBase': ['lefttoebase', 'lefttoe', 'toel', 'balll'], 'RightToeBase': ['righttoebase', 'righttoe', 'toer', 'ballr']}
    normalized = lambda name: re.sub('[^a-z0-9]', '', (name or '').lower()).removeprefix('mixamorig')
    mapping = {}
    for role in ROLE_PARENTS:
        matches = [n['index'] for n in inventory['nodes'] if n['skin_joint'] and normalized(n['name']) in aliases[role]]
        if len(matches) == 1 and matches[0] not in mapping.values():
            mapping[role] = matches[0]
    return mapping


def details(asset_id):
    folder = asset_folder(asset_id); metadata = read(folder / 'asset.json')
    inventory = read(folder / 'inventory.json')
    active = read(folder / 'active-profile.json') if (folder / 'active-profile.json').is_file() else None
    profile = read(profile_path(asset_id, active['id'])) if active else read(folder / 'draft-profile.json')
    from retarget_rig import ROLE_PARENTS, OPTIONAL
    from rig_clip_import import catalog
    return dict(**metadata, inventory=inventory, profile=profile, profile_id=active['id'] if active else None,
        roles=[dict(name=name, required=name not in OPTIONAL) for name in ROLE_PARENTS],
        glb_url=f'/files/character-assets/{asset_id}/character.glb',animations=catalog(folder/'character.glb'))


def list_assets():
    return [read(p) for p in sorted(ASSETS.glob('*/asset.json'), key=lambda p:p.stat().st_mtime, reverse=True)]


def import_bytes(data, filename):
    from rig_asset import read_asset, RigAsset
    if not data or len(data) > MAX_UPLOAD:
        raise ValueError('Choose a self-contained rigged GLB up to 32 MiB')
    digest = hashlib.sha256(data).hexdigest()
    filename = str(filename).replace('\\', '/').split('/')[-1][:160] or 'Character.glb'
    with STORE_LOCK:
        if (ASSETS / digest / 'asset.json').exists():
            return details(digest)
        ASSETS.mkdir(parents=True, exist_ok=True)
        temp = ASSETS / ('_incoming-' + uuid.uuid4().hex + '.glb')
        try:
            temp.write_bytes(data); document, binary = read_asset(temp)
            if len(document.get('nodes', [])) > 512 or any(len(s.get('joints', [])) > 256 for s in document.get('skins', [])):
                raise ValueError('Studio import supports up to 512 nodes and 256 skin joints')
            primitives = [p for mesh in document.get('meshes', []) for p in mesh.get('primitives', [])]
            if len(primitives) > 64 or sum(document['accessors'][p['attributes']['POSITION']]['count'] for p in primitives) > 250000:
                raise ValueError('Studio import supports up to 64 primitives and 250,000 mesh vertices')
            rig = RigAsset(document, binary); inventory = rig.inventory()
            folder = ASSETS / digest; folder.mkdir(exist_ok=False)
            temp.replace(folder / 'character.glb')
            save(folder / 'inventory.json', inventory)
            profile = dict(schema='strep-rig-profile-v1', character_sha256=digest, reference_pose='default_nodes',
                           mapping=suggest_mapping(inventory), world_offset_m=[0,0,0], axis_alignment_xyzw={},
                           notes='Local import; suggested mapping and reference axes require review.')
            fixture = bundled_fixture(digest)
            if fixture:
                profile = read(ROOT / fixture['profile'])
                # Use explicit indices in the editor, retaining the exact-profile defaults.
                from retarget_rig import resolve_profile
                profile['mapping'] = resolve_profile(rig, profile)[0]
                for name,path in fixture['attachments'].items():
                    if Path(name).name!=name:raise ValueError('Invalid bundled attachment filename')
                    shutil.copyfile(ROOT / path, folder / name)
            save(folder / 'draft-profile.json', profile)
            save(folder / 'asset.json', dict(id=digest, name=filename, imported_at=now(), bytes=len(data),
                nodes=len(document['nodes']), joints=len(rig.joints), vertices=sum(p['vertices'] for p in inventory['primitives']),
                recognized_fixture=bool(fixture), license_metadata=fixture['license_metadata'] if fixture else 'User-supplied local asset; license metadata not supplied',
                importer_sha256=sha256(ROOT / 'scripts/rig_asset.py')))
        finally:
            temp.unlink(missing_ok=True)
    return details(digest)


def save_profile(payload):
    from rig_asset import RigAsset
    from retarget_rig import resolve_profile
    if not isinstance(payload, dict) or set(payload) != {'asset_id','profile'}:
        raise ValueError('Character and profile required')
    folder = asset_folder(payload['asset_id']); profile = payload['profile']
    if not isinstance(profile, dict): raise ValueError('Rig profile must be an object')
    if profile.get('character_sha256') != payload['asset_id'] or sha256(folder / 'character.glb') != payload['asset_id']:
        raise ValueError('Character/profile checksum mismatch')
    if len(str(profile.get('notes', ''))) > 2000:
        raise ValueError('Profile notes are too long')
    resolve_profile(RigAsset.load(folder / 'character.glb'), profile)
    # Save exact JSON bytes before using their hash as the immutable filename.
    with STORE_LOCK:
        temporary = folder / ('profile-' + uuid.uuid4().hex + '.json')
        save(temporary, profile); digest = sha256(temporary)
        destination = folder / 'profiles' / (digest + '.json'); destination.parent.mkdir(exist_ok=True)
        if destination.exists(): temporary.unlink()
        else: temporary.replace(destination)
        save(folder / 'active-profile.json', dict(id=digest))
    return dict(profile_id=digest, profile=profile, url=f'/files/character-assets/{payload["asset_id"]}/profiles/{digest}.json')


def validate_job(payload, resolve_file):
    if not isinstance(payload, dict) or set(payload) - {'asset_id','profile_id','kind','motion_url','label','correct_contacts','animation_index'}:
        raise ValueError('Invalid rig job request')
    if not {'asset_id','profile_id','kind'} <= set(payload) or payload['kind'] not in ['neutral','transfer','rough_import']:
        raise ValueError('Choose alignment preview or transfer')
    folder = asset_folder(payload['asset_id']); profile = profile_path(payload['asset_id'], payload['profile_id'])
    if sha256(folder/'character.glb') != payload['asset_id']:
        raise ValueError('Imported character changed')
    if type(payload.get('correct_contacts', False)) is not bool:
        raise ValueError('Invalid contact option')
    source = None
    if payload['kind']!='rough_import' and 'animation_index' in payload:raise ValueError('Animation selection applies only to an existing clip')
    if payload['kind']=='rough_import':
        from rig_clip_import import catalog
        number=payload.get('animation_index');clips=catalog(folder/'character.glb')
        if type(number) is not int or not 0<=number<len(clips) or not clips[number]['supported']:raise ValueError('Choose a supported embedded animation')
        if payload.get('correct_contacts') or payload.get('motion_url'):raise ValueError('Prepare existing motion first, then author its contacts')
        label=payload.get('label',clips[number]['name'])
        if not isinstance(label,str) or not 1<=len(label)<=160:raise ValueError('Invalid clip label')
        return dict(asset_id=payload['asset_id'],profile_id=payload['profile_id'],kind='rough_import',label=label,correct_contacts=False,
            animation_index=number,source_kind='gltf_animation',source_motion_sha256=payload['asset_id']),None,profile
    if payload['kind'] == 'transfer':
        url = payload.get('motion_url')
        if not isinstance(url, str) or not url.startswith('/files/') or not url.endswith('/motion.npz') or '?' in url or '#' in url:
            raise ValueError('Choose a motion from Preview')
        source = resolve_file(url)
        if source is None or not source.is_file() or source.suffix != '.npz':
            raise ValueError('Selected motion is unavailable')
    elif payload.get('correct_contacts') or payload.get('motion_url'):
        raise ValueError('Neutral alignment does not use a clip or contact correction')
    label = payload.get('label', 'Neutral alignment' if source is None else 'Transferred motion')
    if not isinstance(label,str) or not 1 <= len(label) <= 160: raise ValueError('Invalid clip label')
    request = dict(asset_id=payload['asset_id'], profile_id=payload['profile_id'], kind=payload['kind'],
        label=label, correct_contacts=payload.get('correct_contacts',False), motion_url=payload.get('motion_url'),
        source_motion_sha256=sha256(source) if source else None)
    if source is not None:
        from motion_origin import describe
        request['motion_origin'] = describe(source)
    return request, source, profile


def prepare_job(request, motion, profile, folder):
    """Freeze the validated transfer inputs before the worker is launched."""
    folder = Path(folder); source = folder/'source'
    source.mkdir(parents=True, exist_ok=False)
    original = asset_folder(request['asset_id'])
    shutil.copyfile(original/'character.glb', source/'character.glb')
    shutil.copyfile(profile, source/'rig-profile.json')
    if sha256(source/'character.glb') != request['asset_id'] or sha256(source/'rig-profile.json') != request['profile_id']:
        raise ValueError('Character/profile changed after validation')
    if motion is not None:
        shutil.copyfile(motion, source/'motion.npz')
        if sha256(source/'motion.npz') != request['source_motion_sha256']:
            raise ValueError('Motion changed after validation')
        from motion_origin import snapshot, verify
        snapshot(motion, source/'motion-origin', request['motion_origin'])
        verify(source/'motion.npz', source/'motion-origin', request['motion_origin'])
    for name in ['asset.json','LICENSE.md','Cesium-logo-terms.txt','UPSTREAM-README.md','provenance.json','packing.json']:
        if (original/name).exists():shutil.copyfile(original/name,source/name)
    save(folder/'request.json', request)
    save(folder/'pipeline.json', dict(status='starting'))


def jobs():
    from contact_edit_job import observed_state
    output=[]
    for folder in sorted(JOBS.glob('*'),reverse=True):
        if not (folder/'request.json').is_file(): continue
        request=read(folder/'request.json'); state=observed_state(folder)
        item=dict(id=folder.name, label=request['label'], asset_id=request['asset_id'], kind=request['kind'], **state)
        if state['status']=='complete' and (folder/'result.json').exists():
            item['result']=read(folder/'result.json')
            if (folder/'transfer/prompt-edit-audit.json').exists():
                from rig_prompt_edit import review_info
                item['result']['prompt_edit_info']=review_info(read(folder/'transfer/prompt-edit-audit.json'))
            for name,variant in item['result']['variants'].items():
                if name not in ('transfer','corrected','input','repeated'):continue
                if name=='repeated' and item['kind']=='loop':
                    for field,file in [('events','events.json'),('contact_review','contact-review.json'),('timeline','timeline.json')]:
                        if (folder/name/file).exists():variant[field]=f'/files/rig-jobs/{folder.name}/{name}/{file}'
                relative='corrected/repeated' if name=='repeated' and variant.get('source_variant')=='corrected' else name
                audit_path=folder/relative/'ground-audit.json'
                if not audit_path.is_file():continue
                audit=read(audit_path)
                if audit['glb_sha256']!=variant['sha256']:continue
                supports=[p for p in audit.get('foot_envelope_support',[]) if p['hover_max_m'] is not None]
                hover=max(supports,key=lambda p:p['hover_max_m']) if supports else None
                variant['ground_inspection']=dict(url=f'/files/rig-jobs/{folder.name}/{relative}/ground-audit.json',
                    contact_provenance=audit.get('contact_provenance'),
                    floor_depth_m=audit['worst_floor']['depth_m'],worst_floor_frame=audit['worst_floor']['frame'],
                    hover_max_m=hover['hover_max_m'] if hover else None,worst_hover_frame=hover['worst_hover_frame'] if hover else None,
                    sole_draft_error=audit.get('sole_draft_error'))
        output.append(item)
    return output
