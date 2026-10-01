"""Native-key fit of a valid region contact pose, followed by interval audits."""
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
    from timed_rotation_edit import TimedRotationEdit, sampled_rotations
    from joint_ball_least_squares import solve
    from elbow_swivel import local_transforms
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import measure
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from paired_temporal_neighbor import rotation_channels
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh native region motion study required')
    sr, sq = read(source/'result.json'), read(source/'request.json')
    if not (sr['status'] == 'complete' and sr['inter_actor_pose_screen_pass'] and sr['original_pose_limits_pass'] and sr['contact']['contact_target_pass']):
        raise ValueError('Completed valid region rig pose required')
    files = dict(sq['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in sr['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Escaping source output')
        files[str(path)] = digest
    for name, digest in sq['implementation'].items():
        path = (source/'implementation'/name).resolve()
        if path.parent != source/'implementation': raise ValueError('Escaping source method')
        files[str(path)] = digest
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed bound evidence')
    def bound(path):
        path = Path(path)
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound evidence: '+str(path))
        return read(path)
    region = bound(Path(sq['source'])/'request.json'); donor = Path(region['source']); dq = bound(donor/'request.json')
    ball = bound(Path(dq['source'])/'request.json'); shared = bound(Path(ball['source'])/'request.json')
    prior = bound(Path(shared['source'])/'request.json'); window_study = bound(Path(prior['window_audit'])/'request.json')
    fr = bound(Path(window_study['study'])/'request.json')
    baseline = Path(sq['baseline']); br = bound(baseline/'result.json')
    trial = next(t for t in bound(baseline/'trials.json') if t['folder'] == br['selected'])
    prepared, actors = load_actors(region['prepared']); target = sq['target']; contact = sq['selected_contact']
    event = sq['event_time_s']; window = shared['window_s']; guard = np.asarray(shared['guard_times_s']); uniform = np.asarray(fr['uniform_times_s'])
    if event not in guard: raise ValueError('Original guard clock must include contact')
    pose = np.load(source/'pose.npz', allow_pickle=False)
    rigs = []; refs = []; samplers = []; originals = []
    for i, entry in enumerate(trial['actors']):
        path = donor/f'candidate-{i}.glb'; reference = baseline/br['selected']/entry['path']
        for p in (path, reference):
            if files.get(str(p)) != sha256(p): raise ValueError('Unbound rig source or reference')
        rigs.append(RigAsset.load(path)); refs.append(RigAsset.load(reference))
        samplers.append(AnimationSampler(rigs[-1].document, rigs[-1].binary, 0)); originals.append(AnimationSampler(refs[-1].document, refs[-1].binary, 0))
    full = np.unique(np.r_[uniform, guard, window, event, 0., [s.duration for s in samplers]])
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(sq['implementation']) | {'study_palm_region_motion.py'}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        target=target, selected_contact=contact, contact_regions=sq['contact_regions'], event_time_s=event, window_s=window,
        guard_times_s=guard.tolist(), uniform_times_s=uniform.tolist(), original_bins_s=fr['original_bins_s'],
        policy='Fit only the three arm rotation channels to the validated contact pose using a native triangular edit envelope. Per-joint correction ball is the remaining 45-degree original-reference allowance across all native keys. Other channels stay fixed. Recheck decoded original joint budgets, exact native clocks/protected regions, full-mesh guard samples, floor and original motion caps. Single-pose success never approves the trajectory.',
        new_authored_condition=True, quality_approved=False))
    decoded = []; clips = []; fits = []
    for i, (rig, ref, sampler) in enumerate(zip(rigs, refs, samplers)):
        layout = dq['actors'][i]; nodes = layout['nodes'][:3]
        model = TimedRotationEdit(rig.document, rig.binary, [rig.document['nodes'][n]['name'] for n in nodes],
            [window[0], event, window[1]], window, shared['remaining_protected_spans'], knots=[window[0], event, window[1]],
            limit_degrees=45., reference=(ref.document, ref.binary))
        remaining = np.array([45.-np.rad2deg(np.linalg.norm(e['relative'], axis=1)).max() for e in model.entries])
        if np.any(remaining <= 0): raise ValueError('No original-reference arm headroom')
        scale = np.repeat(np.deg2rad(remaining), 3); desired = local_transforms(pose[f'actor{i}'], rig.parents)[nodes, :3, :3]
        def residual(x):
            q = model.quaternions(x*scale)
            actual = np.array([sampled_rotations(e['clock'], q[e['node']], np.array([event]))[0] for e in model.entries])
            return np.r_[Rotation.from_matrix(desired.transpose(0, 2, 1)@actual).as_rotvec().ravel()/.01, x*1e-5]
        point, fit = solve(residual, np.zeros(model.size), iterations=80)
        fits.append(dict(actor=i, remaining_original_budget_degrees=remaining.tolist(), controls_radians=(point*scale).tolist(), **fit))
        path = output/f'candidate-{i}.glb'; model.export(point*scale, path)
        asset = RigAsset.load(path); reader = AnimationSampler(asset.document, asset.binary, 0)
        world = np.array([reader.sample(t) for t in full]); before = np.array([sampler.sample(t) for t in full])
        outside = (full <= window[0]) | (full >= window[1]); np.testing.assert_array_equal(world[outside], before[outside])
        for first, last in shared['remaining_protected_spans']:
            mask = (full >= first) & (full <= last); np.testing.assert_array_equal(world[mask], before[mask])
        assert len(reader.channels) == len(sampler.channels)
        for a, b in zip(reader.channels, sampler.channels):
            assert a[:2] == b[:2] and a[4] == b[4]; np.testing.assert_array_equal(a[2], b[2])
            if a[1] != 'rotation' or a[0] not in nodes: np.testing.assert_array_equal(a[3], b[3])
        original_channels, channels = rotation_channels(ref.document, ref.binary), rotation_channels(asset.document, asset.binary)
        angles = []
        for node, budget in zip(layout['nodes'], layout['original_budgets_degrees']):
            angle = float(np.rad2deg((Rotation.from_quat(original_channels[node][2]).inv()*Rotation.from_quat(channels[node][2])).magnitude()).max())
            if angle > budget+1e-4: raise ValueError('Decoded native original edit budget exceeded')
            angles.append(angle)
        decoded.append(world); clips.append(dict(path=path.name, sha256=sha256(path), original_edit_angles_degrees=angles,
            native_clocks_unselected_channels_outside_window_protected_poses_exact=True))
        print(dict(phase='region_native_fit', actor=i, cost=fit['final_cost'], optimizer_success=fit['optimizer_success']), flush=True)
    save(output/'fits.json', fits)
    def payload(values):
        rows = [features(v, r.joints) for v, r in zip(values, refs)]
        return {k: np.concatenate([v[k] for v in rows], axis=1) for k in ('positions', 'rotations')}
    raw = [np.array([s.sample(t) for t in uniform]) for s in originals]
    caps = SampledMotionCaps(payload(raw), uniform, fr['original_bins_s']); actual = payload([w[np.searchsorted(full, uniform)] for w in decoded])
    rates = []
    for kind, values, ceiling in zip(('position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'), measures(actual, caps.dt), caps.caps):
        excess = values-ceiling-caps.tolerance; rates.append(dict(kind=kind, failed_rows=int(np.count_nonzero(excess > 0)), maximum_excess=float(excess.max())))
    observations = []; floor = []; contact_check = None
    for index, time in enumerate(guard):
        frame = int(np.searchsorted(full, time)); points = [r.vertices(w[frame])@a['rotation'].T+a['translation'] for r, w, a in zip(rigs, decoded, actors)]
        surface = audit(points[0], actors[0]['faces'], points[1], actors[1]['faces'])
        depths = [penetration(points[a], points[b], actors[b]['faces'], tolerance_m=1e-8) for a, b in [(0, 1), (1, 0)]]
        passed = not any(v for k, v in surface['counts'].items() if k != 'disjoint') and not any(surface['degenerate_faces']) and max(d['max_depth_m'] for d in depths) <= 1e-8
        row = dict(time_s=float(time), surface=surface, depths=depths, inter_actor_pose_screen_pass=bool(passed))
        if time == event:
            centers = []; normals = []
            for i, (p, a) in enumerate(zip(points, actors)):
                v = (contact['effector'] if i == 0 else contact['target'])['surface_vertex']; patch = a['faces'][np.any(a['faces'] == v, axis=1)]
                c, n = palm_geometry(p, patch, v); centers.append(c); normals.append(n)
            contact_check = measure(centers, normals, target); row['contact'] = contact_check
        observations.append(row); save(output/f'geometry-{index:02d}.json', row)
        before = [r.vertices(s.sample(time))@a['rotation'].T+a['translation'] for r, s, a in zip(rigs, samplers, actors)]
        floor.append(dict(time_s=float(time), source_m=[max(0., -float(p[:, 1].min())) for p in before], exported_m=[max(0., -float(p[:, 1].min())) for p in points]))
        print(dict(phase='region_motion_geometry', completed=index+1, total=len(guard), passed=bool(passed)), flush=True)
    save(output/'decoded.json', dict(clips=clips, contact=contact_check, motion_rates=rates)); save(output/'floor.json', floor)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed input during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Changed method during study')
    contact_geometry = next(v for v in observations if v['time_s'] == event)
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        contact_target_pass=contact_check['contact_target_pass'], contact_mesh_screen_pass=contact_geometry['inter_actor_pose_screen_pass'],
        guard_samples=len(guard), failed_geometry_samples=sum(not v['inter_actor_pose_screen_pass'] for v in observations),
        pair_time_crossings=sum(v['surface']['counts'].get('proper_crossing', 0) for v in observations),
        maximum_vertex_depth_m=max(d['max_depth_m'] for v in observations for d in v['depths']),
        original_motion_caps_pass=all(r['failed_rows'] == 0 for r in rates), native_animation_exported=True,
        full_interval_geometry_sampled=True, continuous_collision_certified=False, selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output)
