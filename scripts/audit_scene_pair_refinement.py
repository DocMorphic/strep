"""Decode refined-curve exports against the unchanged original motion limits."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from diagnose_scene_pair_limits import load_bound_study
from scene_pair_problem import load_actors, ScenePairProblem
from timed_rotation_edit import TimedRotationEdit
from study_scene_pair_fit import exported_motion
from verify_scene_pair_fit import rate_check
from bound_evidence import bind_inputs


def run(refinement, output):
    refinement, output = Path(refinement).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh export audit required')
    result = read(refinement/'result.json'); request = read(refinement/'request.json')
    if result['status'] != 'complete': raise ValueError('Completed refinement required')
    files = {}
    for name in ['request.json', 'solver.json', 'linearization.npz']:
        digest = result[name.split('.')[0]+'_sha256']
        if sha256(refinement/name) != digest: raise ValueError('Refinement artifact changed')
        files[str(refinement/name)] = digest
    files[str(refinement/'result.json')] = sha256(refinement/'result.json')
    for name, digest in request['implementation'].items():
        path = refinement/'implementation'/name
        if sha256(path) != digest or sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Refinement method changed')
        files[str(path)] = digest
    study = Path(request['study']); original_request, _, bound_files = load_bound_study(study)
    files.update(bound_files)
    files.update(bind_inputs(bound_files, request['inputs']))
    _, actors = load_actors(Path(original_request['prepared_request']).parent)
    if [a['name'] for a in actors] != [a['actor'] for a in request['actors']]: raise ValueError('Refined actor order changed')
    for actor, description in zip(actors, request['actors']):
        old = actor['model']; np.testing.assert_array_equal(old.knots, description['original_knots_s'])
        actor['original_knots'] = old.knots.copy()
        actor['model'] = TimedRotationEdit(old.document, old.binary, [old.document['nodes'][n]['name'] for n in old.nodes],
            old.times, old.window, old.protected, knots=description['refined_knots_s'], limit_degrees=old.limit_degrees)
        if actor['model'].size != description['refined_controls']: raise ValueError('Refined controls changed')
    problem = ScenePairProblem(actors, [read(study/'source'/n) for n in read(study/'source-index.json')])
    step = read(refinement/'solver.json')['step']
    if step is None: raise ValueError('No refined proposal to export')
    step = np.asarray(step); problem.split(step)
    output.mkdir(); (output/'implementation').mkdir()
    methods = {}
    for name in sorted(set(request['implementation']) | {'audit_scene_pair_refinement.py', 'verify_scene_pair_fit.py', 'bound_evidence.py'}):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name); methods[name] = sha256(output/'implementation'/name)
    save(output/'request.json', dict(at=now(), refinement=str(refinement), inputs=files, implementation=methods,
        factors=[1., .5, .25, .125, .0625], scope='Export and independent original-bin motion checks only. Full fresh mesh/floor queries and engine import still required.', quality_approved=False))
    trials = []
    for index, factor in enumerate([1., .5, .25, .125, .0625]):
        folder = output/f'trial-{index}'
        records, worlds, surface = exported_motion(problem, step*factor, folder)
        independent = []
        for actor, world, record in zip(actors, worlds, records):
            model = actor['model']; positions = actor['rates'].positions
            checked = rate_check(positions(model.source_world), positions(world), model.times, actor['original_knots'])
            if checked['failures'] != record['rate_failures']: raise ValueError('Independent all-joint replay disagrees')
            independent.append(dict(actor=actor['name'], **checked))
        passed = all(r['preserved'] and not r['rate_failures'] for r in records) and max(surface.values()) <= 1e-6
        row = dict(factor=factor, controls=(step*factor).tolist(), actors=records, retained_surface=surface,
            independent_rates=independent, preliminary_checks_pass=bool(passed), quality_approved=False)
        save(folder/'review.json', row); trials.append(row); save(output/'trials.json', trials)
        print(dict(factor=factor, preliminary_checks_pass=passed, motion_failures=[r['rate_failures'] for r in records]), flush=True)
    for name, digest in files.items():
        if sha256(name) != digest: raise ValueError('Audit input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Audit method changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        trials_sha256=sha256(output/'trials.json'), passing_factors=[t['factor'] for t in trials if t['preliminary_checks_pass']],
        full_geometry_checked=False, engine_checked=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('refinement', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.refinement, args.output)
