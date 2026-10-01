"""Refresh native wrist retractions against interpolated hand half-spaces."""
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
    from native_wrist_retraction import NativeWristRetraction, repair
    from paired_approach_basis import BoundSkin
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
    if not (sr['status'] == 'complete' and sr['contact_target_pass'] and sr['contact_mesh_screen_pass']):
        raise ValueError('Clean source contact required; trajectory failures remain separate')
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
    guide = bound(Path(sq['source'])/'request.json'); motion = Path(guide['source'])
    mq = bound(motion/'request.json'); pose = bound(Path(mq['source'])/'request.json')
    region = bound(Path(pose['source'])/'request.json'); donor = bound(Path(region['source'])/'request.json')
    baseline = Path(pose['baseline']); br = bound(baseline/'result.json')
    trial = next(t for t in bound(baseline/'trials.json') if t['folder'] == br['selected'])
    prepared, actors = load_actors(region['prepared']); target = sq['target']; contact = sq['selected_contact']
    for key in ('effector', 'target'): contact[key] = rebind_surface_point(contact[key], contact[key]['surface_vertex'])
    contact['tolerance_m'] = target['maximum_gap_m']
    event = sq['event_time_s']; window = sq['window_s']; protected = sq['protected_spans']
    guard, uniform = np.asarray(sq['guard_times_s']), np.asarray(sq['uniform_times_s'])
    rigs = []; refs = []; readers = []; ref_readers = []
    for i, entry in enumerate(trial['actors']):
        path = source/f'candidate-{i}.glb'; reference = baseline/br['selected']/entry['path']
        for p in (path, reference):
            if files.get(str(p)) != sha256(p): raise ValueError('Unbound rig or original reference')
        rigs.append(RigAsset.load(path)); refs.append(RigAsset.load(reference))
        readers.append(AnimationSampler(rigs[-1].document, rigs[-1].binary, 0)); ref_readers.append(AnimationSampler(refs[-1].document, refs[-1].binary, 0))
    plane_times = list(guard)
    for actor_index, reader in enumerate(readers):
        for node, kind, clock, values, mode in reader.channels:
            if node == donor['actors'][actor_index]['nodes'][0] and kind == 'rotation':
                for a, b in zip(clock[:-1], clock[1:]):
                    plane_times.extend(float(a)+(float(b)-float(a))*f for f in (0., .25, .5, .75, 1.) if window[0] <= float(a)+(float(b)-float(a))*f <= window[1])
    plane_times = np.unique(plane_times)
    full = np.unique(np.r_[plane_times, guard, uniform, event, window, 0., [r.duration for r in readers]])
    plane_frames = np.searchsorted(full, plane_times)
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(sq['implementation']) | {'native_wrist_retraction.py', 'study_native_wrist_retraction.py'}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        target=target, selected_contact=contact, event_time_s=event, window_s=window, protected_spans=protected,
        guard_times_s=guard.tolist(), uniform_times_s=uniform.tolist(), original_bins_s=sq['original_bins_s'],
        plane_times_s=plane_times.tolist(), maximum_extra_retraction_m=.02, reserve_m=.0001, maximum_iterations=8,
        policy='Freeze both native keys around contact. At editable common arm key times, retract wrist up to 20 mm further along the fixed normal, preserving native-key wrist orientation and original 45 degree arm budgets. Refresh float32-serialized interpolated skin, distribute corrections to influencing keys, backtrack reach/budget failures or nondecreasing plane violation. Include original guard times and quarter native intervals. Frozen plane residuals stay explicit; audit full meshes, contact, floor and original rates independently.',
        quality_approved=False))
    decoded = []; clips = []; repairs = []
    for i, (rig, ref, reader) in enumerate(zip(rigs, refs, readers)):
        nodes = donor['actors'][i]['nodes'][:3]
        direction = -actors[i]['rotation'].T@np.asarray(target['normals'][i])
        edit = NativeWristRetraction(rig.document, rig.binary, [rig.document['nodes'][n]['name'] for n in nodes], full, window, protected, event, (ref.document, ref.binary), direction)
        skin = BoundSkin(rig); vertices = np.asarray(region['region_vertices'][i]); actor = actors[i]
        midpoint = np.asarray(target['midpoint_m']); outward = np.asarray(target['normals'][i]); clearance = target['separation_m']/2
        def evaluate(amounts):
            world = edit.world(amounts); excess = []
            for frame in plane_frames:
                points = skin.evaluate(world, np.full(len(vertices), frame), vertices)@actor['rotation'].T+actor['translation']
                excess.append(float(((points-midpoint)@outward).max()+clearance))
            return np.asarray(excess)
        amounts, report = repair(evaluate, edit.influence[plane_frames])
        report.update(actor=i, native_key_ids=edit.ids.tolist(), native_key_times_s=edit.clock[edit.ids].tolist(), retractions_m=amounts.tolist())
        repairs.append(report); save(output/f'actor-{i}-repair.json', report)
        print(dict(phase='native_retraction', actor=i, active_plane_pass=report['active_plane_pass'], maximum_m=report['maximum_retraction_m']), flush=True)
        path = output/f'candidate-{i}.glb'; edit.export(amounts, path)
        asset = RigAsset.load(path); current = AnimationSampler(asset.document, asset.binary, 0)
        world = np.array([current.sample(t) for t in full]); before = np.array([reader.sample(t) for t in full])
        frozen = (full <= window[0]) | (full >= window[1])
        for a, b in protected: frozen |= (full >= a) & (full <= b)
        np.testing.assert_array_equal(world[frozen], before[frozen])
        event_index = int(np.searchsorted(full, event)); error = float(np.max(np.abs(world[event_index]-before[event_index])))
        np.testing.assert_array_equal(world[event_index], before[event_index])
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
        print(dict(phase='native_retraction_geometry', completed=index+1, total=len(guard), passed=bool(passed)), flush=True)
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
        active_planes_pass=all(r['active_plane_pass'] for r in repairs), all_planes_pass=all(r['all_planes_pass'] for r in repairs),
        contact_pose_preserved_exact=True,
        continuous_collision_certified=False, selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output)
