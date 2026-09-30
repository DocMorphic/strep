"""Matched refined-curve proposal with additional original angular-rate caps."""
import argparse
from contextlib import ExitStack
from pathlib import Path
import shutil
import time
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(refinement, output):
    from diagnose_scene_pair_limits import load_bound_study, constraint_population
    from angular_motion_rows import AngularMotionRows
    from scene_pair_angular_constraints import linearize_angular
    from scene_pair_problem import load_actors
    from timed_rotation_edit import TimedRotationEdit
    from coupled_pair_proposal import solve
    refinement, output = Path(refinement).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh angular-constrained proposal required')
    complete = read(refinement/'result.json'); parent = read(refinement/'request.json')
    if complete['status'] != 'complete': raise ValueError('Completed matched refinement required')
    parent_files = {str(refinement/'result.json'): sha256(refinement/'result.json')}
    for name in ['request.json', 'linearization.npz', 'solver.json']:
        digest = complete[name.split('.')[0]+'_sha256']
        if sha256(refinement/name) != digest: raise ValueError('Refinement artifact changed')
        parent_files[str(refinement/name)] = digest
    for name, digest in parent['implementation'].items():
        path = refinement/'implementation'/name
        if sha256(path) != digest or sha256(ROOT/'scripts'/name) != digest: raise ValueError('Refinement method changed')
        parent_files[str(path)] = digest
    original_request, _, files = load_bound_study(Path(parent['study']))
    for path, digest in parent['inputs'].items():
        if files.get(path) != digest: raise ValueError('Refinement source binding differs')
    files.update(parent_files)
    _, actors = load_actors(Path(original_request['prepared_request']).parent); policies = []
    if [a['name'] for a in actors] != [r['actor'] for r in parent['actors']]: raise ValueError('Refinement actor identity differs')
    for actor, spec in zip(actors, parent['actors']):
        old = actor['model']; np.testing.assert_array_equal(old.knots, spec['original_knots_s'])
        policies.append(AngularMotionRows(old, actor['rig'].joints))
        actor['model'] = TimedRotationEdit(old.document, old.binary, [old.document['nodes'][n]['name'] for n in old.nodes],
            old.times, old.window, old.protected, knots=spec['refined_knots_s'], limit_degrees=old.limit_degrees)
        if actor['model'].size != spec['refined_controls']: raise ValueError('Refined control layout changed')
    with np.load(refinement/'linearization.npz', allow_pickle=False) as saved: original = dict(saved)
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    additions = {'study_scene_pair_angular_refinement.py', 'scene_pair_angular_constraints.py', 'angular_motion_rows.py', 'joint_angular_rates.py'}
    for name in sorted(set(parent['implementation']) | additions):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name); methods[name] = sha256(output/'implementation'/name)
    import os, psutil
    save(output/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    save(output/'request.json', dict(at=now(), study=parent['study'], parent_refinement=str(refinement), inputs=files,
        implementation=methods, actors=parent['actors'], trust_degrees=original_request['trust_degrees'],
        scope='Identical saved refined surface, edit and positional rows plus original-span world angular speed/acceleration norms. Affine proposal only; independent exports, full mesh and engine checks remain required.', quality_approved=False))
    save(output/'pipeline.json', dict(status='processing', stage='Building angular norm derivatives'))
    linear, proofs = linearize_angular(actors, policies, original)
    # Every previous constraint remains exactly present, in the same order.
    for key in ['gaps', 'gap_jacobian', 'depth_caps', 'surface_vectors', 'surface_jacobians']:
        np.testing.assert_array_equal(linear[key], original[key])
    for key in ['vectors', 'jacobians', 'radii', 'kinds']:
        np.testing.assert_array_equal(linear[key][:len(original[key])], original[key])
    np.savez_compressed(output/'linearization.npz', **linear); save(output/'angular-derivative-proof.json', proofs)
    population = constraint_population(linear); trust = np.deg2rad(original_request['trust_degrees'])
    save(output/'pipeline.json', dict(status='processing', stage='Solving with angular caps'))
    step, solver = solve(**{k: linear[k] for k in ['gaps', 'gap_jacobian', 'depth_caps']},
        **{k: population[k] for k in ['vectors', 'jacobians', 'radii']}, trust=trust, norm_tolerances=population['tolerances'])
    save(output/'solver.json', dict(solver=solver, step=None if step is None else step.tolist(), angular_derivative_proofs=proofs))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Angular proposal input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Angular proposal method changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        linearization_sha256=sha256(output/'linearization.npz'), solver_sha256=sha256(output/'solver.json'),
        original_controls=complete['original_controls'], refined_controls=complete['refined_controls'], quality_approved=False))
    save(output/'pipeline.json', dict(status='complete', proposal_available=step is not None, quality_approved=False))
    print(dict(status='complete', proposal_available=step is not None, solver=solver), flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('refinement', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--wait-seconds', type=int, default=0); args = parser.parse_args()
    if args.wait_seconds < 0: parser.error('Nonnegative worker wait required')
    deadline = time.monotonic()+args.wait_seconds; announced = False
    while True:
        with ExitStack() as stack:
            try: stack.enter_context(worker_lock())
            except RuntimeError as error:
                if str(error) != 'Another local action job is running' or time.monotonic() >= deadline: raise
                if not announced: print(dict(status='waiting_for_existing_worker', maximum_wait_seconds=args.wait_seconds), flush=True); announced = True
            else:
                with threadpool_limits(limits=1): run(args.refinement, args.output)
                break
        time.sleep(min(5., max(0., deadline-time.monotonic())))
