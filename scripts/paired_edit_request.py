"""Immutable saved-scene inputs for a reusable two-actor rotation solver."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from scene_trim_job import source
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from timed_rotation_edit import TimedRotationEdit
from paired_temporal_neighbor import rotation_channels

JOBS = ROOT/'reports/paired-edit-jobs'
METHODS = ['paired_edit_request.py', 'timed_rotation_edit.py', 'scene_trim_job.py', 'scene_release_job.py',
           'paired_temporal_neighbor.py', 'paired_guarded_temporal.py', 'rig_clip_import.py', 'rig_asset.py', 'gltf_tools.py']


def describe(url):
    data = source(url); scene = data['bundle']['scene']
    if len(scene['actors']) != 2 or scene['objects']:
        raise ValueError('This paired solver input requires two actors and no scene objects')
    actors = {}; durations = []
    for name, entry in scene['actors'].items():
        path = (data['base']/entry['preview_glb']).resolve(); doc, binary = read_glb(path)
        sampler = AnimationSampler(doc, binary, 0); channels = rotation_channels(doc, binary)
        if len(doc.get('skins', [])) != 1:
            raise ValueError('One skin per actor required')
        actors[name] = dict(path=str(path), sha256=sha256(path),
            joints=[doc['nodes'][i]['name'] for i in doc['skins'][0]['joints'] if i in channels], placement=entry['transform'])
        durations.append(sampler.duration)
    if max(durations)-min(durations) > 1e-5:
        raise ValueError('Actors must share the saved scene duration')
    precise = {}
    if data.get('exact_windows_path'):
        precise = {r['id']: r['exact_output_frames'] for r in read(data['exact_windows_path'])['windows']}
    contacts = []
    for contact in scene['contacts']:
        if contact['target'].get('space') != 'actor':
            continue
        if contact['actor'] not in actors or contact['target']['actor'] not in actors or contact['actor'] == contact['target']['actor']:
            raise ValueError('Contact must join the two different saved actors')
        interval = precise.get(contact['id'], [contact['start_frame'], contact['end_frame']])
        if len(interval) != 2 or any(type(v) not in (int, float) or not np.isfinite(v) for v in interval) or not 0 <= interval[0] <= interval[1] <= min(durations)*30+1e-5:
            raise ValueError('Saved contact has an invalid precise interval')
        contacts.append(dict(id=contact['id'], actors=[contact['actor'], contact['target']['actor']], seconds=[float(v)/30 for v in interval]))
    methods = {name: sha256(ROOT/'scripts'/name) for name in METHODS}
    inputs = {str(p): digest for p, digest in data['files'].items()}
    revision = hashlib.sha256(json.dumps(dict(inputs=inputs, methods=methods), sort_keys=True).encode()).hexdigest()
    return dict(source_url=url, bundle_path=str(data['path']), revision=revision, duration_s=min(durations), actors=actors, contacts=contacts,
                inputs=inputs, methods=methods, scope='Saved native two-actor scenes, linear joint rotations and explicit protected contact times. Input compilation only; no fitting or quality approval.')


def compile_request(payload):
    fields = {'schema', 'source_url', 'revision', 'actors', 'window_s', 'protected_contact_ids', 'limit_degrees', 'knots_s'}
    if not isinstance(payload, dict) or set(payload) != fields or payload['schema'] != 'strep-paired-rotation-request-v1':
        raise ValueError('Complete paired rotation request required')
    data = describe(payload['source_url'])
    if data['revision'] != payload['revision']:
        raise ValueError('Saved scene or edit model changed; reload its revision')
    if not isinstance(payload['actors'], dict) or set(payload['actors']) != set(data['actors']):
        raise ValueError('Both saved actors require explicit joint selections')
    selected = payload['protected_contact_ids']
    if not isinstance(selected, list) or any(not isinstance(i, str) for i in selected) or len(set(selected)) != len(selected):
        raise ValueError('Distinct protected contact IDs required')
    contacts = {c['id']: c for c in data['contacts']}
    if set(selected)-set(contacts):
        raise ValueError('Protected contact is not in the saved paired scene')
    if type(payload['limit_degrees']) not in (int, float) or not np.isfinite(payload['limit_degrees']):
        raise ValueError('Finite numeric rotation budget required')
    for key in ['window_s', 'knots_s']:
        if not isinstance(payload[key], list) or any(type(v) not in (int, float) or not np.isfinite(v) for v in payload[key]):
            raise ValueError('Finite numeric window and knot times required')
    window = np.asarray(payload['window_s'], float)
    if window.shape != (2,) or not np.isfinite(window).all() or not 0 <= window[0] < window[1] <= data['duration_s']:
        raise ValueError('Edit window outside the shared animation')
    if window[1]-window[0] > 5:
        raise ValueError('Local fitting window is limited to five seconds per request')
    # The future motion constraints share a 120 Hz clock with halo stencils.
    first = max(0, int(np.floor(window[0]*120))-2)
    last = min(int(np.floor(data['duration_s']*120)), int(np.ceil(window[1]*120))+2)
    times = np.arange(first, last+1)/120
    protected = [contacts[i]['seconds'] for i in selected]; models = {}
    for name, spec in payload['actors'].items():
        if not isinstance(spec, dict) or set(spec) != {'joints'} or not isinstance(spec['joints'], list) or not 1 <= len(spec['joints']) <= 8 or any(n not in data['actors'][name]['joints'] for n in spec['joints']):
            raise ValueError('Choose one to eight available rotation joints for each actor')
        doc, binary = read_glb(data['actors'][name]['path'])
        models[name] = TimedRotationEdit(doc, binary, spec['joints'], times, window, protected,
            knots=payload['knots_s'], limit_degrees=payload['limit_degrees'])
    for path, digest in data['inputs'].items():
        if sha256(path) != digest:
            raise ValueError('Input changed while compiling paired controls')
    return data, models, protected


def prepare(payload, output):
    data, models, protected = compile_request(payload); output = Path(output).resolve()
    if output.parent != JOBS.resolve() or output.exists():
        raise ValueError('Fresh paired-edit-jobs directory required')
    output.mkdir(parents=True); snapshot = output/'implementation'; snapshot.mkdir()
    for name in METHODS:
        shutil.copyfile(ROOT/'scripts'/name, snapshot/name)
    (output/'input').mkdir()
    shutil.copyfile(data['bundle_path'], output/'input/scene.json')
    if sha256(output/'input/scene.json') != data['inputs'][data['bundle_path']]:
        raise ValueError('Scene changed during snapshot')
    actors = {}
    for number, (name, entry) in enumerate(data['actors'].items()):
        folder = output/'input'/str(number); folder.mkdir(parents=True)
        path = folder/'actor.glb'; shutil.copyfile(entry['path'], path)
        if sha256(path) != entry['sha256']:
            raise ValueError('Actor changed during snapshot')
        actors[name] = dict(path=path.relative_to(output).as_posix(), sha256=sha256(path), placement=entry['placement'],
            controls=models[name].size, editable_keys={str(e['node']): e['ids'].tolist() for e in models[name].entries})
    if describe(payload['source_url'])['revision'] != payload['revision']:
        raise ValueError('Scene changed during snapshot')
    save(output/'request.json', dict(at=now(), authored=payload, inputs=data['inputs'], implementation=data['methods'], actors=actors,
        scene_snapshot=dict(path='input/scene.json', sha256=sha256(output/'input/scene.json')),
        protected_seconds=protected, sample_times_seconds=next(iter(models.values())).times.tolist(),
        original_reference='Immutable input actor exports. A continuation must keep these references; cumulative controls cannot reset the budget.', quality_approved=False))
    save(output/'state.json', dict(status='prepared', solver_executed=False, quality_approved=False,
        scope='Verified immutable solver input. No generated correction, completed worker or release approval.'))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('request', type=Path); p.add_argument('output', type=Path); a = p.parse_args()
    prepare(read(a.request), a.output)
