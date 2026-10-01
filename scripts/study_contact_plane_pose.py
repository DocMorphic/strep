"""Fit the authored palm pose against complete selected hand surfaces."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.optimize import least_squares
from strep import ROOT, read, save, sha256, now


def run(source, output, optimizer="least_squares_box"):
    if optimizer not in ("least_squares_box", "slsqp_box", "slsqp_ball"):
        raise ValueError("Explicit supported contact-pose optimizer required")
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from timed_rotation_edit import TimedRotationEdit
    from paired_approach_basis import BoundSkin
    from native_finger_motion import palm_geometry
    from hand_contact_plane import hand_region, plane_excess, measure as plane_measure
    from shared_palm_meeting import measure as contact_measure
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh contact-plane study required')
    result, request = read(source/'result.json'), read(source/'request.json')
    if result['status'] != 'complete' or not result['new_authored_condition']:
        raise ValueError('Completed explicitly authored contact source required')
    files = dict(request['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in result['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Source output path escaped')
        files[str(path)] = digest
    for name, digest in request['implementation'].items():
        files[str(source/'implementation'/name)] = digest
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Source implementation changed')
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Source evidence changed: '+path)
    def bound(path):
        path = Path(path).resolve()
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound source: '+str(path))
        return read(path)
    prior = bound(Path(request['source'])/'request.json')
    wr = bound(Path(prior['window_audit'])/'request.json')
    fr = bound(Path(wr['study'])/'request.json')
    donor = bound(Path(fr['donor'])/'request.json')
    anchor = bound(Path(donor['study'])/'request.json')
    terminal = bound(Path(anchor['study'])/'request.json')
    plan = bound(Path(terminal['plan'])/'request.json')
    protocol = bound(Path(plan['source_plan'])/'request.json')
    baseline = Path(protocol['study']); br = bound(baseline/'result.json')
    original = bound(baseline/'request.json')
    prepared_folder = Path(original['prepared_request']).parent
    prepared, actors = load_actors(prepared_folder)
    scene = bound(prepared_folder/prepared['scene_snapshot']['path'])['scene']
    contact = next(c for c in scene['contacts'] if c['id'] == request['replaced_contact_id'])
    trial = next(v for v in bound(baseline/'trials.json') if v['folder'] == br['selected'])
    event = request['event_time_s']; window = request['window_s']; spec = request['target']
    midpoint = np.asarray(spec['midpoint_m']); axis = np.asarray(spec['normals'][0])
    uniform = np.asarray(fr['uniform_times_s']); protected = request['remaining_protected_spans']
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    extras = {'hand_contact_plane.py', 'study_contact_plane_pose.py'}
    if optimizer != 'least_squares_box': extras.add('joint_ball_least_squares.py')
    for name in sorted(set(request['implementation']) | extras):
        methods[name] = sha256(ROOT/'scripts'/name)
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    rigs = []; references = []; models = []; regions = []; patches = []; skins = []; scales = []
    layouts = []
    for i, (actor, entry) in enumerate(zip(actors, trial['actors'])):
        path = source/f'authored-meeting-{i}.glb'; reference = baseline/br['selected']/entry['path']
        if files.get(str(path)) != sha256(path) or files.get(str(reference)) != sha256(reference):
            raise ValueError('Bound source and original reference required')
        rig = RigAsset.load(path); ref = RigAsset.load(reference)
        rigs.append(rig); references.append(ref); skins.append(BoundSkin(rig))
        item = contact['effector'] if i == 0 else contact['target']
        lookup = {n.get('name'): n for n in rig.document['nodes']}
        hand = item['joint']; fingers = [hand+finger+str(joint) for finger in ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
            for joint in range(1, 4 if finger == 'Thumb' else 5)]
        if any(name not in lookup for name in fingers): raise ValueError('Mapped finger joints required')
        names = [rig.document['nodes'][n]['name'] for n in protocol['chains'][actor['name']]]+fingers
        model = TimedRotationEdit(rig.document, rig.binary, names, [window[0], event, window[1]], window,
            protected, knots=[window[0], event, window[1]], limit_degrees=45., reference=(ref.document, ref.binary))
        budgets = [45.]*3+[8. if n == hand+'Thumb1' else (5. if n.endswith('1') else 12.) for n in fingers]
        extra = []
        for j, (row, budget) in enumerate(zip(model.entries, budgets)):
            used = float(np.rad2deg(np.linalg.norm(row['relative'], axis=1)).max())
            remaining = min(15. if j < 3 else budget, budget-used)
            if remaining <= 1e-6: raise ValueError('No conservative original edit headroom')
            extra.append(remaining)
        scale = np.repeat(np.deg2rad(extra)/(np.sqrt(3) if optimizer == 'least_squares_box' else 1.), 3)
        primitive = rig.primitives[0]; nodes = np.asarray(rig.joints)[primitive['joints']]
        hand_node = next(n for n in rig.joints if rig.document['nodes'][n]['name'] == hand)
        ids, face_ids = hand_region(rig.parents, hand_node, nodes, primitive['weights'], actor['faces'])
        faces = actor['faces'][np.any(actor['faces'] == item['surface_vertex'], axis=1)]
        patch_ids, remap = np.unique(faces, return_inverse=True)
        patches.append((patch_ids, remap.reshape(-1, 3), int(np.flatnonzero(patch_ids == item['surface_vertex'])[0])))
        regions.append(ids); models.append(model); scales.append(scale)
        layouts.append(dict(nodes=model.nodes, original_budgets_degrees=budgets,
            additional_control_limits_degrees=extra, vertices=ids.tolist(), triangles=face_ids.tolist()))
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        target=spec, event_time_s=event, window_s=window, actors=layouts, optimizer=optimizer,
        max_nfev_per_actor=80 if optimizer == 'least_squares_box' else None,
        max_iterations_per_actor=80 if optimizer != 'least_squares_box' else None,
        policy='Fixed meeting plane is a conservative proposal surrogate. Original arm/finger budgets retained. Contact-pose full mesh and full-window original motion caps audited separately. No motion or collision acceptance inferred from least squares.',
        diagnostic_only=True, quality_approved=False))
    def geometry(i, world, frame=1):
        a, skin = actors[i], skins[i]
        ids, faces, center = patches[i]
        points = skin.evaluate(world, np.full(len(ids), frame), ids)@a['rotation'].T+a['translation']
        c, n = palm_geometry(points, faces, center)
        ids = regions[i]
        points = skin.evaluate(world, np.full(len(ids), frame), ids)@a['rotation'].T+a['translation']
        return c, n, points
    controls = []; fits = []
    for i, model in enumerate(models):
        calls = [0]
        def residual(x):
            center, normal, points = geometry(i, model.world(x*scales[i]))
            calls[0] += 1
            if calls[0] % 1000 == 0:
                print(dict(phase='plane_pose_fit', actor=i, residual_calls=calls[0]), flush=True)
            return np.r_[(center-spec['centers_m'][i])/1e-5, (normal-spec['normals'][i])/.05,
                np.maximum(plane_excess(points, midpoint, axis, i), 0)/.001, x*.001*(1. if optimizer == 'least_squares_box' else np.sqrt(3))]
        initial = geometry(i, model.source_world)
        if optimizer == 'least_squares_box':
            fit = least_squares(residual, np.zeros(model.size), bounds=(-1., 1.), max_nfev=80,
                ftol=1e-9, xtol=1e-9, gtol=1e-9)
            point = fit.x
            fit_record = dict(success=bool(fit.success), message=fit.message, nfev=int(fit.nfev), cost=float(fit.cost))
        else:
            from joint_ball_least_squares import solve
            def observe(row):
                if row['iteration'] % 10 == 0:
                    print(dict(phase='joint_constraint_fit', actor=i, **row), flush=True)
            point, solver_record = solve(residual, np.zeros(model.size), ball=optimizer == 'slsqp_ball',
                iterations=80, observe=observe)
            save(output/f'solver-{i}.json', solver_record)
            fit_record = dict(success=solver_record['optimizer_success'], message=solver_record['message'],
                iterations=solver_record['iterations'], cost=solver_record['final_cost'])
        controls.append(point*scales[i]); final = geometry(i, model.world(controls[-1]))
        fits.append(dict(actor=i, **fit_record, residual_calls=calls[0], controls_radians=controls[-1].tolist(),
            initial_plane=plane_measure(initial[2], midpoint, axis, i),
            unrounded_plane=plane_measure(final[2], midpoint, axis, i)))
        save(output/'fits.json', fits)
        print(dict(phase='plane_pose_actor_complete', actor=i, **fit_record), flush=True)
    full = np.unique(np.r_[uniform, window, event, 0., [AnimationSampler(r.document, r.binary, 0).duration for r in rigs]])
    worlds = []; centers = []; normals = []; decoded_planes = []; positions = []; exports = []
    for i, (rig, ref, model, values) in enumerate(zip(rigs, references, models, controls)):
        path = output/f'plane-pose-{i}.glb'; model.export(values, path)
        candidate = RigAsset.load(path); sampler = AnimationSampler(candidate.document, candidate.binary, 0)
        original_sampler = AnimationSampler(rig.document, rig.binary, 0)
        world = np.array([sampler.sample(t) for t in full]); worlds.append(world)
        for a, b in zip(original_sampler.channels, sampler.channels):
            assert a[:2] == b[:2] and a[4] == b[4]
            np.testing.assert_array_equal(a[2], b[2])
            if a[1] != 'rotation' or a[0] not in model.nodes: np.testing.assert_array_equal(a[3], b[3])
        assert len(original_sampler.channels) == len(sampler.channels)
        outside = (full <= window[0]) | (full >= window[1])
        np.testing.assert_array_equal(world[outside], np.array([original_sampler.sample(t) for t in full[outside]]))
        # Independently check the stricter per-finger budgets on exported keys.
        from paired_temporal_neighbor import rotation_channels
        from scipy.spatial.transform import Rotation
        channels = rotation_channels(candidate.document, candidate.binary)
        maximum = []
        for entry, budget in zip(model.entries, layouts[i]['original_budgets_degrees']):
            angle = float(np.rad2deg((Rotation.from_quat(entry['original']).inv()*Rotation.from_quat(channels[entry['node']][2])).magnitude()).max())
            if angle > budget+1e-4: raise ValueError('Original per-joint export budget exceeded')
            maximum.append(angle)
        frame = int(np.searchsorted(full, event)); center, normal, points = geometry(i, world, frame)
        centers.append(center); normals.append(normal); decoded_planes.append(plane_measure(points, midpoint, axis, i))
        positions.append(candidate.vertices(world[frame])@actors[i]['rotation'].T+actors[i]['translation'])
        exports.append(dict(path=path.name, sha256=sha256(path), maximum_edits_degrees=maximum,
            native_clocks_root_unselected_channels_and_outside_window_exact=True))
    def payload(values):
        parts = [features(v, r.joints) for v, r in zip(values, references)]
        return {k: np.concatenate([p[k] for p in parts], axis=1) for k in ['positions', 'rotations']}
    raw = []
    for ref in references:
        sampler = AnimationSampler(ref.document, ref.binary, 0)
        raw.append(np.array([sampler.sample(t) for t in uniform]))
    caps = SampledMotionCaps(payload(raw), uniform, fr['original_bins_s'])
    selected = np.searchsorted(full, uniform); actual = payload([w[selected] for w in worlds])
    rates = []
    for kind, values, ceiling in zip(['position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'], measures(actual, caps.dt), caps.caps):
        excess = values-ceiling-caps.tolerance
        rates.append(dict(kind=kind, failed_rows=int(np.count_nonzero(excess > 0)), maximum_excess=float(excess.max())))
    decoded_contact = contact_measure(centers, normals, spec)
    save(output/'decoded.json', dict(exports=exports, contact=decoded_contact, planes=decoded_planes, motion_rates=rates))
    print(dict(phase='full_contact_geometry'), flush=True)
    surface = audit(positions[0], actors[0]['faces'], positions[1], actors[1]['faces'])
    depths = [penetration(positions[a], positions[b], actors[b]['faces']) for a, b in [(0, 1), (1, 0)]]
    save(output/'contact-geometry.json', dict(time_s=event, surface=surface, depths=depths))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Source changed during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during study')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        contact_target_pass=decoded_contact['contact_target_pass'], original_motion_caps_pass=all(v['failed_rows'] == 0 for v in rates),
        selected_hand_plane_pass=all(v['selected_surface_plane_pass'] for v in decoded_planes),
        contact_proper_crossings=surface['counts'].get('proper_crossing', 0),
        contact_maximum_vertex_depth_m=max(v['max_depth_m'] for v in depths), full_interval_geometry_audited=False,
        diagnostic_only=True, selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--optimizer', choices=['least_squares_box', 'slsqp_box', 'slsqp_ball'], default='least_squares_box')
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output, args.optimizer)
