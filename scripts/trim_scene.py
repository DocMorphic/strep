"""Trim a portable native-SOMA scene on one clock, retaining event context."""
import argparse
import copy
import hashlib
from pathlib import Path
import shutil
import zipfile

import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256
from inspect_motion import validate_motion
from gltf_tools import write_glb, read_glb, accessor, append_accessor
from scene_constraints import sample_object
from scene_runtime import local, write as write_runtime


def trim_clock(scene, events, first, last):
    frames = scene['frame_count']
    if scene.get('fps') != 30 or events.get('fps') != 30:
        raise ValueError('Scene and event clocks must be 30 fps')
    if any(type(v) is not int for v in [first, last, frames]) or not 0 <= first < last < frames or last-first < 2:
        raise ValueError('Choose at least three native frames inside the scene')
    output = copy.deepcopy(scene)
    output['frame_count'] = last-first+1
    contacts, clipped, active = [], [], []
    for contact in scene['contacts']:
        a, b = contact['start_frame'], contact['end_frame']
        if type(a) is not int or type(b) is not int or not 0 <= a <= b < frames:
            raise ValueError('Invalid source contact clock')
        if a < first <= b:
            active.append(contact['id'])
        if b < first or a > last:
            continue
        c = copy.deepcopy(contact)
        c.update(start_frame=max(a, first)-first, end_frame=min(b, last)-first)
        contacts.append(c)
        if a < first or b > last:
            clipped.append(dict(id=c['id'], source_interval=[a, b], retained_interval=[max(a, first), min(b, last)]))
    output['contacts'] = contacts
    for name, obj in output.get('objects', {}).items():
        p, r = sample_object(scene['objects'][name], frames)
        q = Rotation.from_matrix(r[first:last+1]).as_quat()
        obj['keyframes'] = [dict(frame=i, translation_m=point.tolist(), rotation_xyzw=quat.tolist())
                            for i, (point, quat) in enumerate(zip(p[first:last+1], q))]
    kept, before, after = [], [], []
    for event in events['events']:
        f, t = event.get('frame'), event.get('time_s')
        if type(f) is not int or not 0 <= f <= frames or type(t) not in (int, float) or not np.isfinite(t) or abs(t-f/30) > 1e-8:
            raise ValueError('Invalid source event clock')
        # Preserve the source package's exclusive terminal marker only when its
        # original end is retained. Do not pull a future action into this trim.
        keep = first <= f <= last or (last == frames-1 and f == frames)
        if keep:
            e = copy.deepcopy(event); e.update(frame=f-first, time_s=(f-first)/30); kept.append(e)
        else:
            (before if f < first else after).append(copy.deepcopy(event))
    mapped = copy.deepcopy(events); mapped['events'] = kept
    context = dict(source_first_frame=first, source_last_frame=last,
                   events_before_range=before, events_after_range=after,
                   contacts_active_at_start=active, clipped_contact_windows=clipped,
                   scope='Excluded events are history, not replayed commands. Active contact windows are authored intent, not inferred physical state. Baked object motion remains its sole owner.')
    return output, mapped, context


def trim_export(path, frames, first, last):
    """Keep the actual meshes/materials/rig; slice the baked animation tracks."""
    doc, binary = read_glb(path); binary = bytearray(binary)
    if len(doc.get('animations', [])) != 1:
        raise ValueError('One baked animation per participant export required')
    inputs, outputs = {}, {}
    for sampler in doc['animations'][0]['samplers']:
        clock, values = sampler['input'], sampler['output']
        times = accessor(doc, binary, clock); data = accessor(doc, binary, values)
        if sampler.get('interpolation', 'LINEAR') not in ['LINEAR', 'STEP'] or len(times) != frames or not np.allclose(times, np.arange(frames)/30, atol=1e-5, rtol=0) or len(data) != frames:
            raise ValueError('Export must use a complete baked 30 fps clock')
        if clock not in inputs:
            inputs[clock] = append_accessor(doc, binary, np.arange(last-first+1)/30, 'SCALAR')
        if values not in outputs:
            outputs[values] = append_accessor(doc, binary, data[first:last+1], doc['accessors'][values]['type'])
        sampler.update(input=inputs[clock], output=outputs[values])
    return doc, binary


