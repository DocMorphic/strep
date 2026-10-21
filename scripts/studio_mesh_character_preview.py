"""Receipt-bound original/candidate comparison, without changing selection."""
import re
from strep import ROOT, read, sha256
from studio_mesh_character_job import folder_for, review
from studio_mesh_scene_preview import SAMPLING_METHODS


def verified(job, digest):
    if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest): raise ValueError('Exact correction result required')
    result = review(job)
    if result['status'] != 'complete' or result['result_sha256'] != digest: raise ValueError('Completed unchanged correction required')
    folder = folder_for(job)
    methods = read(folder / 'prepared.json')['methods_sha256']
    if any(methods.get(name) != sha256(ROOT / 'scripts' / name) for name in SAMPLING_METHODS):
        raise ValueError('Sampling implementation changed; remeasure this scene')
    return folder, result['result']


def descriptor(job, digest):
    folder, result = verified(job, digest)
    base=preview_directory(result)
    def scene(role):
        package = folder / base / role
        mesh = read(package / 'mesh-scene.json'); actors = read(package / 'actor-scene.json')
        contact = read(package / 'contact-report.json'); policy = read(package / 'geometry-policy.json')
        def asset(entry):
            name = entry['glb']
            if not re.fullmatch(r'(actors|props)/[A-Za-z0-9_-]{1,64}\.glb', name): raise ValueError('Packaged asset required')
            if result['files_sha256'].get(f'{base}/{role}/{name}') != entry['sha256']: raise ValueError('Packaged asset binding changed')
            return {**entry, 'url': f'/files/mesh-character-previews/{job}/{digest}/{role}/{name}'}
        contacts = []
        for row in mesh['mesh_contacts']:
            path = (package / row['grip']).resolve()
            if not path.is_relative_to(package.resolve()) or sha256(path) != row['grip_sha256']: raise ValueError('Exact packaged grip required')
            contacts.append({**row, 'grip_position_m': read(path)['position_m']})
        if result.get('recoverable'):
            from studio_mesh_character_recovery_job import local
            name=result['geometry_reports'][role];path=local(folder,name)
            if result['files_sha256'].get(name)!=sha256(path):raise ValueError('Recovered geometry binding changed')
            geometry=read(path)
        else:geometry = read(folder / 'fit' / ('original' if role == 'original' else result['candidate']) / 'geometry.json')
        return dict(schema='strep-mesh-scene-preview-v2', role=role, original_selected=True,
            skin_weight_policy='native-all-influence-unit-sum', duration_s=actors['duration_s'],
            actors={k: asset(v) for k, v in actors['actors'].items()}, props={k: asset(v) for k, v in mesh['props'].items()},
            objects=actors['objects'], planes=policy['planes'], mesh_contacts=contacts, contacts=contact['mesh_contacts'],
            all_declared_point_contacts_pass=contact['all_declared_point_contacts_pass'],
            other_contact_count=len(actors['contacts']), motion_fitted=role=='candidate', geometry_evaluated=True,
            sampled_geometry_pass=geometry['sampled_conditions_pass'], quality_approved=False, release_approved=False)
    return dict(schema='strep-mesh-character-comparison-v1', job=job, result_sha256=digest,
                original=scene('original'), candidate=scene('candidate') if result['candidate'] else None,
                sampled_candidate_pass=result['sampled_candidate_pass'], stop_reason=result['stop_reason'],
                original_selected=True, quality_approved=False, release_approved=False)


def preview_directory(result):
    if not result.get('recoverable'):return 'preview'
    value=result.get('preview_directory')
    if not isinstance(value,str) or not re.fullmatch('publications/[a-f0-9]{32}/preview',value):
        raise ValueError('Exact completed preview publication required')
    return value


def served_file(url):
    match = re.fullmatch(r'/files/mesh-character-previews/([a-f0-9]{32})/([a-f0-9]{64})/(original|candidate)/((?:actors|props)/[A-Za-z0-9_-]{1,64}\.glb)', url)
    if not match: return None
    job, digest, role, name = match.groups(); folder, result = verified(job, digest)
    relative = f'{preview_directory(result)}/{role}/{name}'; path = (folder / relative).resolve()
    if not path.is_relative_to(folder) or relative not in result['files_sha256'] or sha256(path) != result['files_sha256'][relative]:
        raise ValueError('Exact saved comparison asset required')
    return path
