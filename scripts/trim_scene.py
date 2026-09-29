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
        if type(f) not in (int,float) or not np.isfinite(f) or not 0 <= f <= frames or type(t) not in (int, float) or not np.isfinite(t) or abs(t-f/30) > 1e-8:
            raise ValueError('Invalid source event clock')
        # Preserve the source package's exclusive terminal marker only when its
        # original end is retained. Do not pull a future action into this trim.
        keep = first <= f <= last or (last == frames-1 and last < f <= frames)
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
    """Clip LINEAR/STEP curves at exact boundaries; keep mesh/rig and interior keys."""
    from rig_clip_import import AnimationSampler
    doc, binary = read_glb(path); binary = bytearray(binary)
    if len(doc.get('animations', [])) != 1:
        raise ValueError('One animation per participant export required')
    source=AnimationSampler(doc,binary,0)
    if abs(source.duration-(frames-1)/30)>1e-5:
        raise ValueError('Export clock differs from source scene')
    if any(type(x) is not int for x in [first,last]) or not 0<=first<last<frames:
        raise ValueError('Integer trim bounds inside source clock required')
    animation=doc['animations'][0]
    # Preserve decoded channels before changing their sampler indices.
    channels=source.channels;samplers=[]
    start,end=first/30,last/30
    for channel,(node,prop,times,values,mode) in zip(animation['channels'],channels):
        if mode not in ['LINEAR','STEP']:
            raise ValueError('Curve trimming currently supports LINEAR and STEP tracks')
        if mode=='LINEAR' and len(times)==frames and np.allclose(times,np.arange(frames)/30,rtol=0,atol=1e-5):
            clock=np.arange(last-first+1)/30;data=values[first:last+1]
        else:
            # Avoid duplicate output times from float32 noise at a cut. Sample
            # the exact requested boundaries rather than copying nearby keys.
            times=times.astype(float)
            margin=1e-7 if mode=='LINEAR' else 0.
            selected=times[(times>start+margin)&(times<end-margin)]
            source_times=np.r_[start,selected,end]
            clock=source_times-start
            data=np.array([source.value(prop,times,values,mode,float(t)) for t in source_times])
        if np.any(np.diff(np.asarray(clock,dtype=np.float32))<=0):
            raise ValueError('Trimmed key times collapse at export precision')
        clock_id=append_accessor(doc,binary,clock,'SCALAR')
        value_id=append_accessor(doc,binary,data,'VEC4' if prop=='rotation' else 'VEC3')
        channel['sampler']=len(samplers)
        samplers.append(dict(input=clock_id,output=value_id,interpolation=mode))
    animation['samplers']=samplers
    AnimationSampler(doc,binary,0)
    return doc,binary


def trim_exact_windows(scene, windows, first, last):
    """Retain precise retime intent alongside conservative native contact keys."""
    entries=windows.get('windows')
    if not isinstance(entries,list):raise ValueError('Invalid exact contact windows')
    by_id={c['id']:c for c in scene['contacts']}
    if len(entries)!=len(by_id) or {e['id'] for e in entries}!=set(by_id):
        raise ValueError('Exact contact windows differ from scene contacts')
    contacts=[];mapped=[];excluded=[];active=[]
    for entry in entries:
        interval=entry.get('exact_output_frames')
        if not isinstance(interval,list) or len(interval)!=2 or any(type(v) not in (int,float) or not np.isfinite(v) for v in interval) or not 0<=interval[0]<=interval[1]<scene['frame_count']:
            raise ValueError('Invalid precise contact clock')
        a,b=interval
        if b<first or a>last:
            excluded.append(copy.deepcopy(entry));continue
        if a<first<=b:active.append(entry['id'])
        exact=[max(a,first)-first,min(b,last)-first]
        native=[int(np.floor(exact[0]+1e-10)),int(np.ceil(exact[1]-1e-10))]
        c=copy.deepcopy(by_id[entry['id']]);c.update(start_frame=native[0],end_frame=native[1]);contacts.append(c)
        mapped.append(dict(id=c['id'],exact_output_frames=exact,native_enclosing_frames=native,
                           maximum_enclosure_seconds=max(exact[0]-native[0],native[1]-exact[1])/30))
    return contacts,dict(windows=mapped,excluded_exact_windows=excluded,contacts_active_at_start=active,
                         scope='Precise authored intervals clipped and shifted; integer solver intervals conservatively enclose them. Excluded intervals remain provenance, not active requests.')


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
    exact_path=source/'retime-contact-windows.json';exact=None
    if exact_path.exists():
        trimmed['contacts'],exact=trim_exact_windows(scene,read(exact_path),first,last)
        inputs[str(exact_path)]=sha256(exact_path)
        context['exact_contacts_active_at_start']=exact['contacts_active_at_start']
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
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Source changed during trimming')
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
    if exact is not None:
        save(output/'retime-contact-windows.json',exact)
        shutil.copyfile(exact_path,output/'source-retime-contact-windows.json')
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
