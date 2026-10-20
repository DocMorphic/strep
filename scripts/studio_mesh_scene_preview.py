"""Read-only preview of a receipt-verified saved scene, never the mutable draft."""
import re
from strep import ROOT, read, sha256
from studio_mesh_scene_job import folder_for, review

SAMPLING_METHODS = ('rig_asset.py', 'gltf_tools.py', 'rig_clip_import.py',
                    'native_support_clock.py', 'native_support_skin.py',
                    'native_scene_contacts.py', 'native_mesh_prop_scene.py')


def verified(job, digest):
    if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
        raise ValueError('Exact saved result hash required')
    if review(job)['status'] != 'complete':
        raise ValueError('Complete saved scene required')
    package = folder_for(job) / 'package'
    if sha256(package / 'result.json') != digest:
        raise ValueError('Saved scene result changed')
    methods = read(package / 'implementation.json')['methods_sha256']
    if any(methods.get(name) != sha256(ROOT / 'scripts' / name) for name in SAMPLING_METHODS):
        raise ValueError('Contact sampling implementation changed; remeasure or use the archived preview')
    return package


def descriptor(job, digest):
    package = verified(job, digest)
    result = read(package / 'result.json')
    manifest = read(package / 'mesh-scene.json')
    scene = read(package / 'actor-scene.json')
    policy = read(package / 'geometry-policy.json')
    prefix = f'/files/mesh-scene-previews/{job}/{digest}/'

    def asset(entry):
        name = entry['glb']
        if not re.fullmatch(r'(actors|props)/[A-Za-z0-9_-]{1,64}\.glb', name):
            raise ValueError('Packaged asset path required')
        if result['files_sha256'].get(name) != entry['sha256']:
            raise ValueError('Packaged asset binding required')
        return {**entry, 'url': prefix + name}

    contacts = []
    for contact in manifest['mesh_contacts']:
        grip = read(package / contact['grip'])
        if result['files_sha256'].get(contact['grip']) != contact['grip_sha256']:
            raise ValueError('Packaged grip binding required')
        contacts.append({**contact, 'grip_position_m': grip['position_m']})
    return dict(schema='strep-mesh-scene-preview-v1', job=job, result_sha256=digest,
                skin_weight_policy='native-all-influence-unit-sum',
                duration_s=scene['duration_s'], actors={k: asset(v) for k, v in scene['actors'].items()},
                props={k: asset(v) for k, v in manifest['props'].items()}, objects=scene['objects'],
                planes=policy['planes'], mesh_contacts=contacts, contacts=result['contacts'],
                all_declared_point_contacts_pass=result['all_declared_point_contacts_pass'],
                other_contact_count=len(scene['contacts']), motion_fitted=False,
                geometry_evaluated=False, quality_approved=False, release_approved=False)


def served_file(relative):
    match = re.fullmatch(r'/files/mesh-scene-previews/([a-f0-9]{32})/([a-f0-9]{64})/((?:actors|props)/[A-Za-z0-9_-]{1,64}\.glb)', relative)
    if not match:
        return None
    job, digest, name = match.groups()
    package = verified(job, digest)
    files = read(package / 'result.json')['files_sha256']
    path = (package / name).resolve()
    if not path.is_relative_to(package.resolve()) or name not in files or sha256(path) != files[name]:
        raise ValueError('Exact packaged asset required')
    return path
