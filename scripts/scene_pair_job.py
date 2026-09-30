"""Studio supervision for immutable paired-scene fitting and review."""
import argparse
import os
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from paired_edit_request import JOBS, describe, compile_request, prepare as prepare_request

METHODS = ['scene_pair_job.py', 'publish_scene_pair_fit.py', 'verify_scene_pair_fit.py',
           'run_godot_rig_import.py', 'godot_import_audit.gd', 'retime_scene.py', 'scene_constraints.py',
           'scene_region_job.py', 'floor_contact.py', 'inspect_motion.py']


def metadata(url):
    data = describe(url)
    return {k: data[k] for k in ['source_url', 'revision', 'duration_s', 'contacts']} | dict(
        actors={name: dict(joints=entry['joints']) for name, entry in data['actors'].items()})


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'label', 'request'}:
        raise ValueError('Name and complete paired edit request required')
    if not isinstance(payload['label'], str) or not 1 <= len(payload['label'].strip()) <= 100:
        raise ValueError('Name the correction using 1-100 characters')
    return compile_request(payload['request'])


def prepare(payload, folder):
    validate(payload); folder = Path(folder).resolve(); prepare_request(payload['request'], folder)
    attach_review_inputs(folder, payload['label'])


def attach_review_inputs(folder, label):
    folder = Path(folder).resolve()
    if folder.parent != JOBS.resolve() or (folder/'job.json').exists():
        raise ValueError('Unregistered immutable prepared request required')
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 100:
        raise ValueError('Name the correction using 1-100 characters')
    from scene_pair_problem import load_actors
    load_actors(folder)
    request = read(folder/'request.json'); scene = read(folder/'input/scene.json')['scene']
    files = {}; meta = folder/'review-input'; meta.mkdir(); native = {}
    for index, (name, actor) in enumerate(scene['actors'].items()):
        source = (ROOT/actor['motion']).resolve(); digest = request['inputs'].get(str(source))
        if digest is None or sha256(source) != digest: raise ValueError('Native review source changed')
        target = meta/f'actor-{index}.npz'; shutil.copyfile(source, target)
        native[name] = target.relative_to(folder).as_posix(); files[native[name]] = digest
    for filename in ['events.json', 'retime-contact-windows.json']:
        matches = [Path(p) for p in request['inputs'] if Path(p).name == filename]
        if len(matches) > 1: raise ValueError('Ambiguous saved event metadata')
        if matches:
            source = matches[0]; target = meta/filename; shutil.copyfile(source, target)
            digest = request['inputs'][str(source)]
            if sha256(target) != digest: raise ValueError('Saved event metadata changed')
            files[target.relative_to(folder).as_posix()] = digest
    from build_soma_preview import ASSET
    asset = str(ASSET.resolve())
    if sha256(ASSET) != request['inputs'].get(asset): raise ValueError('Review skin changed')
    license_path = ROOT/'vendor/kimodo/LICENSE'; shutil.copyfile(license_path, meta/'SOMA-LICENSE.txt')
    files['review-input/SOMA-LICENSE.txt'] = sha256(license_path)
    from study_scene_pair_fit import METHODS as fitting_methods
    methods = sorted(set(METHODS+fitting_methods)); snapshot = folder/'worker-implementation'; snapshot.mkdir()
    for name in methods: shutil.copyfile(ROOT/'scripts'/name, snapshot/name)
    save(folder/'job.json', dict(label=label.strip(), native=native, files=files,
        prepared_request_sha256=sha256(folder/'request.json'), asset_sha256=sha256(ASSET),
        implementation={n: sha256(snapshot/n) for n in methods}, quality_approved=False))
    save(folder/'pipeline.json', dict(status='starting', stage='Paired correction prepared'))


def listing():
    from contact_edit_job import observed_state
    jobs = []
    for folder in sorted(JOBS.glob('*'), reverse=True):
        if not (folder/'job.json').is_file(): continue
        state = observed_state(folder); progress = read(folder/'fit/progress.json') if (folder/'fit/progress.json').exists() else None
        jobs.append(dict(id=folder.name, label=read(folder/'job.json')['label'], **state, progress=progress))
    return dict(jobs=jobs)


def copy_completed_fit(folder, study):
    folder, study = Path(folder).resolve(), Path(study).resolve()
    result, request = read(study/'result.json'), read(study/'request.json')
    if result['status'] != 'complete' or result['request_sha256'] != sha256(study/'request.json'):
        raise ValueError('Completed bound fitting study required')
    if Path(request['prepared_request']).resolve() != folder/'request.json' or request['inputs'].get(str(folder/'request.json')) != sha256(folder/'request.json'):
        raise ValueError('Completed study belongs to another prepared request')
    if folder.is_relative_to(study) or study.is_relative_to(folder/'fit') or (folder/'fit').exists():
        raise ValueError('Separate study and fresh fit destination required')
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Completed study input changed')
    shutil.copytree(study, folder/'fit')
    if sha256(folder/'fit/result.json') != sha256(study/'result.json'):
        raise ValueError('Copied result differs')
    save(folder/'adopted-study.json', dict(source=str(study), request_sha256=sha256(study/'request.json'), result_sha256=sha256(study/'result.json')))


def run(folder, completed_study=None):
    folder = Path(folder).resolve()
    if folder.parent != JOBS.resolve(): raise ValueError('Saved paired job folder required')
    try:
        import psutil
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        save(folder/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
        job = read(folder/'job.json')
        if sha256(folder/'request.json') != job['prepared_request_sha256']: raise ValueError('Prepared request changed')
        for name, digest in job['files'].items():
            if sha256(folder/name) != digest: raise ValueError('Review input changed')
        for name, digest in job['implementation'].items():
            if sha256(ROOT/'scripts'/name) != digest or sha256(folder/'worker-implementation'/name) != digest:
                raise ValueError('Worker changed after preparation')
        with worker_lock(), threadpool_limits(limits=1):
            from study_scene_pair_fit import run as fit
            from verify_scene_pair_fit import run as replay
            from run_godot_rig_import import run as engine
            from publish_scene_pair_fit import publish
            save(folder/'pipeline.json', dict(status='processing', stage='Checking meshes and fitting both actors'))
            if completed_study is None:
                fit(folder, folder/'fit')
            else:
                copy_completed_fit(folder, completed_study)
            save(folder/'pipeline.json', dict(status='processing', stage='Independently replaying exported motion'))
            replay(folder/'fit', folder/'replay')
            save(folder/'pipeline.json', dict(status='processing', stage='Checking game-engine import'))
            engine(folder/'fit', folder/'engine')
            save(folder/'pipeline.json', dict(status='processing', stage='Building scene comparison'))
            collection = publish(folder)
        accepted = read(folder/'fit/result.json')['selected'] is not None
        save(folder/'pipeline.json', dict(status='complete', stage='Local correction ready for review' if accepted else 'No correction accepted; original retained',
            collection=collection, default_scene='candidate' if accepted else 'source', accepted_local_step=accepted, quality_approved=False, finished_at=now()))
    except Exception as exc:
        save(folder/'pipeline.json', dict(status='failed', error=str(exc), finished_at=now())); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('folder', type=Path)
    p.add_argument('--completed-study', type=Path); p.add_argument('--label'); args = p.parse_args()
    if args.completed_study is not None and not (args.folder/'job.json').exists():
        if args.label is None: p.error('--label is required to register an existing prepared request')
        attach_review_inputs(args.folder, args.label)
    run(args.folder, args.completed_study)
