"""Repair retained triangle witnesses under original motion/contact limits.

The earlier support anchor moves earlier to include measured approach crossings.
The original protected contact/end anchor stays fixed; uneditable crossings are
retained as failures and cannot be certified away by this local experiment.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def proof_inputs(folder, declared, source_root=None):
    """Bind historical code to its archived bytes, while retaining exact assets."""
    source_root = (ROOT/'scripts' if source_root is None else Path(source_root)).resolve()
    folder = Path(folder).resolve(); result = {}
    for name, digest in declared.items():
        path = Path(name).resolve()
        if path.parent == source_root:
            path = (folder/'implementation'/path.name).resolve()
            if path.parent != folder/'implementation': raise ValueError('Proof snapshot escaped its directory')
        if sha256(path) != digest: raise ValueError('Crossing proof input or archived method changed')
        result[str(path)] = digest
    return result


def run(donor, proof_paths, output, iterations=3):
    from diagnose_oriented_hand_returns import load_evidence
    from diagnose_scene_pair_limits import load_bound_study
    from bound_evidence import bind_inputs
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from sampled_motion_caps import SampledMotionCaps, features
    from independent_hand_motion import layout, INDEPENDENT_LAYOUT
    from oriented_terminal_hand import support_clock
    from paired_temporal_neighbor import rotation_channels
    from paired_approach_basis import BoundSkin
    from continuous_terminal_hand import HandWitnessObjective
    from smooth_hand_proposal import proposal_type
    from hand_norm_proposal import rate_vectors, measurement
    from hand_witness_envelope import limits
    from triangle_separation_objective import TriangleSeparationObjective, choose_axes, gaps
    from triangle_crossing import classify, audit
    from verify_triangle_scene import interior_witness
    from iterated_hand_norm import solve
    from conic_root_descent import solver_module
    from diagnose_terminal_hand_rates import explain
    donor, output = Path(donor).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh triangle correction output required')
    if type(iterations) is not int or not 1 <= iterations <= 12: raise ValueError('One to twelve iterations required')
    previous, donor_request = read(donor/'result.json'), read(donor/'request.json')
    if previous['status'] != 'complete' or not previous['full_clock_motion_pass']: raise ValueError('Completed motion-feasible donor required')
    files = {str(donor/'result.json'): sha256(donor/'result.json')}
    files.update(bind_inputs({}, donor_request['inputs']))
    for name, digest in previous['outputs'].items():
        path = (donor/name).resolve()
        if path.parent != donor or sha256(path) != digest: raise ValueError('Donor output changed')
        files[str(path)] = digest
    study = Path(donor_request['study']); request, evidence = load_evidence(study); files.update(evidence)
    if request.get('control_layout') != INDEPENDENT_LAYOUT: raise ValueError('Independent wrist donor required')
    terminal = read(Path(request['study'])/'request.json'); plan = read(Path(terminal['plan'])/'request.json')
    protocol = read(Path(plan['source_plan'])/'request.json'); baseline = Path(protocol['study'])
    original, _, required = load_bound_study(baseline); files.update(bind_inputs(required, request['inputs']))
    prepared, actors = load_actors(Path(original['prepared_request']).parent)
    baseline_result = read(baseline/'result.json'); trials_path = baseline/'trials.json'
    if sha256(trials_path) != baseline_result['trials_sha256']: raise ValueError('Baseline trials changed')
    trial = next(row for row in read(trials_path) if row['folder'] == baseline_result['selected'])
    sources = []; donors = []; reference = []; times = np.asarray(terminal['sample_times_s'])
    for entry, clip in zip(trial['actors'], read(donor/'decoded.json')['clips']):
        path = (baseline/baseline_result['selected']/entry['path']).resolve()
        if files.get(str(path)) != entry['sha256'] or sha256(path) != entry['sha256']: raise ValueError('Bound original source required')
        rig = RigAsset.load(path); reader = AnimationSampler(rig.document, rig.binary, 0)
        sources.append(rig); reference.append(np.array([reader.sample(t) for t in times]))
        path = (donor/clip['path']).resolve()
        if path.parent != donor or sha256(path) != clip['sha256']: raise ValueError('Donor GLB changed')
        files[str(path)] = clip['sha256']; rig = RigAsset.load(path)
        donors.append((rig, AnimationSampler(rig.document, rig.binary, 0)))
    checks = []
    for folder in map(lambda p: Path(p).resolve(), proof_paths):
        result = read(folder/'result.json')
        if result['status'] != 'complete' or result['failed'] or sha256(folder/'checks.json') != result['checks_sha256']:
            raise ValueError('Completed independent crossing proof required')
        files.update(proof_inputs(folder, result['inputs']))
        for clip in read(donor/'decoded.json')['clips']:
            if result['inputs'].get(str(donor/clip['path'])) != clip['sha256']: raise ValueError('Proof must describe these donor clips')
        for name in ['result.json', 'checks.json']: files[str(folder/name)] = sha256(folder/name)
        checks.extend(read(folder/'checks.json'))
    if not checks or not all(row['passed'] for row in checks): raise ValueError('Verified nonempty crossing population required')
    # Keep the protected end; broaden only the earlier approach support.
    old_native = np.asarray(request['edit_native_times_s']); clock = rotation_channels(sources[0].document, sources[0].binary)[protocol['chains'][actors[0]['name']][0]][1].astype(float)
    start = max(0, int(np.searchsorted(clock, min(r['time_s'] for r in checks), side='right'))-2)
    native = clock[(clock >= min(clock[start], old_native[0])) & (clock <= old_native[-1])]
    if native[-1] != old_native[-1] or not np.isin(old_native, native).all(): raise ValueError('Retain original native keys and protected end')
    _, ids = support_clock(times, native)
    stamps = np.array([row['time_s'] for row in checks]); combined = np.unique(np.r_[times[ids], stamps])
    local_ids = np.searchsorted(combined, times[ids]); witness_frames = np.searchsorted(combined, stamps)
    active = (stamps > native[0]) & (stamps < native[-1])
    if not active.any(): raise ValueError('No retained witness lies inside editable support')
    _, model_type, scale_type, domain = layout(INDEPENDENT_LAYOUT); smooth_type = proposal_type(INDEPENDENT_LAYOUT)
    models = []; smooth = []
    for i, (rig, actor) in enumerate(zip(sources, actors)):
        args = (rig, protocol['chains'][actor['name']], native, combined, prepared['protected_seconds'], actor['rotation'], i)
        models.append(model_type(*args)); smooth.append(smooth_type(*args))
    scale = scale_type(native, plan['guide_rate_limits'])
    controls = np.zeros((len(native)-2, 14)); old_controls = np.asarray(read(donor/'selected.json')['controls']).reshape(-1, 14)
    for stamp, value in zip(old_native[1:-1], old_controls): controls[np.flatnonzero(native[1:-1] == stamp)[0]] = value
    point = controls.ravel()/scale
    initial_worlds = [m.evaluate_vector(point*scale)[0] for m in models]
    for worlds, (rig, reader) in zip(initial_worlds, donors):
        np.testing.assert_allclose(worlds, np.array([reader.sample(t) for t in combined]), atol=2e-10, rtol=0)
    skins = [BoundSkin(rig) for rig in sources]
    vertex_ids = np.array([[actor['faces'][row['triangle_pair'][i]] for row in checks] for i, actor in enumerate(actors)])
    triangles = []
    for i, actor in enumerate(actors):
        points = skins[i].evaluate(initial_worlds[i], np.repeat(witness_frames, 3), vertex_ids[i].ravel())
        triangles.append((points@actor['rotation'].T+actor['translation']).reshape(-1, 3, 3))
    proofs = [interior_witness(a, b) for a, b in zip(*triangles)]
    if any(not p['feasible'] or p['minimum_barycentric_weight'] <= 1e-8 or p['max_scaled_equality_error'] > 1e-8 for p in proofs):
        raise ValueError('Donor crossing did not independently reproduce')
    axes = choose_axes(*triangles)
    objective = TriangleSeparationObjective(skins, actors, witness_frames[active], vertex_ids[:, active], axes[active])
    rows = copy.deepcopy(read(study/'witnesses.json'))
    for row in rows: row['frame'] = int(np.flatnonzero(ids == request['sample_indices'][row['frame']])[0])
    hand_objective = HandWitnessObjective(skins, actors, rows)
    def payload(worlds):
        parts = [features(w, rig.joints) for w, rig in zip(worlds, sources)]
        return {key: np.concatenate([part[key] for part in parts], axis=1) for key in ['positions', 'rotations']}
    caps = SampledMotionCaps(payload(reference), times, request['original_bins_s'])
    bounded = [cap[ids[0]:ids[0]+len(ids)-order] for cap, order in zip(caps.caps, [1, 2, 1, 2])]
    fixed_caps = np.concatenate([(cap+.9*caps.tolerance).ravel() for cap in bounded])
    fixed_scales = np.concatenate([np.maximum(cap, floor).ravel() for cap, floor in zip(bounded, [.01, 1., .01, 1.])])
    initial_depths = -hand_objective.gaps([w[local_ids] for w in initial_worlds]); ceiling = limits(initial_depths, request['hand_tolerance_m'])
    def evaluate(model_set, x):
        control = x*scale; evaluated = [m.evaluate_vector(control) for m in model_set]; worlds = [e[0] for e in evaluated]
        local = [w[local_ids] for w in worlds]; old_depths = -hand_objective.gaps(local)
        return dict(vectors=np.concatenate([v.reshape(-1, 3) for v in rate_vectors(payload(local), caps.dt)]), caps=fixed_caps, scales=fixed_scales,
            margins=np.r_[(45.+1e-4-max(e[1] for e in evaluated))/45., domain(control, native, plan['guide_rate_limits']), (ceiling-old_depths)/.02],
            depths=objective.depths(worlds))
    exact = lambda x: evaluate(models, x); proposal = lambda x: evaluate(smooth, x)
    before = measurement(exact(point))
    if before['minimum_margin'] < 0: raise ValueError('Expanded donor must preserve original feasibility')
    solver = solver_module(); solver_meta_path = ROOT/'reports/conic-solver-bootstrap-v1.json'; solver_meta = read(solver_meta_path)
    files[str(solver_meta_path)] = sha256(solver_meta_path)
    for name, digest in solver_meta['files'].items(): files[str(Path(solver_meta['vendor'])/name)] = digest
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    names = set(request['implementation']) | {'study_triangle_hand_proposal.py', 'triangle_separation_objective.py', 'swept_triangle_separation.py',
        'swept_surface_boxes.py', 'triangle_crossing.py', 'verify_triangle_scene.py', 'smooth_hand_proposal.py', 'hand_norm_proposal.py',
        'hand_witness_envelope.py', 'iterated_hand_norm.py', 'conic_root_descent.py', 'conic_linear_screen.py', 'root_release_block.py',
        'diagnose_oriented_hand_returns.py', 'diagnose_terminal_hand_rates.py'}
    for name in sorted(names):
        source = ROOT/'scripts'/name; methods[name] = sha256(source); shutil.copyfile(source, output/'implementation'/name)
    witness_record = [dict(time_s=float(t), triangle_pair=row['triangle_pair'], active=bool(ok), axis=axis.tolist(),
        initial_gap_m=float(gap.min()), independent_proof=proof) for t, row, ok, axis, gap, proof in zip(stamps, checks, active, axes, gaps(*triangles, axes), proofs)]
    save(output/'witnesses.json', witness_record)
    save(output/'envelope.json', dict(initial_depths_m=initial_depths.tolist(), limits_m=ceiling.tolist()))
    save(output/'request.json', dict(at=now(), donor=str(donor), inputs=files, implementation=methods, native_times_s=native.tolist(),
        original_native_times_s=old_native.tolist(), sample_indices=ids.tolist(), witness_times_s=stamps.tolist(),
        point=point.tolist(), scale=scale.tolist(), original_bins_s=request['original_bins_s'], protected_seconds=prepared['protected_seconds'],
        iterations=iterations, trusts=[.1, .01, .001], triangle_clearance_m=1e-8, witnesses_sha256=sha256(output/'witnesses.json'),
        envelope_sha256=sha256(output/'envelope.json'), before=before, quality_approved=False,
        scope='Earlier approach support expanded under unchanged original motion/contact/edit limits. Fixed directions on retained active crossings only; protected/frozen crossings remain explicit. Fixed old signed-witness envelope. Fresh mesh audit required; no general quality approval.'))
    history = []
    def checkpoint(model, record):
        name = f'iteration-{record["iteration"]:02d}.npz'
        np.savez_compressed(output/name, point=model['point'], **model['base'], **{k+'_jacobian': v for k, v in model['jacobian'].items()})
        history.append(record); save(output/'proposals.json', history)
    def observe(record):
        if record['phase'] != 'jacobian' or record['coordinates'] % 14 == 0: print(record, flush=True)
    best, report = solve(exact, proposal, point, solver, iterations=iterations, trusts=(.1, .01, .001), checkpoint=checkpoint, observe=observe)
    save(output/'iteration-summary.json', report); save(output/'selected.json', dict(controls=(best*scale).tolist(), **measurement(exact(best))))
    final_worlds = []; exported = []; full_worlds = []
    for i, (rig, model) in enumerate(zip(sources, models)):
        path = output/f'candidate-{i}.glb'; model.export_vector(best*scale, path)
        decoded = RigAsset.load(path); reader = AnimationSampler(decoded.document, decoded.binary, 0)
        final_worlds.append(np.array([reader.sample(t) for t in combined])); full_worlds.append(np.array([reader.sample(t) for t in times]))
        np.testing.assert_allclose(final_worlds[-1], model.evaluate_vector(best*scale)[0], atol=2e-10, rtol=0)
        before_channels, after_channels = rotation_channels(rig.document, rig.binary), rotation_channels(decoded.document, decoded.binary)
        for node, (_, source_clock, values) in before_channels.items():
            np.testing.assert_array_equal(source_clock, after_channels[node][1])
            frozen = ~np.isin(source_clock, native[1:-1]) if node in protocol['chains'][actors[i]['name']] else np.ones(len(source_clock), bool)
            np.testing.assert_array_equal(values[frozen], after_channels[node][2][frozen])
        for first, last in prepared['protected_seconds']:
            for t in (first, last): np.testing.assert_array_equal(reader.sample(t), donors[i][1].sample(t))
        exported.append(dict(path=path.name, sha256=sha256(path), frozen_keys_and_protected_endpoints_exact=True))
    if not caps.check(dict(indices=np.arange(len(times)), **payload(full_worlds))): raise ValueError('Export lost original full-clock motion caps')
    final_old_depths = -hand_objective.gaps([w[local_ids] for w in final_worlds])
    if np.any(final_old_depths > ceiling): raise ValueError('Export lost old witness envelope')
    labels = [actor['name']+':'+rig.document['nodes'][n]['name'] for actor, rig in zip(actors, sources) for n in rig.joints]
    save(output/'decoded.json', dict(clips=exported, full_clock=explain(dict(indices=np.arange(len(times)), **payload(full_worlds)), caps, labels),
        all_old_witnesses_inside_envelope=True, triangle_measurement=measurement(exact(best))))
    fresh = []
    for index, stamp in enumerate(stamps):
        points = [rig.vertices(world[witness_frames[index]])@actor['rotation'].T+actor['translation'] for rig, world, actor in zip(sources, final_worlds, actors)]
        value = audit(points[0], actors[0]['faces'], points[1], actors[1]['faces'])
        pair = checks[index]['triangle_pair']; retained = classify(points[0][actors[0]['faces'][pair[0]]], points[1][actors[1]['faces'][pair[1]]])
        name = f'geometry-{index:02d}.json'; save(output/name, value)
        fresh.append(dict(time_s=float(stamp), active=bool(active[index]), retained_pair=retained, counts=value['counts'], path=name, sha256=sha256(output/name)))
        save(output/'geometry.json', fresh); print(dict(phase='fresh_triangle_audit', completed=len(fresh), total=len(stamps), counts=value['counts']), flush=True)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Triangle correction input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Triangle correction implementation changed')
    outputs = {path.name: sha256(path) for path in output.iterdir() if path.is_file()}
    save(output/'result.json', dict(at=now(), status='complete', outputs=outputs, before=before, after=measurement(exact(best)),
        active_retained_witnesses=int(active.sum()), frozen_retained_witnesses=int((~active).sum()),
        final_retained_proper_crossings=sum(row['retained_pair']['kind']=='proper_crossing' for row in fresh),
        fresh_proper_crossing_pairs=sum(row['counts'].get('proper_crossing', 0) for row in fresh),
        original_motion_limits_pass=True, protected_contact_preserved=True, old_witness_envelope_pass=True,
        collision_free_certified=False, accepted_for_publication=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('donor', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--proofs', type=Path, nargs='+', required=True)
    parser.add_argument('--iterations', type=int, default=3); args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.donor, args.proofs, args.output, args.iterations)
