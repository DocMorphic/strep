"""Test bounded vector-norm proposals against actual serialized hand motion."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(study, output, iterations=1, trusts=(.01, .001, .0001), preserve_witness_envelope=False):
    from diagnose_oriented_hand_returns import load_evidence
    from bound_evidence import bind_inputs
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from independent_hand_motion import layout, SYMMETRIC_LAYOUT
    from paired_approach_basis import BoundSkin
    from continuous_terminal_hand import HandWitnessObjective
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh vector-norm study required')
    if type(iterations) is not int or not 1 <= iterations <= 12:
        raise ValueError('One to twelve local iterations required')
    trusts = np.asarray(trusts, float)
    if (trusts.ndim != 1 or not 1 <= len(trusts) <= 6 or not np.isfinite(trusts).all()
            or np.any(trusts <= 0) or np.any(trusts > 1)):
        raise ValueError('One to six finite trust radii in (0, 1] required')
    trusts = trusts.tolist()
    request, files = load_evidence(study)
    terminal = read(Path(request['study']) / 'request.json')
    plan = read(Path(terminal['plan']) / 'request.json')
    protocol = read(Path(plan['source_plan']) / 'request.json'); baseline = Path(protocol['study'])
    original, _, required = load_bound_study(baseline)
    files.update(bind_inputs(required, request['inputs']))
    prepared, actors = load_actors(Path(original['prepared_request']).parent)
    selected = read(baseline / 'result.json')['selected']
    trials = read(baseline / 'trials.json')
    if sha256(baseline / 'trials.json') != read(baseline / 'result.json')['trials_sha256']:
        raise ValueError('Baseline trials changed')
    trial = next(row for row in trials if row['folder'] == selected)
    times = np.asarray(terminal['sample_times_s']); ids = np.asarray(request['sample_indices'])
    native = np.asarray(request['edit_native_times_s']); scale = np.asarray(request['scale'])
    _, model_type, _, margins = layout(request.get('control_layout', SYMMETRIC_LAYOUT))
    models = []; sources = []; reference = []
    for index, (actor, entry) in enumerate(zip(actors, trial['actors'])):
        path = (baseline / selected / entry['path']).resolve()
        if path.parent != (baseline / selected).resolve() or files.get(str(path)) != entry['sha256'] or sha256(path) != entry['sha256']:
            raise ValueError('Bound baseline clip required')
        rig = RigAsset.load(path); reader = AnimationSampler(rig.document, rig.binary, 0)
        sources.append(rig); reference.append(np.array([reader.sample(t) for t in times]))
        models.append(model_type(rig, protocol['chains'][actor['name']], native, times[ids],
                                 prepared['protected_seconds'], actor['rotation'], index))
    parts = [features(w, rig.joints) for w, rig in zip(reference, sources)]
    caps = SampledMotionCaps({key: np.concatenate([part[key] for part in parts], axis=1)
                             for key in ['positions', 'rotations']}, times, request['original_bins_s'])
    from smooth_hand_proposal import proposal_type
    from hand_norm_proposal import rate_vectors, measurement, linearize, direction, backtrack
    from conic_root_descent import solver_module
    from diagnose_terminal_hand_rates import explain
    from paired_temporal_neighbor import rotation_channels
    from hand_surface_screen import hand_vertices, screen
    from hand_geometry_comparison import compare
    smooth_type = proposal_type(request.get('control_layout', SYMMETRIC_LAYOUT))
    smooth = [smooth_type(rig, protocol['chains'][actor['name']], native, times[ids],
              prepared['protected_seconds'], actor['rotation'], i) for i, (rig, actor) in enumerate(zip(sources, actors))]
    rows = read(study/'witnesses.json')
    objective = HandWitnessObjective([BoundSkin(rig) for rig in sources], actors, rows)
    bounds = [cap[ids[0]:ids[0]+len(ids)-order] for cap, order in zip(caps.caps, [1, 2, 1, 2])]
    fixed_caps = np.concatenate([(cap+.9*caps.tolerance).ravel() for cap in bounds])
    fixed_scales = np.concatenate([np.maximum(cap, floor).ravel() for cap, floor in zip(bounds, [.01, 1., .01, 1.])])
    def payload(worlds):
        parts = [features(w, rig.joints) for w, rig in zip(worlds, sources)]
        return {key: np.concatenate([part[key] for part in parts], axis=1) for key in ['positions', 'rotations']}
    def evaluate(model_set, point):
        controls = point*scale; evaluated = [m.evaluate_vector(controls) for m in model_set]
        world = [entry[0] for entry in evaluated]
        return dict(vectors=np.concatenate([v.reshape(-1, 3) for v in rate_vectors(payload(world), caps.dt)]),
                    caps=fixed_caps, scales=fixed_scales,
                    margins=np.r_[(45.+1e-4-max(entry[1] for entry in evaluated))/45.,
                                  margins(controls, native, plan['guide_rate_limits'])], depths=-objective.gaps(world))
    exact = lambda x: evaluate(models, x)
    proposal = lambda x: evaluate(smooth, x)
    chosen = read(study/'selected.json'); point = np.asarray(chosen['controls'])/scale
    before = measurement(exact(point))
    if (abs(before['witness_peak_m']-chosen['witness_peak_m']) > 1e-10
            or abs(before['minimum_margin']-chosen['minimum_margin']) > 1e-10 or before['minimum_margin'] < 0):
        raise ValueError('Motion-feasible bound selected measurement must reproduce')
    envelope = None
    if preserve_witness_envelope:
        from hand_witness_envelope import limits, guarded
        original_depths = exact(point)['depths'].copy()
        ceiling = limits(original_depths, request['hand_tolerance_m'])
        envelope = dict(reference_depths_m=original_depths.tolist(), limits_m=ceiling.tolist(),
                        tolerance_m=request['hand_tolerance_m'], numerical_slack_m=1e-8,
                        scope='Fixed original per-witness max(tolerance, signed depth) plus numerical slack; no geometry clearance claim.')
        exact, proposal = guarded(exact, ceiling), guarded(proposal, ceiling)
        before = measurement(exact(point))
    solver = solver_module()
    solver_path = ROOT/'reports/conic-solver-bootstrap-v1.json'; solver_meta = read(solver_path)
    files[str(solver_path)] = sha256(solver_path)
    for name, digest in solver_meta['files'].items(): files[str(Path(solver_meta['vendor'])/name)] = digest
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    names = set(request['implementation']) | {'study_hand_norm_proposal.py', 'hand_norm_proposal.py',
        'smooth_hand_proposal.py', 'conic_root_descent.py', 'conic_linear_screen.py', 'root_release_block.py',
        'diagnose_oriented_hand_returns.py', 'diagnose_terminal_hand_rates.py', 'hand_geometry_comparison.py'}
    if iterations > 1: names.add('iterated_hand_norm.py')
    if envelope is not None:
        names.add('hand_witness_envelope.py'); save(output/'witness-envelope.json', envelope)
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        methods[name] = sha256(output/'implementation'/name)
    for path in [Path(request['study'])/'request.json', Path(terminal['plan'])/'request.json',
                 Path(plan['source_plan'])/'request.json', baseline/'trials.json']:
        digest = sha256(path)
        if str(path) in files and files[str(path)] != digest: raise ValueError('Bound ancestor changed')
        files[str(path)] = digest
    derivative_step = 1e-4
    save(output/'request.json', dict(at=now(), study=str(study), inputs=files, implementation=methods,
        point=point.tolist(), scale=scale.tolist(), selected_measurement_reproduced=before,
        sample_indices=ids.tolist(), hand_samples=request['hand_samples'], original_bins_s=request['original_bins_s'],
        derivative_step=derivative_step, trusts=trusts, solver_version=solver.__version__, local_iterations=iterations,
        motion_gate_tolerance=.9*caps.tolerance, export_tolerance=caps.tolerance,
        preserve_witness_envelope=preserve_witness_envelope,
        scope=f'Up to {iterations} local central-difference vector models, starting at the completed selected controls; {len(trusts)} independent trust sizes per model, eight exact backoffs each. Actual float32 base values, float64 proposal Jacobians, all individual signed witnesses and fixed original motion/domain caps. Exact-feasible improvements relinearize for the next iteration; final motion is exported and freshly screened. No full-body, engine, human quality or Studio publication.', quality_approved=False))
    def observe(count, total):
        if count % 7 == 0: print(dict(phase='vector_jacobian', coordinates=count, total=total), flush=True)
    model = linearize(exact, proposal, point, derivative_step, observe)
    np.savez_compressed(output/'local-model.npz', point=point, **model['base'],
                        **{key+'_jacobian': value for key, value in model['jacobian'].items()})
    # Same eight deterministic probes used by the preceding scalar audit.
    probes = np.random.default_rng(230930).normal(size=(4, len(point)))
    probes /= np.max(np.abs(probes), axis=1)[:, None]
    prediction = []
    group_sizes = [cap.size for cap in bounds]; edges = np.r_[0, np.cumsum(group_sizes)]
    for radius in [1e-4, 5e-4]:
        for probe in probes:
            delta = radius*probe; actual = exact(point+delta)
            vector = model['base']['vectors']+model['jacobian']['vectors']@delta
            errors = np.abs(np.linalg.norm(vector, axis=1)-np.linalg.norm(actual['vectors'], axis=1))/fixed_scales
            prediction.append(dict(radius=radius, motion_norm_residuals=[float(errors[a:b].max()) for a, b in zip(edges[:-1], edges[1:])],
                signed_depth_residual=float(np.abs(model['base']['depths']+model['jacobian']['depths']@delta-actual['depths']).max()/.02)))
    save(output/'prediction.json', prediction)
    best = point.copy(); metric = before; attempts = []
    extra_outputs = ['witness-envelope.json'] if envelope is not None else []
    if iterations == 1:
        for trust in trusts:
            delta, report = direction(model, trust, solver)
            if delta is not None:
                candidate, trials = backtrack(exact, point, delta, model['base']); report['trials'] = trials
                if candidate is not None:
                    value = measurement(exact(candidate))
                    if value['witness_peak_m'] < metric['witness_peak_m']: best, metric = candidate, value
            attempts.append(report); save(output/'proposals.json', attempts)
            print(dict(phase='proposal', trust=trust, status=report['status'], best=metric), flush=True)
    else:
        from iterated_hand_norm import solve as iterate
        def checkpoint(local_model, record):
            name = f'iteration-{record["iteration"]:02d}.npz'
            np.savez_compressed(output/name, point=local_model['point'], **local_model['base'],
                                **{key+'_jacobian': value for key, value in local_model['jacobian'].items()})
            extra_outputs.append(name); attempts.append(record); save(output/'proposals.json', attempts)
        def iteration_progress(record):
            if record['phase'] != 'jacobian' or record['coordinates'] % 7 == 0: print(record, flush=True)
        best, report = iterate(exact, proposal, point, solver, iterations=iterations, trusts=trusts,
                               step=derivative_step, observe=iteration_progress, checkpoint=checkpoint)
        save(output/'proposals.json', attempts); save(output/'iteration-summary.json', report)
        extra_outputs.append('iteration-summary.json'); metric = measurement(exact(best))
    control = best*scale
    save(output/'selected.json', dict(controls=control.tolist(), **metric))
    names = [actor['name']+':'+rig.document['nodes'][n]['name'] for actor, rig in zip(actors, sources) for n in rig.joints]
    worlds = []; clips = []
    for i, (rig, actor, model_exact, old) in enumerate(zip(sources, actors, models, reference)):
        path = output/f'candidate-{i}.glb'; model_exact.export_vector(control, path)
        decoded = RigAsset.load(path); reader = AnimationSampler(decoded.document, decoded.binary, 0)
        world = np.array([reader.sample(t) for t in times]); worlds.append(world)
        expected = model_exact.evaluate_vector(control)[0]; error = float(np.abs(world[ids]-expected).max())
        if error > 2e-10: raise ValueError('Export and exact proposal model differ')
        np.testing.assert_array_equal(world[(times <= native[0]) | (times >= native[-1])], old[(times <= native[0]) | (times >= native[-1])])
        before_channels = rotation_channels(rig.document, rig.binary); after_channels = rotation_channels(decoded.document, decoded.binary)
        chain = protocol['chains'][actor['name']]
        for node, (_, clock, q) in before_channels.items():
            np.testing.assert_array_equal(after_channels[node][1], clock)
            frozen = ~np.isin(clock, native[1:-1]) if node in chain else np.ones(len(clock), bool)
            np.testing.assert_array_equal(after_channels[node][2][frozen], q[frozen])
        clips.append(dict(path=path.name, sha256=sha256(path), maximum_batch_error=error, frozen_native_keys_exact=True))
    full_payload = dict(indices=np.arange(len(times)), **payload(worlds))
    full_rates = explain(full_payload, caps, names)
    if not caps.check(full_payload): raise ValueError('Export fails original full-clock motion limits')
    save(output/'decoded.json', dict(clips=clips, full_clock=full_rates))
    hands = [hand_vertices(rig, protocol['chains'][actor['name']][-1]) for rig, actor in zip(sources, actors)]
    geometry = []
    for sample in request['hand_samples']:
        points = [rig.vertices(world[sample])@actor['rotation'].T+actor['translation'] for rig, world, actor in zip(sources, worlds, actors)]
        directions = [screen(points[s], hands[s], points[t], actors[t]['faces']) for s, t in [(0, 1), (1, 0)]]
        geometry.append(dict(sample=sample, time_s=float(times[sample]), directions=directions, hand_peak_m=max(d['max_depth_m'] for d in directions)))
        save(output/'geometry.json', geometry)
        print(dict(phase='fresh_geometry', completed=len(geometry), total=len(request['hand_samples'])), flush=True)
    save(output/'donor-comparison.json', compare(read(study/'geometry.json'), geometry, request['hand_tolerance_m']))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Vector-norm study input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Vector-norm study method changed')
    outputs = {name: sha256(output/name) for name in ['request.json', 'local-model.npz', 'prediction.json',
               'proposals.json', 'selected.json', 'decoded.json', 'geometry.json', 'donor-comparison.json']+extra_outputs}
    result = dict(at=now(), status='complete', outputs=outputs, witness_before=before, witness_after=metric,
                  full_clock_motion_pass=True, fresh_hand_peak_m=max(r['hand_peak_m'] for r in geometry),
                  failed_hand_samples=sum(r['hand_peak_m'] > request['hand_tolerance_m'] for r in geometry),
                  full_body_clearance_checked=False, accepted_for_publication=False, quality_approved=False)
    save(output/'result.json', result); print(result, flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--iterations', type=int, default=1)
    parser.add_argument('--trusts', type=float, nargs='+', default=[.01, .001, .0001])
    parser.add_argument('--preserve-witness-envelope', action='store_true'); args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1):
        run(args.study, args.output, args.iterations, args.trusts, args.preserve_witness_envelope)
