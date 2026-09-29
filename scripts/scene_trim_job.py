"""Immutable synchronized scene-trim requests and Studio review output."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from scene_release_job import source_metadata
from trim_scene import trim_clock, run as trim
from scene_runtime import write as runtime
from scene_object_export import export_objects
from package_generated_scenes import contact_events
from scene_region_job import bundle
from scene_constraints import evaluate
from build_soma_preview import ASSET

JOBS = ROOT/'reports/scene-trim-jobs'
METHODS = ['carry_scene_actor.py','audit_scene_timing.py','rig_asset.py','retime_scene.py','scene_animation_curves.py','godot_scene_clock.gd','scene_trim_job.py','trim_scene.py','scene_runtime.py','scene_release_job.py',
           'scene_object_export.py','scene_constraints.py','gltf_tools.py','scene_region_job.py',
           'package_generated_scenes.py','object_geometry.py','object_geometry_mesh.py','rig_clip_import.py']


def source(url):
    data = source_metadata(url, allow_native_runs=True, allow_actor_only=True)
    scene = data['bundle']['scene']
    for actor in scene['actors'].values():
        if actor.get('source_sha256') != sha256(ROOT/actor['motion']):
            raise ValueError('Saved actor source hash changed')
    if scene.get('objects_glb'):
        path = (data['base']/scene['objects_glb']).resolve()
        if not path.is_relative_to(data['base'].resolve()) or path.suffix != '.glb':
            raise ValueError('Object export escapes collection')
        data['files'][path] = sha256(path)
    event_path = (data['base']/data['bundle']['events_file']).resolve() if data['bundle'].get('events_file') else data['path'].parent/'events.json'
    if not event_path.is_relative_to(data['base'].resolve()):raise ValueError('Event file escapes collection')
    if data['bundle'].get('events_file') or event_path.exists():
        data['files'][event_path] = sha256(event_path); data['events_path'] = event_path
    if data.get('events_path'):
        exact=data['events_path'].parent/'retime-contact-windows.json'
        if exact.exists():data['files'][exact]=sha256(exact);data['exact_windows_path']=exact
    data['files'][ASSET] = sha256(ASSET)
    data['trim_revision'] = hashlib.sha256(json.dumps(dict(
        files={str(p): d for p, d in data['files'].items()},
        methods={n: sha256(ROOT/'scripts'/n) for n in METHODS}), sort_keys=True).encode()).hexdigest()
    return data


def metadata(url):
    data = source(url); scene = data['bundle']['scene']
    return dict(source_url=url, revision=data['trim_revision'], frames=scene['frame_count'],
                actors=len(scene['actors']), objects=len(scene['objects']),actor_ids=list(scene['actors']),object_ids=list(scene['objects']))


def validate(payload):
    if not isinstance(payload, dict) or (set(payload) != {'source_url','revision','first','last','label'} and not (set(payload)=={'source_url','revision','operation','frames','label'} and payload.get('operation')=='retime') and not (set(payload)=={'source_url','revision','operation','actor','object','reference_frame','label'} and payload.get('operation')=='carry')):
        raise ValueError('Saved scene, revision, valid edit operation and name required')
    data = source(payload['source_url'])
    if payload['revision'] != data['trim_revision']:
        raise ValueError('Scene or trimming code changed; reload the saved scene')
    if not isinstance(payload['label'], str) or not 1 <= len(payload['label'].strip()) <= 100:
        raise ValueError('Name must contain 1–100 characters')
    events = read(data['events_path']) if data.get('events_path') else contact_events(data['bundle']['scene'])
    if payload.get('operation')=='carry':
        scene=data['bundle']['scene'];ref=payload['reference_frame']
        if not isinstance(payload['actor'],str) or not isinstance(payload['object'],str) or payload['actor'] not in scene['actors'] or payload['object'] not in scene['objects'] or type(ref) is not int or not 0<=ref<scene['frame_count'] or not 3<=scene['frame_count']<=901:
            raise ValueError('Choose an existing actor/object and reference inside a 3–901-frame scene')
    elif payload.get('operation')=='retime':
        from retime_scene import retime_clock
        retime_clock(data['bundle']['scene'],events,payload['frames'],read(data['exact_windows_path']) if data.get('exact_windows_path') else None)
    else:
        trim_clock(data['bundle']['scene'], events, payload['first'], payload['last'])
        if data.get('exact_windows_path'):
            from trim_scene import trim_exact_windows
            trim_exact_windows(data['bundle']['scene'],read(data['exact_windows_path']),payload['first'],payload['last'])
    return data, events


def prepare(payload, folder):
    data, events = validate(payload); folder = Path(folder).resolve()
    if folder.parent != JOBS.resolve() or folder.exists():
        raise ValueError('Fresh scene-trim job folder required')
    folder.mkdir(parents=True); saved = folder/'input'; saved.mkdir()
    scene = copy.deepcopy(data['bundle']['scene'])
    for index, actor in enumerate(scene['actors'].values()):
        target = saved/'actors'/str(index); target.mkdir(parents=True)
        for key, original, name in [('motion',ROOT/actor['motion'],'motion.npz'),('preview_glb',data['base']/actor['preview_glb'],'actor.glb')]:
            shutil.copyfile(original, target/name)
            if sha256(target/name) != data['files'][original.resolve()]:raise ValueError('Source changed during snapshot')
            actor[key] = f'actors/{index}/{name}'
    if scene['objects']:
        if scene.get('objects_glb'):
            original = data['base']/scene['objects_glb']; shutil.copyfile(original, saved/'objects.glb')
            if sha256(saved/'objects.glb') != data['files'][original.resolve()]:raise ValueError('Object export changed during snapshot')
        else:export_objects(scene, saved/'objects.glb')
        scene['objects_glb'] = 'objects.glb'
    license_path = data['base']/'SOMA-preview-LICENSE.txt'
    if not license_path.exists():license_path = ROOT/'vendor/kimodo/LICENSE'
    shutil.copyfile(license_path, saved/'SOMA-LICENSE.txt')
    shutil.copyfile(license_path, folder/'SOMA-preview-LICENSE.txt')
    if data.get('exact_windows_path'):shutil.copyfile(data['exact_windows_path'],saved/'retime-contact-windows.json')
    save(saved/'portable-scene.json', scene); save(saved/'events.json', events); runtime(saved)
    save(folder/'source-bundle.json', data['bundle'])
    implementation = folder/'implementation'; implementation.mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name, implementation/name)
    if source(payload['source_url'])['trim_revision'] != payload['revision']:
        raise ValueError('Source changed during preparation')
    save(folder/'request.json', dict(at=now(), authored=payload,
         files={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()},
         source_files={str(p):d for p,d in data['files'].items()}))
    save(folder/'pipeline.json', dict(status='starting', stage='Prepared synchronized scene trim'))


def run(folder):
    import psutil
    folder = Path(folder).resolve()
    if folder.parent != JOBS.resolve():raise ValueError('Invalid scene-trim job folder')
    try:
        save(folder/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
        request = read(folder/'request.json'); payload = request['authored']
        for name, digest in request['files'].items():
            if sha256(folder/name) != digest:raise ValueError('Saved trim input changed')
        for name in METHODS:
            if sha256(ROOT/'scripts'/name) != sha256(folder/'implementation'/name):raise ValueError('Trimming code changed after preparation')
        if sha256(ASSET) != request['source_files'][str(ASSET)]:raise ValueError('Review skin changed')
        save(folder/'pipeline.json', dict(status='processing', stage='Editing shared scene clock'))
        retiming=payload.get('operation')=='retime'
        carrying=payload.get('operation')=='carry'
        target='carried' if carrying else 'retimed' if retiming else 'trimmed'
        if carrying:
            from carry_scene_actor import run as carry
            carry(folder/'input',folder/target,payload['actor'],payload['object'],payload['reference_frame'])
        elif retiming:
            from retime_scene import run as retime
            retime(folder/'input',folder/target,payload['frames'])
        else:trim(folder/'input',folder/target,payload['first'],payload['last'])
        from audit_scene_timing import run as timing_review, summary as timing_summary
        if not carrying:
            save(folder/'pipeline.json',dict(status='processing',stage='Measuring exported support and joint rates'))
            timing=timing_review(folder/'input',folder/target,folder/'timing-review.json',
                                0 if retiming else payload['first'],None if retiming else payload['last'])
        skin = dict(np.load(ASSET, allow_pickle=False))
        for version in ['input',target]:
            scene = read(folder/version/'portable-scene.json')
            for actor in scene['actors'].values():
                actor['motion'] = (folder/version/actor['motion']).relative_to(ROOT).as_posix()
                actor['preview_glb'] = version+'/'+actor['preview_glb']
            if scene.get('objects_glb'):scene['objects_glb'] = version+'/'+scene['objects_glb']
            data = bundle(scene, evaluate(scene, skin), skin); data['events_file'] = version+'/events.json'
            save(folder/(version+'.json'), data)
        note = 'Shared scene timing edited; contact measurements recomputed. Collision quality, dynamics and naturalness remain unapproved. Prior event context is retained without replay.'
        downloads=[dict(label='Scene animation ZIP',path=target+'/scene-runtime.zip'),dict(label='Events',path=target+'/events.json')]
        if carrying:
            audit=read(folder/target/'carry-audit.json')
            note=f"Actor {payload['actor']} carried by {payload['object']} relative to frame {payload['reference_frame']}. Existing relative motion retained; floor, object and partner contacts require review. Maximum relative mesh error {audit['maximum_relative_skin_error_m']*1e6:.3f} micrometres; world floor depth {audit['maximum_world_floor_depth_m']*1000:.2f} mm. Contact measurements recomputed; motion quality remains unapproved."
            downloads.append(dict(label='Object-relative motion audit',path=target+'/carry-audit.json'))
        else:
            note+=' '+timing_summary(timing)
            downloads.append(dict(label='Support and joint-rate comparison',path='timing-review.json'))
        if retiming:
            recipe=read(folder/target/'retime-recipe.json');note+=f" Speed multiplier {recipe['speed_multiplier']:.6f}; forces and gravity timing were not re-simulated."
            downloads.append(dict(label='Timing and rate measurements',path=target+'/retime-audit.json'))
        elif not carrying:downloads.append(dict(label='Prior events and contact context',path=target+'/trim-context.json'))
        if (folder/target/'retime-contact-windows.json').exists():downloads.append(dict(label='Precise contact windows',path=target+'/retime-contact-windows.json'))
        save(folder/'manifest.json', dict(scenes=[dict(id='input',label=payload['label']+' · Original',variants=dict(palm='input.json'),review_note='Preserved complete source scene.'),
            dict(id='candidate',label=payload['label']+' · Edited',variants=dict(palm=target+'.json'),review_note=note,
                 downloads=downloads)],quality_approved=False))
        save(folder/'pipeline.json', dict(status='complete',stage=note,finished_at=now(),quality_approved=False))
    except Exception as exc:
        save(folder/'pipeline.json', dict(status='failed',error=str(exc),finished_at=now()));raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path)
    run(parser.parse_args().folder)
