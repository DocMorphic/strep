"""Test measured proposal margins against unchanged decoded paired-motion limits."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from diagnose_scene_pair_limits import load_bound_study, constraint_population
from scene_pair_problem import load_actors, ScenePairProblem
from angular_motion_rows import AngularMotionRows
from coupled_pair_reserve import empirical_reserve, tightened_radii
from coupled_pair_proposal import solve
from joint_angular_rates import compare_angular_rates
from verify_scene_pair_fit import rate_check
from study_scene_pair_fit import exported_motion
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def actual_vectors(actors, policies, controls, worlds):
    values = []; offset = 0
    for actor, world in zip(actors, worlds):
        model = actor['model']; part = controls[offset:offset+model.size]; offset += model.size
        values.extend([model.edit_rows(part)[0], actor['rates'].values(world)[0]])
    if offset != len(controls): raise ValueError('Matching paired controls required')
    values.extend(policy.values(world)[0] for policy,world in zip(policies,worlds))
    return np.concatenate(values)


def run(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh reserve experiment required')
    request, linear, files = load_bound_study(study)
    if request.get('angular_motion') is not True: raise ValueError('Angular-enabled parent required')
    result = read(study/'result.json'); trial_file = study/'trials.json'
    if sha256(trial_file) != result['trials_sha256']: raise ValueError('Parent trial evidence changed')
    files[str(trial_file)] = sha256(trial_file)
    methods = sorted(set(request['implementation']) | {'study_scene_pair_export_reserve.py', 'coupled_pair_reserve.py',
        'diagnose_scene_pair_limits.py', 'verify_scene_pair_fit.py'})
    for name in methods:
        if name in request['implementation'] and sha256(ROOT/'scripts'/name) != request['implementation'][name]:
            raise ValueError('Parent method differs: '+name)
    _, actors = load_actors(Path(request['prepared_request']).parent)
    policies = [AngularMotionRows(a['model'], a['rig'].joints) for a in actors]
    problem = ScenePairProblem(actors, [read(study/'source'/n) for n in read(study/'source-index.json')])
    zero = np.zeros(problem.size)
    np.testing.assert_allclose(actual_vectors(actors, policies, zero, [a['model'].world(np.zeros(a['model'].size)) for a in actors]),
        linear['vectors'], atol=1e-9, rtol=0)
    output.mkdir(); (output/'implementation').mkdir()
    for name in methods: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    saved_methods = {n:sha256(output/'implementation'/n) for n in methods}
    protocol = dict(at=now(), study=str(study), inputs=files, implementation=saved_methods, multiplier=2.,
        factors=[1., .5, .25, .125, .0625], motion_tolerance=1e-5,
        scope='One proposal with empirically tightened motion radii. Original caps, surface constraints, trust and edit budget remain acceptance limits. Margins are not certified error bounds. No full mesh or engine validation here.', quality_approved=False)
    save(output/'request.json', protocol)
    predicted = []; observed = []
    for trial in read(trial_file):
        controls = np.asarray(trial['controls']); worlds = []
        for actor, report in zip(actors, trial['actors']):
            path = study/trial['folder']/report['path']
            if sha256(path) != report['sha256']: raise ValueError('Parent export changed')
            files[str(path)] = report['sha256']; doc, binary = read_glb(path); sampler = AnimationSampler(doc, binary, 0)
            worlds.append(np.array([sampler.sample(t) for t in actor['model'].times]))
        predicted.append(np.linalg.norm(linear['vectors']+np.einsum('nid,d->ni', linear['jacobians'], controls), axis=1))
        observed.append(np.linalg.norm(actual_vectors(actors, policies, controls, worlds), axis=1))
    reserve, error = empirical_reserve(predicted, observed, linear['kinds'], multiplier=protocol['multiplier'])
    tightened = tightened_radii(linear['radii'], reserve, linear['kinds'])
    np.savez_compressed(output/'margins.npz', predicted=predicted, observed=observed, reserve=reserve, error=error,
        original_radii=linear['radii'], tightened_radii=tightened, kinds=linear['kinds'])
    summary = {str(k):dict(rows=int((linear['kinds']==k).sum()),
        tightened=int((reserve[linear['kinds']==k] > 0).sum()), maximum_reserve=float(reserve[linear['kinds']==k].max(initial=0))) for k in np.unique(linear['kinds'])}
    save(output/'margin-summary.json', summary); save(output/'request.json', protocol)
    population = constraint_population(dict(linear, radii=tightened))
    step, solver = solve(**{k:linear[k] for k in ['gaps', 'gap_jacobian', 'depth_caps']},
        **{k:population[k] for k in ['vectors', 'jacobians', 'radii']}, trust=np.deg2rad(request['trust_degrees']),
        norm_tolerances=population['tolerances'])
    save(output/'solver.json', dict(solver=solver, step=None if step is None else step.tolist()))
    print(dict(phase='solve', **solver), flush=True)
    trials = []
    if step is not None:
        for index, factor in enumerate(protocol['factors']):
            folder = output/f'trial-{index}'; records, worlds, bound = exported_motion(problem, step*factor, folder)
            independent = []; reasons = []
            for actor, world, record in zip(actors, worlds, records):
                model = actor['model']; positions = actor['rates'].positions; joints = actor['rig'].joints
                positional = rate_check(positions(model.source_world), positions(world), model.times, model.knots)
                if positional['failures'] != record['rate_failures']: raise ValueError('Independent positional replay differs')
                names = [actor['rig'].document['nodes'][j]['name'] for j in joints]
                angular = compare_angular_rates(model.source_world[:,joints][:,:,:3,:3], world[:,joints][:,:,:3,:3],
                    model.times, model.knots, names, speed_tolerance=1e-5, acceleration_tolerance=1e-5)
                independent.append(dict(actor=actor['name'], positional=positional, angular=angular))
            if any(a['positional']['failures'] for a in independent): reasons.append('exported_motion')
            if any(v['exceeding_observations'] for a in independent for v in a['angular'].values()): reasons.append('exported_angular_motion')
            if any(not r['preserved'] for r in records): reasons.append('preservation_or_budget')
            if max(bound.values()) > 1e-6: reasons.append('retained_surface_bounds')
            row = dict(factor=factor, controls=(step*factor).tolist(), actors=records, motion_reviews=independent, bound=bound,
                preliminary_checks_pass=not reasons, reasons=reasons, full_geometry_checked=False, quality_approved=False)
            save(folder/'review.json', row); trials.append(row); save(output/'trials.json', trials)
            print(dict(factor=factor, reasons=reasons), flush=True)
    for name,digest in files.items():
        if sha256(name) != digest: raise ValueError('Reserve input changed during run')
    for name,digest in saved_methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Reserve method changed during run')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        margins_sha256=sha256(output/'margins.npz'), solver_sha256=sha256(output/'solver.json'),
        trials_sha256=sha256(output/'trials.json') if trials else None,
        passing_factors=[t['factor'] for t in trials if t['preliminary_checks_pass']],
        full_geometry_checked=False, engine_checked=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('study', type=Path); p.add_argument('output', type=Path); a = p.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(a.study, a.output)
