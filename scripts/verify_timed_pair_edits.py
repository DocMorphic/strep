"""Check actual-key paired edit controls on original, retimed and trimmed scenes."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from timed_rotation_edit import TimedRotationEdit


def run(collection, retimed, trimmed, output):
    collection, retimed, trimmed, output = [Path(p).resolve() for p in (collection, retimed, trimmed, output)]
    if output.exists():
        raise ValueError('Preserve earlier timed-model verification')
    folders = [collection/'candidate/portable', retimed/'retimed', trimmed/'trimmed']
    inputs = {}; sources = []
    for label, folder in zip(['original', 'retimed', 'trimmed'], folders):
        path = folder/'portable-scene.json'; scene = read(path)
        inputs[str(path)] = sha256(path); inputs[str(folder/'scene-runtime.json')] = sha256(folder/'scene-runtime.json')
        windows = folder/'retime-contact-windows.json'
        if windows.exists():
            inputs[str(windows)] = sha256(windows)
            event = read(windows)['windows'][0]['exact_output_frames'][0]/30
        else:
            event = scene['contacts'][0]['start_frame']/30
        for index, (name, actor) in enumerate(scene['actors'].items()):
            path = (folder/actor['preview_glb']).resolve(); inputs[str(path)] = sha256(path)
            if not path.is_relative_to(folder):
                raise ValueError('Actor escaped the saved runtime scene')
            sources.append(dict(id=label+'-'+name, path=path, actor=name, frames=scene['frame_count'], event=event,
                                side='Left' if (index+(label == 'retimed')) % 2 == 0 else 'Right'))
    output.mkdir(); implementation = output/'implementation'; implementation.mkdir()
    methods = ['verify_timed_pair_edits.py', 'timed_rotation_edit.py', 'paired_guarded_temporal.py', 'paired_temporal_neighbor.py',
               'rig_clip_import.py', 'rig_asset.py', 'gltf_tools.py', 'strep.py']
    for name in methods:
        shutil.copyfile(ROOT/'scripts'/name, implementation/name)
    request = dict(at=now(), inputs=inputs, implementation={n: sha256(implementation/n) for n in methods},
                   scope='Declared small rotation-control probes on both actors, alternating left/right arms across three existing scenes. These test timeline/reference preservation, not a fitted correction, collision improvement or new generated action.', quality_approved=False)
    save(output/'request.json', request); cases = []; records = []
    for source in sources:
        folder = output/source['id']; folder.mkdir(); path = source['path']; doc, binary = read_glb(path)
        sampler = AnimationSampler(doc, binary, 0); event = source['event']; window = [event-.5, event+.5]; protected = [[event-.05, event+.05]]
        times = np.unique(np.r_[np.linspace(0, sampler.duration, (source['frames']-1)*4+1), window, protected[0], event])
        names = [source['side']+part for part in ['Shoulder', 'Arm', 'ForeArm', 'Hand']]
        model = TimedRotationEdit(doc, binary, names, times, window, protected, limit_degrees=5.)
        controls = np.deg2rad(.25)*np.sin(np.arange(model.size)*1.31+.2)
        values, mapping = model.edit_rows(controls); zero, _ = model.edit_rows(np.zeros(model.size))
        np.testing.assert_allclose(values, zero+np.einsum('nid,d->ni', mapping, controls), atol=1e-15, rtol=0)
        destination = folder/'candidate.glb'; model.export(controls, destination); shutil.copyfile(path, folder/'input.glb')
        after, payload = read_glb(destination); channels = rotation_channels(after, payload); original = rotation_channels(doc, binary)
        sampled = AnimationSampler(after, payload, 0); world = np.array([sampled.sample(t) for t in times]); source_world = model.source_world
        predicted = model.world(controls); model_error = float(np.abs(predicted-world).max())
        np.testing.assert_allclose(predicted, world, atol=2e-7, rtol=0)
        frozen = (times <= window[0]) | (times >= window[1]) | ((times >= protected[0][0]) & (times <= protected[0][1]))
        frozen_error = float(np.abs(world[frozen]-source_world[frozen]).max())
        np.testing.assert_allclose(world[frozen], source_world[frozen], atol=1e-12, rtol=0)
        unchanged = changed = 0; angles = []
        for node, (_, clock, q) in original.items():
            np.testing.assert_array_equal(channels[node][1], clock)
            if node in model.nodes:
                entry = next(e for e in model.entries if e['node'] == node); locked = np.setdiff1d(np.arange(len(clock)), entry['ids'])
                np.testing.assert_array_equal(channels[node][2][locked], q[locked]); unchanged += len(locked)
                changed += int(np.sum(np.any(channels[node][2] != q, axis=1)))
            else:
                np.testing.assert_array_equal(channels[node][2], q); unchanged += len(clock)
            angles.append(float(np.rad2deg((Rotation.from_quat(q).inv()*Rotation.from_quat(channels[node][2])).magnitude()).max()))
        if not changed or max(angles) > 5.0001:
            raise ValueError('Probe did not make a bounded interior edit')
        # Independent directional check includes all controlled joints, without
        # retaining a large all-frame dense world Jacobian on this laptop.
        probe_times = np.unique(np.r_[window[0], event-.25, event, event+.25, window[1]])
        small = TimedRotationEdit(doc, binary, names, probe_times, window, protected, limit_degrees=5.)
        base, derivative = small.world_pair(controls)
        direction = np.cos(np.arange(model.size)) * 1e-6
        discrepancy = float(np.abs(small.world(controls+direction)-(base+np.einsum('tnijd,d->tnij', derivative, direction))).max())
        if discrepancy > 1e-9:
            raise ValueError('World derivative failed independent directional check')
        for version in ['input', 'candidate']:
            export = folder/(version+'.glb')
            cases.append(dict(id=source['id']+'-'+version, path=export.relative_to(output).as_posix(), sha256=sha256(export), frames=source['frames'], fps=30, sample_by_time=True))
        records.append(dict(id=source['id'], selected_joints=names, frames=source['frames'], sample_times=len(times), controls=controls.tolist(),
            edit_window_seconds=window, protected_seconds=protected, exact_event_seconds=event, frozen_pose_samples=int(frozen.sum()),
            unchanged_quaternion_keys=unchanged, changed_quaternion_keys=changed, maximum_local_edit_degrees=max(angles),
            maximum_export_model_error=model_error, directional_derivative_error=discrepancy, quality_approved=False))
        records[-1]['protected_pose_roundoff'] = frozen_error
        save(output/'progress.json', dict(completed=len(records), total=len(sources))); print(records[-1]['id'], flush=True)
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Input changed during model verification')
    for name, digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Method changed during model verification')
    save(output/'manifest.json', dict(cases=cases, quality_approved=False))
    save(output/'verification.json', dict(at=now(), request_sha256=sha256(output/'request.json'), manifest_sha256=sha256(output/'manifest.json'), records=records,
        pose_samples=sum(r['sample_times'] for r in records), frozen_pose_samples=sum(r['frozen_pose_samples'] for r in records),
        maximum_export_model_error=max(r['maximum_export_model_error'] for r in records),
        maximum_directional_derivative_error=max(r['directional_derivative_error'] for r in records), quality_approved=False))
    save(output/'progress.json', dict(status='complete'))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['collection', 'retimed', 'trimmed', 'output']:
        p.add_argument(name, type=Path)
    a = p.parse_args()
    with threadpool_limits(limits=1):
        run(a.collection, a.retimed, a.trimmed, a.output)
