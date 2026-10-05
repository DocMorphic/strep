"""Read a caller-pinned portable region for explicit Studio contact staging."""
import copy
import re
from pathlib import Path
from urllib.parse import urlsplit
from material_patch_bundle import verify, fields, sha_binding, METHODS as BUNDLE_METHODS
from rig_material_patch import require
from strep import ROOT, read, sha256

SCHEMA = 'strep-studio-material-patch-v1'
METHODS = tuple(dict.fromkeys(BUNDLE_METHODS + ('studio_material_patch.py',)))
PREFIXES = ('/files/rig-jobs/', '/files/character-assets/', '/files/native-correction-previews/',
            '/files/native-support-jobs/', '/files/native-scene-jobs/', '/files/native-scene-fit-jobs/')


def load(payload, resolver):
    """No motion queries or writes. The HTTP caller holds the production lock."""
    fields(payload, ('schema', 'actor', 'bundle', 'result_sha256', 'patch_id', 'vertex_indices', 'reduction'),
           'saved region request')
    require(payload['schema'] == SCHEMA, 'Saved region request schema required')
    fields(payload['actor'], ('glb', 'sha256'), 'selected character')
    actor = payload['actor']; sha_binding(actor['sha256'], 'character binding')
    url = actor['glb']; require(isinstance(url, str), 'Served character URL required')
    parsed = urlsplit(url)
    require(not parsed.scheme and not parsed.netloc and not parsed.query and not parsed.fragment
            and parsed.path == url and url.startswith(PREFIXES), 'Choose a served character clip')
    source = resolver(url); require(source is not None, 'Selected character is not served')
    source = Path(source).resolve(); root = (ROOT/'reports').resolve()
    require(source.is_relative_to(root) and source.suffix.lower() == '.glb'
            and source.is_file() and 0 < source.stat().st_size <= 128*1024**2,
            'Bounded existing workspace character required')
    require(sha256(source) == actor['sha256'], 'Selected character changed')
    relative = payload['bundle']
    require(isinstance(relative, str) and 1 <= len(relative) <= 512
            and all(re.fullmatch(r'[A-Za-z0-9_-]+', part) for part in relative.split('/')),
            'Bundle folder relative to reports required')
    folder = (root/relative).resolve()
    require(folder.is_relative_to(root) and folder != root and folder.is_dir(), 'Existing local region bundle required')
    # Bound the full population before the recursive portable verifier reads it.
    count = total = entries = 0
    for path in folder.rglob('*'):
        entries += 1
        require(entries <= 1024, 'Complete region bundle exceeds Studio entry budget')
        require(not path.is_symlink() and path.resolve().is_relative_to(folder), 'Bundle files must stay inside their folder')
        if path.is_file():
            count += 1; size = path.stat().st_size; total += size
            require(count <= 512 and size <= 128*1024**2 and total <= 600*1024**2,
                    'Complete region bundle exceeds Studio import budget')
    sha_binding(payload['result_sha256'], 'region result binding')
    require(isinstance(payload['patch_id'], str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', payload['patch_id']),
            'Explicit saved patch ID required')
    indices = payload['vertex_indices']
    require(isinstance(indices, list) and 1 <= len(indices) <= 256
            and all(type(i) is int and i >= 0 for i in indices) and len(set(indices)) == len(indices),
            'Choose 1-256 distinct ordered patch vertex indices')
    require(payload['reduction'] in ('individual', 'centroid'), 'Explicit contact measurement required')
    methods = {n:sha256(ROOT/'scripts'/n) for n in METHODS}
    manifest = verify(folder, expected_result_sha256=payload['result_sha256'])
    entry = next((p for p in manifest['patches'] if p['id'] == payload['patch_id']), None)
    require(entry is not None, 'Saved patch ID not found')
    patch_path = folder/entry['path']; value = read(patch_path)
    require(sha256(patch_path) == entry['sha256'], 'Saved patch changed')
    require(value['source']['character_sha256'] == actor['sha256'],
            'Region must bind the exact animated clip; transfer the bundle first')
    require(all(i < len(value['vertices']) for i in indices), 'Patch vertex index out of range')
    selected = [copy.deepcopy(value['vertices'][i]) for i in indices]
    require(verify(folder, expected_result_sha256=payload['result_sha256']) == manifest
            and sha256(source) == actor['sha256'] and sha256(patch_path) == entry['sha256'],
            'Region or character changed while loading')
    require(all(sha256(ROOT/'scripts'/n) == h for n,h in methods.items()), 'Region loading method changed')
    return dict(schema=SCHEMA, request=copy.deepcopy(payload), implementation_sha256=methods,
                patch=dict(glb_sha256=actor['sha256'], vertices=selected, reduction=payload['reduction']),
                binding=dict(bundle=relative, result_sha256=payload['result_sha256'], patch_id=entry['id'],
                             patch_sha256=entry['sha256'], source=copy.deepcopy(value['source']),
                             vertex_indices=list(indices), reduction=payload['reduction']),
                explicit_vertex_correspondence=True, original_selected=True, anatomical_review_pending=True,
                animation_edited=False, motion_contacts_measured=False, engine_executed=False,
                human_reviewed=False, quality_approved=False, training_admitted=False, release_approved=False)
