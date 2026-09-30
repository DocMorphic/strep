"""Native finger-only crossing repair with measured palm contact preservation."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(donor, output, iterations=3):
    from bound_evidence import bind_inputs
    from diagnose_oriented_hand_returns import load_evidence
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from native_finger_motion import NativeFingerMotion, palm_geometry
    from paired_approach_basis import BoundSkin
    from paired_temporal_neighbor import rotation_channels
    from continuous_terminal_hand import HandWitnessObjective
    from sampled_motion_caps import SampledMotionCaps, features
    from hand_norm_proposal import rate_vectors, measurement
    from hand_witness_envelope import limits
    from triangle_crossing import audit, classify
    from triangle_separation_objective import choose_axes, TriangleSeparationObjective
    from iterated_hand_norm import solve
    from conic_root_descent import solver_module
    from diagnose_terminal_hand_rates import explain
    donor, output = Path(donor).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh finger study required')
    if type(iterations) is not int or not 1 <= iterations <= 12: raise ValueError('One to twelve iterations required')
    result, donor_request = read(donor/'result.json'), read(donor/'request.json')
    if result['status'] != 'complete' or not result['full_clock_motion_pass']: raise ValueError('Motion-feasible completed donor required')
    files = bind_inputs({}, donor_request['inputs']); files[str(donor/'result.json')] = sha256(donor/'result.json')
    for name, digest in result['outputs'].items():
        path = (donor/name).resolve()
        if path.parent != donor or sha256(path) != digest: raise ValueError('Changed donor output')
        files[str(path)] = digest
    study = Path(donor_request['study']); request, evidence = load_evidence(study); files.update(evidence)
    terminal = read(Path(request['study'])/'request.json'); plan = read(Path(terminal['plan'])/'request.json')
    protocol = read(Path(plan['source_plan'])/'request.json'); baseline = Path(protocol['study'])
    original, _, required = load_bound_study(baseline); files.update(bind_inputs(required, request['inputs']))
    prepared_folder = Path(original['prepared_request']).parent; prepared, actors = load_actors(prepared_folder)
    scene = read(prepared_folder/prepared['scene_snapshot']['path'])['scene']
    protected = prepared['protected_seconds']
    if len(protected) != 1 or protected[0][0] != protected[0][1]: raise ValueError('One protected contact instant required')
    contact_time = float(protected[0][0]); window = prepared['authored']['window_s']
    contacts = [c for c in scene['contacts'] if c['id'] in prepared['authored']['protected_contact_ids']]
    if len(contacts) != 1 or contacts[0]['actor'] != actors[0]['name'] or contacts[0]['target']['actor'] != actors[1]['name']:
        raise ValueError('One matching two-palm contact required')
    contact = contacts[0]; times = np.asarray(terminal['sample_times_s'])
    checks_folder = ROOT/'reports/triangle-hand-repair-v1'
    check_result = read(checks_folder/'result.json')
    if check_result['status'] != 'complete': raise ValueError('Completed triangle witness study required')
    witness_path = checks_folder/'witnesses.json'
    if sha256(witness_path) != check_result['outputs']['witnesses.json']: raise ValueError('Witness times changed')
    files[str(checks_folder/'result.json')] = sha256(checks_folder/'result.json'); files[str(witness_path)] = sha256(witness_path)
    audit_times = np.unique(np.r_[[r['time_s'] for r in read(witness_path)], contact_time])
    combined = np.unique(np.r_[times, audit_times]); uniform_ids = np.searchsorted(combined, times); event = int(np.searchsorted(combined, contact_time))
    original_result = read(baseline/'result.json')
    if sha256(baseline/'trials.json') != original_result['trials_sha256']: raise ValueError('Original trials changed')
    trial = next(r for r in read(baseline/'trials.json') if r['folder'] == original_result['selected'])
    rigs = []; readers = []; models = []; reference = []; donor_worlds = []; input_paths = []; neighborhoods = []
    for index, (actor, original_entry, clip) in enumerate(zip(actors, trial['actors'], read(donor/'decoded.json')['clips'])):
        path = (baseline/original_result['selected']/original_entry['path']).resolve()
        if files.get(str(path)) != original_entry['sha256'] or sha256(path) != original_entry['sha256']: raise ValueError('Bound original motion required')
        source = RigAsset.load(path); sampler = AnimationSampler(source.document, source.binary, 0)
        reference.append(np.array([sampler.sample(t) for t in times]))
        path = (donor/clip['path']).resolve()
        if path.parent != donor or sha256(path) != clip['sha256']: raise ValueError('Bound donor GLB required')
        files[str(path)] = clip['sha256']; input_paths.append(path)
        rig = RigAsset.load(path); reader = AnimationSampler(rig.document, rig.binary, 0)
        rigs.append(rig); readers.append(reader); donor_worlds.append(np.array([reader.sample(t) for t in combined]))
        target = contact['effector'] if index == 0 else contact['target']; hand = target['joint']; lookup = {n.get('name'): i for i, n in enumerate(rig.document['nodes'])}
        names = [hand+finger+str(joint) for finger in ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'] for joint in range(1, 4 if finger == 'Thumb' else 5)]
        nodes = [lookup[name] for name in names]
        budgets = [8. if name == hand+'Thumb1' else (5. if name.endswith('1') else 12.) for name in names]
        models.append(NativeFingerMotion(rig, lookup[hand], nodes, budgets, combined, window, contact_time))
        vertex = target['surface_vertex']; faces = actor['faces'][np.any(actor['faces'] == vertex, axis=1)]
        ids, local_faces = np.unique(faces, return_inverse=True)
        neighborhoods.append(dict(ids=ids, faces=local_faces.reshape(-1, 3), center=int(np.flatnonzero(ids == vertex)[0])))
    skins = [BoundSkin(rig) for rig in rigs]; sizes = [model.size for model in models]
    scale = np.concatenate([np.repeat(model.limits/np.sqrt(3), 3) for model in models])
    def palm_values(worlds):
        centers = []; normals = []
        for actor, skin, world, neighborhood in zip(actors, skins, worlds, neighborhoods):
            p = skin.evaluate(world, np.full(len(neighborhood['ids']), event), neighborhood['ids'])@actor['rotation'].T+actor['translation']
            center, normal = palm_geometry(p, neighborhood['faces'], neighborhood['center']); centers.append(center); normals.append(normal)
        return np.array(centers), np.array(normals)
    initial_centers, initial_normals = palm_values(donor_worlds)
    positions = [rig.vertices(world[event])@actor['rotation'].T+actor['translation'] for rig, world, actor in zip(rigs, donor_worlds, actors)]
    baseline_geometry = audit(positions[0], actors[0]['faces'], positions[1], actors[1]['faces'])
    crossing = [r for r in baseline_geometry['records'] if r['kind'] == 'proper_crossing']
    if not crossing: raise ValueError('No protected-time crossing to repair')
    vertices = np.array([[actor['faces'][r['left_triangle' if i == 0 else 'right_triangle']] for r in crossing] for i, actor in enumerate(actors)])
    axes = choose_axes(positions[0][vertices[0]], positions[1][vertices[1]])
    objective = TriangleSeparationObjective(skins, actors, np.full(len(crossing), event), vertices, axes)
    rows = read(study/'witnesses.json')
    for row in rows: row['frame'] = int(uniform_ids[request['sample_indices'][row['frame']]])
    old_objective = HandWitnessObjective(skins, actors, rows)
    initial_old_depths = -old_objective.gaps(donor_worlds); ceiling = limits(initial_old_depths, request['hand_tolerance_m'])
    def payload(worlds):
        parts = [features(w, rig.joints) for w, rig in zip(worlds, rigs)]
        return {k: np.concatenate([p[k] for p in parts], axis=1) for k in ['positions', 'rotations']}
    caps = SampledMotionCaps(payload(reference), times, request['original_bins_s'])
    # Two absolute surface points, their relative contact vector, and two normals.
    point_limit = 1e-5; normal_limit = 1e-3
    extra_caps = np.r_[np.repeat(point_limit, 3), np.repeat(normal_limit, 2)]
    fixed_caps = np.r_[np.concatenate([(c+.9*caps.tolerance).ravel() for c in caps.caps]), extra_caps]
    fixed_scales = np.r_[np.concatenate([np.maximum(c, f).ravel() for c, f in zip(caps.caps, [.01, 1., .01, 1.])]), extra_caps]
    def worlds_for(x, quantize=True):
        controls = np.split(np.asarray(x)*scale, [sizes[0]])
        return [model.world(control, quantize=quantize) for model, control in zip(models, controls)]
    def evaluate(x, quantize=True):
        worlds = worlds_for(x, quantize); centers, normals = palm_values(worlds)
        palm_vectors = np.vstack([centers-initial_centers, (centers[0]-centers[1])-(initial_centers[0]-initial_centers[1]), normals-initial_normals])
        vectors = np.concatenate([v.reshape(-1, 3) for v in rate_vectors(payload([w[uniform_ids] for w in worlds]), caps.dt)]+[palm_vectors])
        return dict(vectors=vectors, caps=fixed_caps, scales=fixed_scales, margins=(ceiling+old_objective.gaps(worlds))/.02, depths=objective.depths(worlds))
    point = np.zeros(len(scale)); exact = lambda x: evaluate(x); proposal = lambda x: evaluate(x, False)
    before = measurement(exact(point))
    if before['minimum_margin'] < 0: raise ValueError('Donor violates original caps before finger edits')
    solver = solver_module(); meta_path = ROOT/'reports/conic-solver-bootstrap-v1.json'; meta = read(meta_path); files[str(meta_path)] = sha256(meta_path)
    for name, digest in meta['files'].items(): files[str(Path(meta['vendor'])/name)] = digest
    methods = {}; output.mkdir(); (output/'implementation').mkdir()
    names = set(request['implementation']) | {'study_finger_triangle_repair.py', 'native_finger_motion.py', 'triangle_separation_objective.py',
        'swept_triangle_separation.py', 'swept_surface_boxes.py', 'triangle_crossing.py', 'hand_norm_proposal.py', 'hand_witness_envelope.py',
        'iterated_hand_norm.py', 'conic_root_descent.py', 'conic_linear_screen.py', 'root_release_block.py', 'diagnose_oriented_hand_returns.py', 'diagnose_terminal_hand_rates.py'}
    for name in sorted(names):
        source = ROOT/'scripts'/name; methods[name] = sha256(source); shutil.copyfile(source, output/'implementation'/name)
    save(output/'baseline-geometry.json', baseline_geometry)
    save(output/'request.json', dict(at=now(), donor=str(donor), inputs=files, implementation=methods, contact_time_s=contact_time,
        window_s=window, uniform_times_s=times.tolist(), audit_times_s=audit_times.tolist(), original_bins_s=request['original_bins_s'],
        selected_nodes=[m.nodes for m in models], edit_limits_degrees=[np.rad2deg(m.limits).tolist() for m in models],
        scale=scale.tolist(), point_drift_limit_m=point_limit, normal_vector_drift_limit=normal_limit,
        initial_palm_centers_m=initial_centers.tolist(), initial_palm_normals=initial_normals.tolist(), initial_palm_gap_m=float(np.linalg.norm(initial_centers[0]-initial_centers[1])),
        baseline_geometry_sha256=sha256(output/'baseline-geometry.json'), active_crossing_pairs=len(crossing), axes=axes.tolist(),
        old_witness_depths_m=initial_old_depths.tolist(), old_witness_ceilings_m=ceiling.tolist(), iterations=iterations, trusts=[.1, .01, .001],
        before=before, quality_approved=False, scope='Explicit finger-only alternative to whole-pose freezing: arm/wrist/body channels remain exact, actual palm points/relative vector and normals bounded. Original motion caps and old witness ceilings retained. Protected-time triangle objective; whole interaction quality unresolved.'))
    history = []
    def checkpoint(model, record):
        np.savez_compressed(output/f'iteration-{record["iteration"]:02d}.npz', point=model['point'], **model['base'], **{k+'_jacobian': v for k,v in model['jacobian'].items()})
        history.append(record); save(output/'proposals.json', history)
    def observe(record):
        if record['phase'] != 'jacobian' or record['coordinates'] % 19 == 0: print(record, flush=True)
    best, report = solve(exact, proposal, point, solver, iterations=iterations, trusts=(.1, .01, .001), checkpoint=checkpoint, observe=observe)
    save(output/'iteration-summary.json', report); save(output/'selected.json', dict(controls=(best*scale).tolist(), **measurement(exact(best))))
    controls = np.split(best*scale, [sizes[0]]); decoded_worlds = []; clips = []
    for i, (model, control, path, rig, reader) in enumerate(zip(models, controls, input_paths, rigs, readers)):
        dest = output/f'candidate-{i}.glb'
        if np.any(control): model.export(control, dest)
        else: shutil.copyfile(path, dest)
        decoded = RigAsset.load(dest); sampler = AnimationSampler(decoded.document, decoded.binary, 0)
        world = np.array([sampler.sample(t) for t in combined]); decoded_worlds.append(world)
        np.testing.assert_allclose(world, model.world(control), atol=2e-10, rtol=0)
        np.testing.assert_array_equal(world[:, model.body], donor_worlds[i][:, model.body])
        frozen = (combined <= window[0]) | (combined >= window[1]); np.testing.assert_array_equal(world[frozen], donor_worlds[i][frozen])
        old, new = rotation_channels(rig.document, rig.binary), rotation_channels(decoded.document, decoded.binary)
        for node, (_, clock, q) in old.items():
            np.testing.assert_array_equal(new[node][1], clock)
            if node not in model.nodes: np.testing.assert_array_equal(new[node][2], q)
        clips.append(dict(path=dest.name, sha256=sha256(dest), body_and_wrist_exact=True, outside_window_exact=True, native_clocks_exact=True))
    final_payload = dict(indices=np.arange(len(times)), **payload([w[uniform_ids] for w in decoded_worlds]))
    if not caps.check(final_payload): raise ValueError('Decoded motion violates original caps')
    centers, normals = palm_values(decoded_worlds)
    point_error = np.linalg.norm(centers-initial_centers, axis=1); normal_error = np.linalg.norm(normals-initial_normals, axis=1)
    gap_error = np.linalg.norm((centers[0]-centers[1])-(initial_centers[0]-initial_centers[1]))
    if point_error.max() > point_limit or gap_error > point_limit or normal_error.max() > normal_limit: raise ValueError('Decoded palm preservation failed')
    if np.any(-old_objective.gaps(decoded_worlds) > ceiling): raise ValueError('Decoded old witness envelope failed')
    labels = [actor['name']+':'+rig.document['nodes'][n]['name'] for actor, rig in zip(actors, rigs) for n in rig.joints]
    save(output/'decoded.json', dict(clips=clips, full_clock=explain(final_payload, caps, labels), palm_position_errors_m=point_error.tolist(),
        palm_normal_vector_errors=normal_error.tolist(), relative_palm_vector_error_m=float(gap_error), old_witness_envelope_pass=True))
    geometry = []
    for stamp in audit_times:
        frame = int(np.searchsorted(combined, stamp)); points = [rig.vertices(w[frame])@a['rotation'].T+a['translation'] for rig,w,a in zip(rigs,decoded_worlds,actors)]
        value = audit(points[0], actors[0]['faces'], points[1], actors[1]['faces']); name = f'geometry-{len(geometry):02d}.json'; save(output/name, value)
        geometry.append(dict(time_s=float(stamp), counts=value['counts'], path=name, sha256=sha256(output/name)))
        save(output/'geometry.json', geometry); print(dict(phase='fresh_geometry', completed=len(geometry), total=len(audit_times), counts=value['counts']), flush=True)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Finger study input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Finger study method changed')
    outputs = {p.name: sha256(p) for p in output.iterdir() if p.is_file()}
    save(output/'result.json', dict(at=now(), status='complete', outputs=outputs, before=before, after=measurement(exact(best)),
        original_motion_caps_pass=True, palm_preservation_pass=True, old_witness_envelope_pass=True,
        protected_time_crossings_before=len(crossing), protected_time_crossings_after=next(r['counts'].get('proper_crossing',0) for r in geometry if r['time_s']==contact_time),
        total_pair_time_crossings=sum(r['counts'].get('proper_crossing',0) for r in geometry),
        collision_free_certified=False, accepted_for_publication=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('donor', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--iterations', type=int, default=3); args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.donor, args.output, args.iterations)
