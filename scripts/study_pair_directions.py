"""Compare six arm-surface directions on a bound continuation linearization.

This is a development diagnostic. Decoded motion checks do not certify fresh
mesh clearance, native-engine compatibility or animation quality.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(source, output):
    from continuation_evidence import load_continuation, parent_trial
    from diagnose_scene_pair_limits import load_bound_study, constraint_population
    from scene_pair_problem import load_actors
    from scene_pair_relinearization import refreshed_problem
    from angular_motion_rows import AngularMotionRows
    from refined_reserve_inputs import install_refined_models
    from study_scene_pair_fit import METHODS, exported_motion
    from directional_pair_proposal import surface_directions, solve
    from joint_angular_rates import compare_angular_rates
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh diagnostic destination required')
    request, _, _, files = load_continuation(source); parent_trial(request)
    parent = Path(request['study']); prepared, _, bound = load_bound_study(parent); files.update(bound)
    _, actors = load_actors(Path(prepared['prepared_request']).parent)
    policies = [AngularMotionRows(a['model'], a['rig'].joints) for a in actors]
    install_refined_models(actors, prepared['curve_actors'])
    samples = [read(parent/'source'/n) for n in read(parent/'source-index.json')]
    current = [read(source/'current'/n) for n in read(source/'current-index.json')]
    original, refreshed = refreshed_problem(actors, samples, current)
    with np.load(source/'linearization.npz', allow_pickle=False) as archive: linear = dict(archive)
    # The saved matrix starts with refreshed rows, then original rows. Tie the
    # objective explicitly to the first block's ordered witness and normal.
    records = [(row['sample'], d['source'], r) for s in [0, 1] for row in current
               for d in [row['directions'][s]] for r in d['records']]
    normals = np.array([r['normal'] for _, _, r in records])
    np.testing.assert_allclose(linear['gaps'][:len(records)],
                              [r['gap_m'] for _, _, r in records], atol=1e-8, rtol=0)
    np.testing.assert_allclose(linear['gap_jacobian'][:len(records)],
        np.einsum('ni,nid->nd', normals, linear['surface_jacobians'][:len(records)]), atol=1e-12, rtol=0)
    row = int(np.argmin(linear['gaps'][:len(records)])); sample, actor_id, witness = records[row]
    directions = surface_directions(witness['normal'])
    base = np.asarray(request['cumulative_controls'], float)
    original.split(base)
    population = constraint_population(linear)
    output.mkdir(); (output/'implementation').mkdir()
    methods = {}
    for name in sorted(set(METHODS)|{'study_pair_directions.py', 'directional_pair_proposal.py',
            'continuation_evidence.py', 'diagnose_scene_pair_limits.py', 'refined_reserve_inputs.py',
            'diagnose_scene_pair_refinement.py', 'scene_pair_relinearization.py'}):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        methods[name] = sha256(output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        cumulative_controls=base.tolist(), incremental_trust_degrees=5., scale=.025, regularizer=5e-6,
        factors=[1., .5], objective_witness=dict(row=row, sample=sample, actor=actor_id,
            time_s=current[sample]['time_s'], **witness),
        directions={name: d.tolist() for name, d in directions},
        scope='Six directional objectives from the same saved continuous base. Five-degree incremental trust with unchanged original native budgets, motion bins, protected keys, depth caps and witness-distance bounds. No full geometry or engine acceptance.',
        quality_approved=False))
    rows = []
    for name, direction in directions:
        folder = output/name; folder.mkdir()
        objective = direction@linear['surface_jacobians'][row]
        step, report = solve(**{k:linear[k] for k in ['gaps','gap_jacobian','depth_caps']},
            **{k:population[k] for k in ['vectors','jacobians','radii']}, objective=objective,
            norm_tolerances=population['tolerances'], trust=np.deg2rad(5.), regularizer=5e-6)
        save(folder/'solver.json', dict(solver=report, increment=None if step is None else step.tolist()))
        print(dict(phase='solved', direction=name, **report), flush=True)
        trials = []
        if step is not None:
            for index, factor in enumerate([1., .5]):
                controls = base+factor*step
                records_out, worlds, bounds = exported_motion(original, controls, folder/f'trial-{index}')
                surface = refreshed.surface_rows(worlds)
                excess = float(np.maximum(-surface['gaps']-surface['depth_caps'], 0).max(initial=0))
                inside = linear['gaps'][:len(normals)] < 0
                distance_excess = float(np.maximum(np.linalg.norm(surface['surface_vectors'][inside], axis=1)
                    -surface['depth_caps'][inside], 0).max(initial=0))
                angular = []
                for actor, world, policy in zip(actors, worlds, policies):
                    joints = actor['rig'].joints
                    angular.append(dict(actor=actor['name'], rates=compare_angular_rates(
                        actor['model'].source_world[:,joints,:,:][:,:,:3,:3], world[:,joints,:,:][:,:,:3,:3],
                        actor['model'].times, policy.knots,
                        [actor['rig'].document['nodes'][j]['name'] for j in joints],
                        speed_tolerance=1e-5, acceleration_tolerance=1e-5)))
                reasons = []
                if any(r['rate_failures'] for r in records_out): reasons.append('exported_motion')
                if any(not r['preserved'] for r in records_out): reasons.append('preservation_or_budget')
                if max(bounds.values()) > 1e-6: reasons.append('original_surface_bounds')
                if any(v['exceeding_observations'] for a in angular for v in a['rates'].values()): reasons.append('exported_angular_motion')
                if excess > 1e-6: reasons.append('refreshed_surface_planes')
                if distance_excess > 1e-6: reasons.append('refreshed_surface_distance')
                trial = dict(factor=factor, controls=controls.tolist(), actors=records_out,
                    angular_rates=angular, bounds=bounds, refreshed_plane_excess_m=excess,
                    refreshed_distance_excess_m=distance_excess,
                    decoded_directional_displacement_m=float(direction@(surface['surface_vectors'][row]-linear['surface_vectors'][row])),
                    retained_witness_peak_m=float(np.maximum(-surface['gaps'], 0).max()),
                    preliminary_pass=not reasons, reasons=reasons, quality_approved=False)
                save(folder/f'trial-{index}'/'review.json', trial); trials.append(trial)
                print(dict(phase='decoded', direction=name, factor=factor, reasons=reasons), flush=True)
        rows.append(dict(direction=name, solver=report, trials=trials)); save(output/'variants.json', rows)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Directional study input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Directional study method changed')
    artifacts = {str(p.relative_to(output)):sha256(p) for p in output.rglob('*') if p.is_file()}
    save(output/'result.json', dict(at=now(), status='complete', artifacts=artifacts,
        directions=len(rows), preliminary_passes=sum(t['preliminary_pass'] for r in rows for t in r['trials']),
        requires_independent_replay_and_full_mesh=True, accepted_for_publication=False, quality_approved=False))
    print(read(output/'result.json') | {'artifacts':len(artifacts)}, flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    args = p.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output)