def run(source, output, first, last):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'reports'):
        raise ValueError('Choose a fresh output directory under reports')
    scene = read(source/'portable-scene.json'); events = read(source/'events.json')
    runtime = read(source/'scene-runtime.json')
    if runtime['source_scene_sha256'] != sha256(source/'portable-scene.json') or runtime['source_events_sha256'] != sha256(source/'events.json'):
        raise ValueError('Source scene or events changed after packaging')
    if runtime['fps'] != 30 or runtime['frames'] != scene['frame_count'] or set(runtime['actors']) != set(scene['actors']) or set(runtime['objects']) != set(scene.get('objects', {})):
        raise ValueError('Runtime participants or clock differ from the scene')
    if any(runtime['actors'][name]['placement'] != actor['transform'] for name, actor in scene['actors'].items()):
        raise ValueError('Runtime actor placement differs from the source scene')
    if any(obj.get('ownership') != 'baked_track' for obj in runtime['objects'].values()):
        raise ValueError('Scene trim requires baked object ownership')
    trimmed, mapped, context = trim_clock(scene, events, first, last)
    inputs = {str(source/name): sha256(source/name) for name in ['portable-scene.json', 'events.json', 'scene-runtime.json', 'SOMA-LICENSE.txt']}
    motions, exports = {}, {}
    for name, actor in scene['actors'].items():
        path = local(source, actor['motion']); glb = local(source, actor['preview_glb'])
        if sha256(path) != actor['source_sha256'] or sha256(glb) != runtime['actors'][name]['sha256']:
            raise ValueError('Source actor changed')
        motion = dict(np.load(path, allow_pickle=False)); validate_motion(motion, 30)
        if motion['posed_joints'].shape[1] != 77 or any(v.ndim < 1 or len(v) != scene['frame_count'] for v in motion.values()):
            raise ValueError('Current trim requires native SOMA77 arrays on the shared clock')
        motions[name] = {k: v[first:last+1].copy() for k, v in motion.items()}
        exports[name] = trim_export(glb, scene['frame_count'], first, last)
        inputs.update({str(path): sha256(path), str(glb): sha256(glb)})
    if scene.get('objects'):
        path = local(source, scene['objects_glb'])
        if sha256(path) != runtime['object_clip']['sha256']:
            raise ValueError('Source object export changed')
        inputs[str(path)] = sha256(path)
        object_export = trim_export(path, scene['frame_count'], first, last)
    output.mkdir(parents=True)
    save(output/'source-scene.json', scene); save(output/'source-events.json', events)
    for index, (name, motion) in enumerate(motions.items()):
        folder = output/'actors'/str(index); folder.mkdir(parents=True)
        np.savez_compressed(folder/'motion.npz', **motion)
        doc, binary = exports[name]
        write_glb(folder/'actor.glb', doc, binary)
        trimmed['actors'][name].update(motion=f'actors/{index}/motion.npz', preview_glb=f'actors/{index}/actor.glb', source_sha256=sha256(folder/'motion.npz'))
    if trimmed.get('objects'):
        write_glb(output/'objects.glb', *object_export); trimmed['objects_glb'] = 'objects.glb'
    trimmed['id'] += f'-trim-{first}-{last}'
    save(output/'portable-scene.json', trimmed); save(output/'events.json', mapped)
    save(output/'trim-context.json', context)
    shutil.copyfile(source/'SOMA-LICENSE.txt', output/'SOMA-LICENSE.txt')
    save(output/'trim-recipe.json', dict(inputs=inputs, first_frame=first, last_frame=last,
         implementation_sha256=sha256(__file__), quality_approved=False,
         scope='Integer-frame synchronous trim of all native SOMA actors, baked objects and authored contact/event clocks. No retiming, root recentering, collision repair or quality approval. Prior whole-clip quality reports are not copied.'))
    write_runtime(output)
    files = {p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()}
    save(output/'package-manifest.json', dict(files=files, quality_approved=False))
    with zipfile.ZipFile(output/'scene-runtime.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in [*files, 'package-manifest.json']: archive.write(output/name, name)
    with zipfile.ZipFile(output/'scene-runtime.zip') as archive:
        if archive.testzip() is not None or any(hashlib.sha256(archive.read(name)).hexdigest() != digest for name, digest in files.items()):
            raise ValueError('Trim archive verification failed')
    print(dict(frames=trimmed['frame_count'], actors=len(motions), objects=len(trimmed.get('objects', {})), events=len(mapped['events']), quality_approved=False))
    return trimmed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--first', type=int, required=True); parser.add_argument('--last', type=int, required=True)
    args = parser.parse_args(); run(args.source, args.output, args.first, args.last)
