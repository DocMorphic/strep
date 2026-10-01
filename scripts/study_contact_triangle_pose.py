"""Coupled, refreshed triangle witnesses with unchanged authored palm targets."""
import argparse
from pathlib import Path
import shutil
from functools import lru_cache
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(source, output, with_vertices=False):
    if type(with_vertices) is not bool: raise ValueError("Explicit vertex-witness mode required")
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from timed_rotation_edit import TimedRotationEdit, sampled_rotations
    from paired_guarded_temporal import world_from_local
    from paired_approach_basis import BoundSkin
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import measure
    from coupled_contact_proposal import solve, contact_margins
    from triangle_separation_objective import choose_axes, TriangleSeparationObjective
    from triangle_crossing import audit
    if with_vertices:
        from vertex_exit_witnesses import extract as extract_vertices, VertexExitObjective
    from convex_partner_surface import penetration
    from sampled_surface_guard import topology, snapshot, compare
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from paired_temporal_neighbor import rotation_channels
    from scipy.spatial.transform import Rotation
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh coupled triangle study required')
    result, request = read(source/'result.json'), read(source/'request.json')
    if result['status'] != 'complete' or request['optimizer'] != 'slsqp_ball' or not result['contact_target_pass']:
        raise ValueError('Completed joint-ball donor with valid authored contact required')
    files = dict(request['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in result['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Escaping source output')
        files[str(path)] = digest
    for name, digest in request['implementation'].items():
        files[str(source/'implementation'/name)] = digest
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Source implementation changed')
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed source evidence')
    def bound(path):
        path = Path(path).resolve()
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound source: '+str(path))
        return read(path)
    shared = Path(request['source']); sr = bound(shared/'request.json')
    prior = bound(Path(sr['source'])/'request.json')
    wr = bound(Path(prior['window_audit'])/'request.json'); fr = bound(Path(wr['study'])/'request.json')
    donor = bound(Path(fr['donor'])/'request.json'); anchor = bound(Path(donor['study'])/'request.json')
    terminal = bound(Path(anchor['study'])/'request.json'); plan = bound(Path(terminal['plan'])/'request.json')
    protocol = bound(Path(plan['source_plan'])/'request.json'); baseline = Path(protocol['study'])
    br = bound(baseline/'result.json'); original = bound(baseline/'request.json')
    folder = Path(original['prepared_request']).parent; prepared, actors = load_actors(folder)
    scene = bound(folder/prepared['scene_snapshot']['path'])['scene']
    contact = next(c for c in scene['contacts'] if c['id'] == sr['replaced_contact_id'])
    trial = next(v for v in bound(baseline/'trials.json') if v['folder'] == br['selected'])
    window = request['window_s']; event = request['event_time_s']; target = request['target']
    rigs = []; refs = []; models = []; skins = []; patches = []; scales = []; starts = []
    for i, (actor, entry, layout, fit) in enumerate(zip(actors, trial['actors'], request['actors'], bound(source/'fits.json'))):
        path = shared/f'authored-meeting-{i}.glb'; reference = baseline/br['selected']/entry['path']
        if files.get(str(path)) != sha256(path) or files.get(str(reference)) != sha256(reference):
            raise ValueError('Bound original clips required')
        rig = RigAsset.load(path); ref = RigAsset.load(reference); rigs.append(rig); refs.append(ref); skins.append(BoundSkin(rig))
        names = [rig.document['nodes'][n]['name'] for n in layout['nodes']]
        model = TimedRotationEdit(rig.document, rig.binary, names, [window[0], event, window[1]], window,
            sr['remaining_protected_spans'], knots=[window[0], event, window[1]], limit_degrees=45., reference=(ref.document, ref.binary))
        scale = np.repeat(np.deg2rad(layout['additional_control_limits_degrees']), 3)
        if model.size != len(scale): raise ValueError('Original control population changed')
        models.append(model); scales.append(scale); starts.append(np.asarray(fit['controls_radians'])/scale)
        item = contact['effector'] if i == 0 else contact['target']
        faces = actor['faces'][np.any(actor['faces'] == item['surface_vertex'], axis=1)]
        ids, remap = np.unique(faces, return_inverse=True)
        patches.append((ids, remap.reshape(-1, 3), int(np.flatnonzero(ids == item['surface_vertex'])[0])))
    width = models[0].size; point = np.concatenate(starts); initial = point.copy()
    @lru_cache(maxsize=8)
    def cached_worlds(key, quantized):
        values = np.frombuffer(key, dtype=float); result = []
        for model, scale, value in zip(models, scales, np.split(values, [width])):
            if not quantized:
                result.append(model.world(value*scale)); continue
            local = model.local.copy(); q = model.quaternions(value*scale, quantize=True)
            for entry in model.entries:
                node = entry['node']
                local[:, node, :3, :3] = sampled_rotations(entry['clock'], q[node], model.times)*model.scales[node][:, None, :]
            result.append(world_from_local(local, model.parents))
        return result
    def worlds(x, quantized=False): return cached_worlds(np.asarray(x, float).tobytes(), quantized)
    def palms(values):
        centers = []; normals = []
        for actor, skin, world, (ids, faces, center) in zip(actors, skins, values, patches):
            p = skin.evaluate(world, np.ones(len(ids), int), ids)@actor['rotation'].T+actor['translation']
            c, n = palm_geometry(p, faces, center); centers.append(c); normals.append(n)
        return np.asarray(centers), np.asarray(normals)
    for i, world in enumerate(worlds(point, True)):
        path = source/f'plane-pose-{i}.glb'; rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
        np.testing.assert_allclose(world, [sampler.sample(t) for t in models[i].times], rtol=0, atol=2e-10)
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    extras = {'coupled_contact_proposal.py', 'study_contact_triangle_pose.py'}
    if with_vertices: extras.add('vertex_exit_witnesses.py')
    for name in sorted(set(request['implementation']) | extras):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        target=target, event_time_s=event, window_s=window, actors=request['actors'], initial_controls=point.tolist(),
        rounds=2, solver_iterations_per_round=40, proposal_clearance_m=1e-8, vertex_witnesses_enabled=with_vertices,
        internal_selection='Authored contact and joint limits pass after serialization; no directional maximum-depth increase beyond 1e-8 m, no crossing-count increase or new uncertain/degenerate outcomes, and a strict depth/count improvement. This is internal search, not mesh-regression or animation approval.',
        full_interval_geometry_audited=False, quality_approved=False))
    mesh_topology = topology([a['faces'] for a in actors], [len(r.vertices(r.reference)) for r in rigs])
    def audit_worlds(value):
        positions = [r.vertices(w[1])@a['rotation'].T+a['translation'] for r, w, a in zip(rigs, value, actors)]
        observation = dict(time_s=event, contact=measure(*palms(value), target),
            surface=audit(positions[0], actors[0]['faces'], positions[1], actors[1]['faces']),
            depths=[penetration(positions[a], positions[b], actors[b]['faces']) for a, b in [(0, 1), (1, 0)]])
        return observation, positions
    def audit_point(x): return audit_worlds(worlds(x, True))
    current, positions = audit_point(point); original_observation = current
    save(output/'geometry-initial.json', current); history = []
    for iteration in range(2):
        pairs = [v for v in current['surface']['records'] if v['kind'] in ('proper_crossing', 'coplanar_or_near_parallel_overlap')]
        vertex_data = [extract_vertices(positions[a], positions[b], actors[b]['faces']) for a, b in [(0, 1), (1, 0)]] if with_vertices else []
        if not pairs and not any(v['witnesses'] for v in vertex_data): break
        vertices = np.array([[a['faces'][r['left_triangle' if i == 0 else 'right_triangle']] for r in pairs] for i, a in enumerate(actors)]).reshape(2, -1, 3)
        axes = choose_axes(positions[0][vertices[0]], positions[1][vertices[1]]) if pairs else np.empty((0, 3))
        objective = TriangleSeparationObjective(skins, actors, np.ones(len(pairs), int), vertices, axes, clearance_m=1e-8) if pairs else None
        vertex_objective = VertexExitObjective(skins, actors, [v['witnesses'] for v in vertex_data]) if with_vertices else None
        save(output/f'witnesses-{iteration}.json', dict(pairs=pairs, vertices=vertices.tolist(), axes=axes.tolist(), vertex_directions=vertex_data))
        def residual(x, quantized=False):
            value = worlds(x, quantized)
            triangle_rows = np.maximum(objective.depths(value), 0)/.001 if objective is not None else np.empty(0)
            vertex_rows = np.maximum(vertex_objective.depths(value), 0)/.001 if vertex_objective is not None else np.empty(0)
            return np.r_[triangle_rows, vertex_rows, x*.001*np.sqrt(3)]
        def hard(x, quantized=False): return contact_margins(*palms(worlds(x, quantized)), target)
        def observe(row):
            if row['iteration'] % 10 == 0:
                print(dict(phase='coupled_triangle_proposal', round=iteration, iteration=row['iteration'], cost=row['best_cost']), flush=True)
        proposal, solver = solve(residual, hard, point, replay_residual=lambda x: residual(x, True),
            replay_hard=lambda x: hard(x, True), iterations=40, observe=observe)
        save(output/f'solver-{iteration}.json', dict(**solver, final_controls=proposal.tolist()))
        record = dict(round=iteration, witnesses=len(pairs), vertex_witnesses=sum(len(v['witnesses']) for v in vertex_data), accepted=False, trials=[])
        for trial_id, fraction in enumerate([1., .5, .25, .125]):
            candidate = point+fraction*(proposal-point)
            if np.any(hard(candidate, True) < 0):
                record['trials'].append(dict(fraction=fraction, contact_pass=False)); continue
            observed, proposed_positions = audit_point(candidate)
            save(output/f'geometry-{iteration}-{trial_id}.json', observed)
            counts = [o['surface']['counts'].get('proper_crossing', 0) for o in [current, observed]]
            depths = np.array([[d['max_depth_m'] for d in o['depths']] for o in [current, observed]])
            regression = compare(snapshot(mesh_topology, [current]), snapshot(mesh_topology, [observed]))
            uncertain_ok = not any(s['new_uncertain_pairs'] or any(s['new_degenerate_faces']) for s in regression['samples'])
            accepted = (observed['contact']['contact_target_pass'] and uncertain_ok and counts[1] <= counts[0]
                and np.all(depths[1] <= depths[0]+1e-8) and (counts[1] < counts[0] or np.any(depths[1] < depths[0]-1e-8)))
            record['trials'].append(dict(fraction=fraction, contact_pass=observed['contact']['contact_target_pass'],
                proper_counts=counts, directional_depths_m=depths.tolist(), mesh_regression=regression, retained_internally=bool(accepted)))
            print(dict(phase='coupled_triangle_geometry', round=iteration, fraction=fraction, accepted=bool(accepted),
                crossings=counts[1], maximum_depth_m=float(depths[1].max())), flush=True)
            if accepted:
                point, current, positions = candidate.copy(), observed, proposed_positions
                record['accepted'] = True; break
        history.append(record); save(output/'history.json', history)
        if not record['accepted']: break
    uniform = np.asarray(fr['uniform_times_s']); full = np.unique(np.r_[uniform, window, event, 0.,
        [AnimationSampler(r.document, r.binary, 0).duration for r in rigs]])
    decoded = []; exports = []
    for i, (rig, model, scale, x) in enumerate(zip(rigs, models, scales, np.split(point, [width]))):
        path = output/f'candidate-{i}.glb'
        if np.array_equal(point, initial): shutil.copyfile(source/f'plane-pose-{i}.glb', path)
        else: model.export(x*scale, path)
        asset = RigAsset.load(path); sampler = AnimationSampler(asset.document, asset.binary, 0)
        before = AnimationSampler(rig.document, rig.binary, 0); world = np.array([sampler.sample(t) for t in full]); decoded.append(world)
        assert len(before.channels) == len(sampler.channels)
        for a, b in zip(before.channels, sampler.channels):
            assert a[:2] == b[:2] and a[4] == b[4]; np.testing.assert_array_equal(a[2], b[2])
            if a[1] != 'rotation' or a[0] not in model.nodes: np.testing.assert_array_equal(a[3], b[3])
        outside = (full <= window[0]) | (full >= window[1])
        np.testing.assert_array_equal(world[outside], [before.sample(t) for t in full[outside]])
        np.testing.assert_allclose(world[np.searchsorted(full, model.times)], worlds(point, True)[i], rtol=0, atol=2e-10)
        channels = rotation_channels(asset.document, asset.binary); angles = []
        for entry, budget in zip(model.entries, request['actors'][i]['original_budgets_degrees']):
            angle = float(np.rad2deg((Rotation.from_quat(entry['original']).inv()*Rotation.from_quat(channels[entry['node']][2])).magnitude()).max())
            if angle > budget+1e-4: raise ValueError('Original joint edit budget exceeded after export')
            angles.append(angle)
        exports.append(dict(path=path.name, sha256=sha256(path), original_edit_angles_degrees=angles,
            native_clocks_unselected_channels_outside_window_exact=True))
    def payload(values):
        parts = [features(v, r.joints) for v, r in zip(values, refs)]
        return {k: np.concatenate([p[k] for p in parts], axis=1) for k in ['positions', 'rotations']}
    raw = []
    for ref in refs:
        sampler = AnimationSampler(ref.document, ref.binary, 0); raw.append(np.array([sampler.sample(t) for t in uniform]))
    caps = SampledMotionCaps(payload(raw), uniform, fr['original_bins_s'])
    actual = payload([w[np.searchsorted(full, uniform)] for w in decoded]); rates = []
    for kind, value, ceiling in zip(['position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'], measures(actual, caps.dt), caps.caps):
        excess = value-ceiling-caps.tolerance; rates.append(dict(kind=kind, failed_rows=int(np.count_nonzero(excess > 0)), maximum_excess=float(excess.max())))
    event_index = int(np.searchsorted(full, event))
    current, _ = audit_worlds([w[[0, event_index, len(full)-1]] for w in decoded])
    if not current['contact']['contact_target_pass']: raise ValueError('Independent export lost hard contact')
    save(output/'geometry-decoded-final.json', current)
    save(output/'decoded.json', dict(exports=exports, motion_rates=rates, contact=current['contact']))
    final_guard = compare(snapshot(mesh_topology, [original_observation]), snapshot(mesh_topology, [current]))
    save(output/'final-mesh-comparison.json', final_guard)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Input changed during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during study')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        internal_steps=sum(r['accepted'] for r in history), contact_target_pass=current['contact']['contact_target_pass'],
        contact_proper_crossings=current['surface']['counts'].get('proper_crossing', 0),
        contact_maximum_vertex_depth_m=max(d['max_depth_m'] for d in current['depths']),
        original_motion_caps_pass=all(r['failed_rows'] == 0 for r in rates), contact_mesh_regression_pass=final_guard['passed'],
        full_interval_geometry_audited=False, selected_for_studio=False, diagnostic_only=True, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--with-vertices', action='store_true')
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output, args.with_vertices)
