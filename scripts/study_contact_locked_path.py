"""Bake a hand-clearance pose guide to native keys and retain inter-key contact."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now


def run(source, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from contact_locked_native import NativeRotationEdit, locked_pair
    from elbow_swivel import local_transforms
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import measure
    from palm_contact_region import rebind_surface_point
    from paired_temporal_neighbor import rotation_channels
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh native path export required')
    sr, sq = read(source/'result.json'), read(source/'request.json')
    if not (sr['status'] == 'complete' and sr['original_pose_limits_pass'] and sr['failed_geometry_samples'] == 0 and sr['contact_pose_preserved_exact']):
        raise ValueError('Validated bounded pose guide required; rate failures remain separate')
    files = dict(sq['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in sr['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Escaping source output')
        files[str(path)] = digest
    for name, digest in sq['implementation'].items():
        path = (source/'implementation'/name).resolve()
        if path.parent != source/'implementation': raise ValueError('Escaping method archive')
        files[str(path)] = digest
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed input')
    def bound(path):
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound evidence: '+str(path))
        return read(path)
    motion = Path(sq['source']); mq = bound(motion/'request.json'); pose = bound(Path(mq['source'])/'request.json')
    region = bound(Path(pose['source'])/'request.json'); donor = bound(Path(region['source'])/'request.json')
    baseline = Path(pose['baseline']); br = bound(baseline/'result.json')
    trial = next(t for t in bound(baseline/'trials.json') if t['folder'] == br['selected'])
    prepared, actors = load_actors(region['prepared']); target = sq['target']; contact = mq['selected_contact']
    for key in ('effector', 'target'): contact[key] = rebind_surface_point(contact[key], contact[key]['surface_vertex'])
    contact['tolerance_m'] = target['maximum_gap_m']
    event = sq['event_time_s']; window = sq['window_s']; protected = sq['protected_spans']
    guard, uniform = np.asarray(sq['guard_times_s']), np.asarray(sq['uniform_times_s'])
    planned = np.load(source/'planned-worlds.npz', allow_pickle=False); plan_times = planned['times']
    rigs = []; refs = []; readers = []; ref_readers = []
    for i, entry in enumerate(trial['actors']):
        path = motion/f'candidate-{i}.glb'; reference = baseline/br['selected']/entry['path']
        for p in (path, reference):
            if files.get(str(p)) != sha256(p): raise ValueError('Unbound rig or original reference')
        rigs.append(RigAsset.load(path)); refs.append(RigAsset.load(reference))
        readers.append(AnimationSampler(rigs[-1].document, rigs[-1].binary, 0)); ref_readers.append(AnimationSampler(refs[-1].document, refs[-1].binary, 0))
    full = np.unique(np.r_[plan_times, guard, uniform, event, window, 0., [r.duration for r in readers]])
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(sq['implementation']) | {'contact_locked_native.py', 'study_contact_locked_path.py'}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        target=target, selected_contact=contact, event_time_s=event, window_s=window, protected_spans=protected,
        guard_times_s=guard.tolist(), uniform_times_s=uniform.tolist(), original_bins_s=sq['original_bins_s'],
        policy='Write planned arm local rotations only to editable native keys. Joint-wise geodesic endpoint fitting preserves the source contact rotation at the exact decoder interpolation fraction. Check original native-key budgets and unchanged channels; independently decode contact, all guard meshes, floor and original motion caps. A pose guide is not assumed valid after interpolation.',
        quality_approved=False))
    decoded = []; clips = []; locks = []
    for i, (rig, ref, reader) in enumerate(zip(rigs, refs, readers)):
        nodes = donor['actors'][i]['nodes'][:3]
        edit = NativeRotationEdit(rig.document, rig.binary, [rig.document['nodes'][n]['name'] for n in nodes], full, window, protected, (ref.document, ref.binary))
        guide_local = np.array([local_transforms(w, rig.parents) for w in planned[f'actor{i}']]); values = {}; actor_locks = []
        for entry in edit.model.entries:
            node = entry['node']; q = entry['source'].astype(float).copy(); clock = entry['clock']; ids = entry['ids']
            indices = np.searchsorted(plan_times, clock[ids]); np.testing.assert_array_equal(plan_times[indices], clock[ids])
            replacement = Rotation.from_matrix(guide_local[indices, node, :3, :3]).as_quat()
            replacement *= np.where(np.sum(replacement*q[ids], axis=1) < 0, -1., 1.)[:, None]; q[ids] = replacement
            left = int(np.searchsorted(clock, event, side='right')-1)
            if event == float(clock[left]):
                q[left] = entry['source'][left]; record = dict(native_key_contact=True)
            else:
                if left not in ids or left+1 not in ids: raise ValueError('Contact bracket must be editable')
                fraction = (event-float(clock[left]))/float(clock[left+1]-clock[left])
                desired = Rotation.from_quat(reader.value('rotation', clock, entry['source'], 'LINEAR', event)).as_matrix()
                pair, record = locked_pair(desired, *Rotation.from_quat(q[[left, left+1]]).as_matrix(), fraction)
                pair_q = Rotation.from_matrix(pair).as_quat(); pair_q *= np.where(np.sum(pair_q*entry['source'][[left, left+1]], axis=1) < 0, -1., 1.)[:, None]
                q[[left, left+1]] = pair_q; record.update(fraction=fraction, native_key_contact=False)
            values[node] = q; actor_locks.append(dict(node=node, lower_key=left, **record))
        path = output/f'candidate-{i}.glb'; edit.export(values, path); locks.append(actor_locks)
        asset = RigAsset.load(path); current = AnimationSampler(asset.document, asset.binary, 0)
        world = np.array([current.sample(t) for t in full]); before = np.array([reader.sample(t) for t in full])
        frozen = (full <= window[0]) | (full >= window[1])
        for a, b in protected: frozen |= (full >= a) & (full <= b)
        np.testing.assert_array_equal(world[frozen], before[frozen])
        event_index = int(np.searchsorted(full, event)); error = float(np.max(np.abs(world[event_index]-before[event_index])))
        if error > 1e-6: raise ValueError('Decoded contact lock drift exceeds matrix tolerance')
        assert len(current.channels) == len(reader.channels)
        for a, b in zip(current.channels, reader.channels):
            assert a[:2] == b[:2] and a[4] == b[4]; np.testing.assert_array_equal(a[2], b[2])
            if a[1] != 'rotation' or a[0] not in nodes: np.testing.assert_array_equal(a[3], b[3])
        original_channels, channels = rotation_channels(ref.document, ref.binary), rotation_channels(asset.document, asset.binary); angles = []
        for node, budget in zip(donor['actors'][i]['nodes'], donor['actors'][i]['original_budgets_degrees']):
            angle = float(np.rad2deg((Rotation.from_quat(original_channels[node][2]).inv()*Rotation.from_quat(channels[node][2])).magnitude()).max())
            if angle > budget+1e-4: raise ValueError('Decoded original native edit budget exceeded')
            angles.append(angle)
        decoded.append(world); clips.append(dict(path=path.name, sha256=sha256(path), contact_matrix_drift=error,
            original_edit_angles_degrees=angles, native_clocks_unselected_channels_outside_window_protected_poses_exact=True))
    save(output/'locks.json', locks)
    def payload(values):
        parts = [features(w, r.joints) for w, r in zip(values, refs)]
        return {k: np.concatenate([p[k] for p in parts], axis=1) for k in ('positions', 'rotations')}
    raw = [np.array([r.sample(t) for t in uniform]) for r in ref_readers]
    caps = SampledMotionCaps(payload(raw), uniform, sq['original_bins_s']); actual = payload([w[np.searchsorted(full, uniform)] for w in decoded]); rates = []
    for kind, values, ceiling in zip(('position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'), measures(actual, caps.dt), caps.caps):
        excess = values-ceiling-caps.tolerance; rates.append(dict(kind=kind, failed_rows=int(np.count_nonzero(excess > 0)), maximum_excess=float(excess.max())))
    observations = []; contact_check = None; floor = []
    for index, time in enumerate(guard):
        frame = int(np.searchsorted(full, time)); points = [r.vertices(w[frame])@a['rotation'].T+a['translation'] for r, w, a in zip(rigs, decoded, actors)]
        surface = audit(points[0], actors[0]['faces'], points[1], actors[1]['faces'])
        depths = [penetration(points[a], points[b], actors[b]['faces'], tolerance_m=1e-8) for a, b in ((0, 1), (1, 0))]
        passed = not any(v for k, v in surface['counts'].items() if k != 'disjoint') and not any(surface['degenerate_faces']) and max(d['max_depth_m'] for d in depths) <= 1e-8
        row = dict(time_s=float(time), surface=surface, depths=depths, inter_actor_pose_screen_pass=bool(passed)); observations.append(row)
        if time == event:
            centers = []; normals = []
            for i, (p, a) in enumerate(zip(points, actors)):
                v = (contact['effector'] if i == 0 else contact['target'])['surface_vertex']; patch = a['faces'][np.any(a['faces'] == v, axis=1)]
                c, n = palm_geometry(p, patch, v); centers.append(c); normals.append(n)
            contact_check = measure(centers, normals, target); row['contact'] = contact_check
        save(output/f'geometry-{index:02d}.json', row)
        before = [r.vertices(reader.sample(time))@a['rotation'].T+a['translation'] for r, reader, a in zip(rigs, readers, actors)]
        floor.append(dict(time_s=float(time), source_m=[max(0., -float(p[:, 1].min())) for p in before], exported_m=[max(0., -float(p[:, 1].min())) for p in points]))
        print(dict(phase='locked_native_geometry', completed=index+1, total=len(guard), passed=bool(passed)), flush=True)
    save(output/'decoded.json', dict(clips=clips, contact=contact_check, motion_rates=rates)); save(output/'floor.json', floor)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed input during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Changed method during study')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        contact_target_pass=contact_check['contact_target_pass'], contact_mesh_screen_pass=next(o['inter_actor_pose_screen_pass'] for o in observations if o['time_s'] == event),
        guard_samples=len(guard), failed_geometry_samples=sum(not o['inter_actor_pose_screen_pass'] for o in observations),
        maximum_vertex_depth_m=max(d['max_depth_m'] for o in observations for d in o['depths']),
        original_motion_caps_pass=all(r['failed_rows'] == 0 for r in rates), native_animation_exported=True,
        continuous_collision_certified=False, selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output)
