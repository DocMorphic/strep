"""One matched coupled step with fresh surface bindings and clear-time protection."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from strep import ROOT, read, save, sha256, now
from coupled_pair_problem import PairProblem
from coupled_pair_proposal import solve
from coupled_pair_reserve import tightened_radii
from coupled_continuation_checkpoint import checkpoint
from coupled_continuation_checks import ContinuationReview
from coupled_continuation_policy import acceptance
from coupled_clearance_policy import protected_caps, compare_depths
from coupled_surface_refresh import query, install, per_time_depths


def run(start, geometry, witnesses, reserve, output):
    start, geometry, reserve, output = (Path(p).resolve() for p in (start, geometry, reserve, output))
    if output.exists():
        raise ValueError('Preserve earlier refreshed comparison')
    problem = PairProblem(witnesses); state = checkpoint(start)
    gp, gr = read(geometry/'request.json'), read(geometry/'verification.json')
    if gr['request_sha256'] != sha256(geometry/'request.json') or gr['samples_sha256'] != sha256(geometry/'samples.json') or gr['samples'] != 57 or gr['fresh_directional_queries'] != 114:
        raise ValueError('Completed exact full-mesh starting audit required')
    if gr['cap_failures_over_1e_6'] or gr['maximum_floor_increase_m'] > 1e-6:
        raise ValueError('Starting pair exceeds unchanged geometry limits')
    rows = read(geometry/'samples.json')['rows']
    np.testing.assert_array_equal([r['frame'] for r in rows], problem.request['frames'])
    starting_full_depths = np.array([r['candidate_depth_m'] for r in rows])
    caps = protected_caps([r['source_depth_m'] for r in rows], starting_full_depths)
    rp, rr = read(reserve/'request.json'), read(reserve/'result.json')
    if rr['status'] != 'complete' or rr['request_sha256'] != sha256(reserve/'request.json') or rr['reserve_sha256'] != sha256(reserve/'reserve.npz'):
        raise ValueError('Completed bound motion margins required')
    if rr.get('checkpoint') != str(start) or sha256(rr['center_linearization_path']) != rr['center_linearization_sha256']:
        raise ValueError('Exact local margin center required')
    np.testing.assert_array_equal(rr['center_controls'], state['controls'])
    inputs = {**problem.inputs, **state['inputs'], **gp['inputs'], **rp['inputs']}
    start_paths = []
    for entry in state['result']['selected']['actors']:
        path = start/'candidate'/(entry['actor']+'.glb')
        if gp['inputs'].get(str(path)) != entry['sha256']:
            raise ValueError('Starting geometry uses another pair')
        inputs[str(path)] = entry['sha256']; start_paths.append(path)
    for folder, names in [(geometry, ['request.json', 'samples.json', 'verification.json']), (reserve, ['request.json', 'result.json', 'reserve.npz'])]:
        for name in names:
            inputs[str(folder/name)] = sha256(folder/name)
    bootstrap = ROOT/'reports/conic-solver-bootstrap-v1.json'; inputs[str(bootstrap)] = sha256(bootstrap)
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Comparison input changed')
    output.mkdir(); snapshot = output/'implementation'; snapshot.mkdir()
    methods = ['study_coupled_refreshed_pair.py', 'coupled_surface_refresh.py', 'coupled_clearance_policy.py',
               'coupled_continuation_checks.py', 'coupled_continuation_policy.py', 'coupled_continuation_checkpoint.py',
               'coupled_pair_problem.py', 'coupled_pair_proposal.py', 'coupled_pair_reserve.py', 'coupled_surface_norms.py',
               'paired_approach_basis.py', 'paired_surface_witness.py', 'paired_guarded_temporal.py', 'paired_temporal_neighbor.py',
               'study_paired_guarded_temporal.py', 'study_paired_temporal_neighbor.py', 'audit_scene_joint_rates.py',
               'verify_paired_stage_rates.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'conic_root_descent.py', 'strep.py']
    for name in methods:
        shutil.copyfile(ROOT/'scripts'/name, snapshot/name)
    request = dict(at=now(), inputs=inputs, implementation={n: sha256(snapshot/n) for n in methods},
                   start=str(start), origin=str(state['origin']), reserve=str(reserve), starting_geometry=str(geometry),
                   trust_degrees=.2, maximum_steps=1, line_factors=[1., .5, .25, .125, .0625],
                   frames=problem.request['frames'], depth_caps_m=caps.tolist(), windows=problem.windows,
                   protected_clear_times=[r['frame'] for r in rows if r['candidate_depth_m'] <= .005],
                   original_edit_limit_degrees=5., export_edit_tolerance_degrees=1e-4, motion_tolerance=1e-5,
                   surface_comparison_tolerance_m=1e-6, minimum_actual_depth_improvement_m=1e-6,
                   quality_approved=False, scope='One fresh-binding step from the earlier 24-failure pair. Original source ceilings, motion and total edit origins remain fixed. Previously clear sampled times receive a stricter 5 mm cap. Fresh selected-vertex signed distances, not rebound fixed-point norms, determine improvement. All 3045 original selected vertex/time identities remain; closest target features and inside masks are refreshed at the exact starting exports. This is a subset screen, pending complete sampled mesh and engine audits.')
    save(output/'request.json', request); save(output/'progress.json', dict(status='refreshing_start'))
    began = time.monotonic()
    bindings = query(problem, start_paths)
    np.savez_compressed(output/'bindings.npz', **bindings)
    starting_depths = per_time_depths(problem, bindings)
    if np.any(starting_depths > starting_full_depths + 1e-8):
        raise ValueError('Starting subset contradicts completed full-mesh audit')
    install(problem, bindings, dict(zip(problem.request['frames'], caps)))
    gaps = -np.concatenate([bindings[f'{n}_signed_depth'] for n in range(2)])
    review = ContinuationReview(problem, gaps)
    controls = state['controls'].copy(); initial = review.export_and_check(controls, output/'start')
    for entry, source in zip(initial['actors'], start_paths):
        if entry['sha256'] != sha256(source):
            raise ValueError('Cumulative controls do not reproduce start bytes')
        entry['path'] = 'start/'+entry['path']
    if initial['surface']['maximum_cap_excess_m'] > 1e-6 or any(c['rate_failures'] or c['maximum_original_edit_degrees'] > 5.0001 or not c['preservation']['original_finger_limits_passed'] for c in initial['actors']):
        raise ValueError('Rebound start violates unchanged exported gates')
    initial['actual_subset'] = compare_depths(starting_depths, starting_depths, caps)
    save(output/'start-review.json', initial)
    linear = problem.linearize(controls, include_surface_vectors=True)
    # Only surface references/policy change. The locally calibrated motion center must be identical.
    with np.load(rr['center_linearization_path'], allow_pickle=False) as center:
        for key in ['vectors', 'jacobians', 'radii', 'kinds']:
            np.testing.assert_array_equal(linear[key], center[key], err_msg='Motion margin center mismatch: '+key)
    with np.load(state['origin']/'linearization.npz', allow_pickle=False) as origin:
        for key in ['radii', 'kinds']:
            np.testing.assert_array_equal(linear[key], origin[key])
        if np.any(linear['depth_caps'] > origin['depth_caps']):
            raise ValueError('Surface refresh widened original ceilings')
    np.savez_compressed(output/'linearization.npz', **linear)
    with np.load(reserve/'reserve.npz', allow_pickle=False) as archive:
        margins = archive['reserve'].copy()
    inside = review.initial_inside
    step, solver = solve(**{k: linear[k] for k in ['gaps', 'gap_jacobian', 'depth_caps']},
        vectors=np.concatenate([linear['vectors'], linear['surface_vectors'][inside]]),
        jacobians=np.concatenate([linear['jacobians'], linear['surface_jacobians'][inside]]),
        radii=np.r_[tightened_radii(linear['radii'], margins, linear['kinds']), linear['depth_caps'][inside]],
        trust=np.deg2rad(.2), norm_tolerances=np.r_[np.where(linear['kinds'] == 'edit', 1e-8, 1e-6), np.full(inside.sum(), 1e-8)])
    save(output/'solver.json', dict(base_controls=controls.tolist(), step=None if step is None else step.tolist(), solver=solver,
                                   linearization_sha256=sha256(output/'linearization.npz')))
    print(dict(status='solved', solver=solver), flush=True)
    trials = []; selected = None; verified = initial['verified_peak_values']; error = initial['maximum_replay_error']
    save(output/'trials.json', trials)
    if step is not None:
        for index, factor in enumerate(request['line_factors']):
            save(output/'progress.json', dict(status='checking_export', trial=index, factor=factor))
            folder = output/f'trial-{index}'; candidate_controls = controls+factor*step
            candidate = review.export_and_check(candidate_controls, folder)
            verified += candidate['verified_peak_values']; error = max(error, candidate['maximum_replay_error'])
            fresh = query(problem, [folder/(a['name']+'.glb') for a in problem.actors])
            np.savez_compressed(folder/'fresh-surface.npz', **fresh)
            actual = compare_depths(starting_depths, per_time_depths(problem, fresh), caps)
            decision = acceptance(actual['start_peak_m'], actual['candidate_peak_m'],
                max(actual['maximum_cap_excess_m'], candidate['surface']['maximum_cap_excess_m']),
                [c['rate_failures'] for c in candidate['actors']], [c['maximum_original_edit_degrees'] for c in candidate['actors']],
                [c['preservation']['original_finger_limits_passed'] for c in candidate['actors']])
            for entry in candidate['actors']:
                entry['path'] = (folder/entry['path']).relative_to(output).as_posix()
            trial = dict(factor=factor, controls=candidate_controls.tolist(), decision=decision, actual_subset=actual,
                         fresh_surface_sha256=sha256(folder/'fresh-surface.npz'), **candidate)
            trials.append(trial); save(output/'trials.json', trials)
            print(dict(factor=factor, actual=actual, reasons=decision['reasons']), flush=True)
            if decision['accepted']:
                selected = trial; break
    if selected is not None:
        cases = []
        for variant in ['input', 'candidate']:
            (output/variant).mkdir()
        for actor, entry in zip(problem.actors, selected['actors']):
            for variant, source in [('input', actor['source']), ('candidate', output/entry['path'])]:
                target = output/variant/(actor['name']+'.glb'); shutil.copyfile(source, target)
                cases.append(dict(id=variant+'-'+actor['name'], path=target.relative_to(output).as_posix(), sha256=sha256(target), frames=150, fps=30, sample_by_time=True))
        save(output/'manifest.json', dict(cases=cases, quality_approved=False))
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Input changed during comparison')
    for name, digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Method changed during comparison')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        bindings_sha256=sha256(output/'bindings.npz'), solver_sha256=sha256(output/'solver.json'), trials_sha256=sha256(output/'trials.json'),
        selected=selected, trial_count=len(trials), total_controls=controls.tolist() if selected is None else selected['controls'],
        penetrating_norm_rows=int(inside.sum()), verified_peak_values=verified, maximum_replay_error=error,
        elapsed_seconds=time.monotonic()-began, geometry_checked=False, quality_approved=False))
    save(output/'progress.json', dict(status='complete')); print(dict(status='complete', selected=selected is not None, trials=len(trials)), flush=True)


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['start', 'geometry', 'witnesses', 'reserve', 'output']:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        run(args.start, args.geometry, args.witnesses, args.reserve, args.output)
