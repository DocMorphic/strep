"""Queue exact saved mesh-scene corrections; preserve every proposal and source."""
import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from strep import ROOT, read, save, sha256, offline_environment

NAMESPACE = 'mesh-character-jobs'


def folder_for(job):
    if not isinstance(job, str) or not re.fullmatch('[a-f0-9]{32}', job):
        raise ValueError('Choose an exact character correction job')
    base = (ROOT / 'reports' / NAMESPACE).resolve()
    folder = (base / job).resolve()
    if folder.parent != base: raise ValueError('Correction escapes its store')
    return folder


def validate(payload):
    required = {'schema', 'scene_job', 'scene_result_sha256', 'mesh_request', 'correction',
                'editable_clip_boundaries', 'acknowledge_changed_boundary_compatibility'}
    if not isinstance(payload, dict) or set(payload) != required or payload['schema'] != 'strep-studio-mesh-character-v1':
        raise ValueError('Explicit saved-scene correction required')
    if not isinstance(payload['scene_job'], str) or not re.fullmatch('[a-f0-9]{32}', payload['scene_job']):
        raise ValueError('Choose a saved scene job')
    if not isinstance(payload['scene_result_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', payload['scene_result_sha256']):
        raise ValueError('Exact saved scene result required')
    correction = payload['correction']
    if not isinstance(correction, dict) or set(correction) != {'schema', 'draft', 'actors', 'options', 'resume_from'} or correction['schema'] != 'strep-studio-native-scene-fit-v1' or correction['resume_from'] is not None:
        raise ValueError('Use fresh contact adjustment bounds; continuation, clearance and turning-speed settings are not supported here')
    mesh = payload['mesh_request']
    if not isinstance(mesh, dict) or not isinstance(correction['draft'], dict) or mesh.get('draft') != correction['draft'] or correction['draft'].get('rotation_speed_limits'):
        raise ValueError('Correction bounds must belong to the exact mesh scene, without unsupported turning-speed limits')
    options = correction['options']
    if not isinstance(options, dict) or set(options) != {'iterations'} or type(options['iterations']) is not int or not 1 <= options['iterations'] <= 16:
        raise ValueError('Choose 1-16 correction iterations')
    actors = correction['actors']; boundaries = payload['editable_clip_boundaries']
    if not isinstance(actors, dict) or not actors or not isinstance(boundaries, dict) or set(boundaries) != set(actors):
        raise ValueError('Explicit clip-edge choices required for every edited character')
    for edges in boundaries.values():
        if not isinstance(edges, list) or any(e not in ('start', 'end') for e in edges) or len(set(edges)) != len(edges):
            raise ValueError('Choose distinct start/end clip edges, or preserve both')
    changed = any(boundaries.values())
    if type(payload['acknowledge_changed_boundary_compatibility']) is not bool or payload['acknowledge_changed_boundary_compatibility'] != changed:
        raise ValueError('Changed clip edges require transition-review acknowledgment')
    return payload


def prepare(payload):
    validate(payload)
    if len(json.dumps(payload, allow_nan=False).encode()) > 1024**2: raise ValueError('Correction exceeds 1 MiB')
    folder = folder_for(uuid.uuid4().hex); folder.mkdir(parents=True, exist_ok=False)
    save(folder / 'request.json', payload)
    save(folder / 'prepared.json', dict(request_sha256=sha256(folder / 'request.json'),
         methods_sha256={p.name: sha256(p) for p in sorted((ROOT / 'scripts').glob('*.py'))}))
    return folder


def verify_prepared(folder):
    if folder.resolve() != folder_for(folder.name): raise ValueError('Exact queued correction required')
    prepared = read(folder / 'prepared.json')
    if sha256(folder / 'request.json') != prepared['request_sha256']: raise ValueError('Queued correction changed')
    current = {p.name: sha256(p) for p in (ROOT / 'scripts').glob('*.py')}
    if not current or current != prepared['methods_sha256']: raise ValueError('Implementation changed; submit a fresh correction')
    return validate(read(folder / 'request.json'))


def preview_package(source, probe, output):
    """Portable saved scenes: exact actor bytes, unchanged props/grips and poses."""
    shutil.copytree(source, output)
    actor_scene = read(output / 'actor-scene.json')
    if probe is not None:
        for name, entry in actor_scene['actors'].items():
            if (probe / (name + '.glb')).is_file():
                shutil.copyfile(probe / (name + '.glb'), output / entry['glb'])
                entry['sha256'] = sha256(output / entry['glb'])
        shutil.copyfile(probe / 'contacts.json', output / 'contact-report.json')
        shutil.copyfile(probe / 'contact-observations.npz', output / 'contact-observations.npz')
    save(output / 'actor-scene.json', actor_scene)
    mesh = read(output / 'mesh-scene.json'); mesh['actor_scene_sha256'] = sha256(output / 'actor-scene.json')
    save(output / 'mesh-scene.json', mesh)
    policy = read(output / 'geometry-policy.json'); policy['mesh_scene_sha256'] = sha256(output / 'mesh-scene.json')
    save(output / 'geometry-policy.json', policy)
    from native_mesh_prop_scene import MeshPropScene
    import numpy as np
    report, observations = MeshPropScene(output / 'mesh-scene.json').contact_audit()
    with np.load(output / 'contact-observations.npz') as saved:
        if set(saved.files) != set(observations): raise ValueError('Preview contact population changed')
        for name, array in observations.items(): np.testing.assert_array_equal(saved[name], array)
    previous = read(output / 'contact-report.json')
    if report['mesh_contacts'] != previous['mesh_contacts'] or report['all_declared_point_contacts_pass'] != previous['all_declared_point_contacts_pass']:
        raise ValueError('Preview contact measurements changed')
    # Only the file bindings change; all contact observations stay identical.
    save(output / 'contact-report.json', report)
    # The old measurement result does not describe a candidate. Keep provenance
    # in source/, with each preview bound by the correction's own file receipt.
    (output / 'result.json').unlink()


def execute(folder):
    from studio_mesh_scene_preview import verified
    from native_mesh_character_fit import fit
    payload = verify_prepared(folder)
    package = verified(payload['scene_job'], payload['scene_result_sha256'])
    if read(package / 'studio-draft.json') != payload['mesh_request']:
        raise ValueError('Saved scene differs from the bound object/contact draft; save and measure it again')
    source = folder / 'source'; shutil.copytree(package, source)
    actors = copy.deepcopy(payload['correction']['actors'])
    for name, permission in actors.items():
        if 'editable_clip_boundaries' in permission: raise ValueError('Duplicate clip-edge policy')
        permission['editable_clip_boundaries'] = payload['editable_clip_boundaries'][name]
    save(folder / 'permissions.json', dict(schema='strep-native-mesh-character-edit-v1',
         mesh_scene='source/mesh-scene.json', mesh_scene_sha256=sha256(source / 'mesh-scene.json'), actors=actors))
    result = fit(folder / 'permissions.json', source / 'geometry-policy.json', folder / 'fit',
                 iterations=payload['correction']['options']['iterations'])
    preview_package(source, None, folder / 'preview/original')
    if result['candidate'] is not None:
        preview_package(source, folder / 'fit' / result['candidate'], folder / 'preview/candidate')
    # Verify source package and implementation again after all numerical work.
    verified(payload['scene_job'], payload['scene_result_sha256']); verify_prepared(folder)
    files = {p.relative_to(folder).as_posix(): sha256(p) for base in ('source', 'fit', 'preview')
             for p in sorted((folder / base).rglob('*')) if p.is_file()}
    files['permissions.json'] = sha256(folder / 'permissions.json')
    report = dict(schema='strep-studio-mesh-character-result-v1', **result, files_sha256=files,
                  request_sha256=sha256(folder / 'request.json'), scene_result_sha256=payload['scene_result_sha256'])
    save(folder / 'result.json', report)
    with zipfile.ZipFile(folder / 'correction-package.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in [*files, 'result.json', 'request.json', 'prepared.json']: archive.write(folder / name, name)
    save(folder / 'receipt.json', dict(result_sha256=sha256(folder / 'result.json'),
         zip_sha256=sha256(folder / 'correction-package.zip'), request_sha256=sha256(folder / 'request.json')))
    return report


def launch(folder):
    import psutil
    process = None
    try:
        with (folder / 'supervisor.log').open('w', encoding='utf8') as log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(folder)], cwd=ROOT,
                env=offline_environment(), stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        save(folder / 'supervisor.json', dict(pid=process.pid, created_at=psutil.Process(process.pid).create_time()))
        return process
    except (OSError, psutil.Error) as error:
        if process is not None and process.poll() is None: process.terminate(); process.wait(timeout=5)
        save(folder / 'startup.json', dict(status='failed', reason=str(error))); raise OSError(str(error)) from error


def review(job):
    folder = folder_for(job); prepared = read(folder / 'prepared.json')
    if sha256(folder / 'request.json') != prepared['request_sha256']: raise ValueError('Saved correction request changed')
    pipeline = read(folder / 'guard/pipeline.json') if (folder / 'guard/pipeline.json').is_file() else read(folder / 'startup.json') if (folder / 'startup.json').is_file() else dict(status='starting')
    if pipeline['status'] not in ('complete', 'failed', 'deferred') and (folder / 'supervisor.json').is_file():
        import psutil
        owner = read(folder / 'supervisor.json')
        try: live = psutil.Process(owner['pid']).create_time() == owner['created_at']
        except psutil.NoSuchProcess: live = False
        if not live: pipeline = dict(status='failed', reason='Correction supervisor stopped; submit a fresh request')
    response = dict(id=job, status=pipeline['status'], original_selected=True, quality_approved=False, release_approved=False)
    if pipeline['status'] == 'complete':
        receipt = read(folder / 'receipt.json')
        if receipt['request_sha256'] != prepared['request_sha256'] or sha256(folder / 'result.json') != receipt['result_sha256'] or sha256(folder / 'correction-package.zip') != receipt['zip_sha256']:
            raise ValueError('Correction receipt changed')
        result = read(folder / 'result.json')
        if result['request_sha256'] != prepared['request_sha256']: raise ValueError('Correction result binding changed')
        for name, digest in result['files_sha256'].items():
            path = (folder / name).resolve()
            if not path.is_relative_to(folder) or sha256(path) != digest: raise ValueError('Saved correction artifact changed')
        response.update(result=result, result_sha256=receipt['result_sha256'],
            comparison_url=f'/mesh-character-viewer.html?job={job}&result={receipt["result_sha256"]}',
            download_url=f'/files/{NAMESPACE}/{job}/correction-package.zip')
    elif pipeline['status'] in ('failed', 'deferred'):
        response['error'] = read(folder / 'failure.json')['error'] if (folder / 'failure.json').is_file() else pipeline.get('reason') or 'Worker did not complete'
    return response


def served_file(url):
    match = re.fullmatch(r'/files/mesh-character-jobs/([a-f0-9]{32})/correction-package\.zip', url)
    if not match or review(match[1])['status'] != 'complete': return None
    return folder_for(match[1]) / 'correction-package.zip'


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('folder', type=Path); parser.add_argument('--worker', action='store_true')
    args = parser.parse_args(); folder = args.folder.resolve()
    if folder != folder_for(folder.name): raise ValueError('Exact queued correction required')
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        try:
            with worker_lock():
                # threadpoolctl can only limit libraries already loaded. Keep
                # this worker-only import inside admission and the job lock.
                import native_mesh_character_fit
                with threadpool_limits(limits=1): execute(folder)
        except Exception as error:
            save(folder / 'failure.json', dict(error=str(error))); raise
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        result = run(Path(__file__), folder / 'guard', ResourcePolicy(expected_rss_bytes=512*1024**2,
            max_tree_rss_bytes=512*1024**2, stable_seconds=15, admission_seconds=600, max_seconds=900), worker_args=[str(folder), '--worker'])
        save(folder / 'resource-replay.json', audit(folder / 'guard'))
        return {'complete': 0, 'failed': 1, 'deferred': 2}[result['status']]
    return 0


if __name__ == '__main__': raise SystemExit(main())
