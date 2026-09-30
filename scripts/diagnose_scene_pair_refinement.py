"""Test denser edit curves with unchanged source witnesses and motion limits."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.linalg import block_diag
from strep import ROOT, read, save, sha256, now
from diagnose_scene_pair_limits import load_bound_study, constraint_population, original_checks, trust_only_bound
from coupled_pair_proposal import solve


def refine_knots(knots, joint_count):
    knots = np.asarray(knots, float)
    if knots.ndim != 1 or not 3 <= len(knots) <= 6 or not np.isfinite(knots).all() or np.any(np.diff(knots) <= 0):
        raise ValueError('Three to six increasing finite original knots required')
    if type(joint_count) is not int or joint_count < 1: raise ValueError('Positive joint count required')
    refined = np.sort(np.r_[knots, (knots[:-1]+knots[1:])/2])
    mapping = np.stack([np.interp(refined[1:-1], knots, np.eye(len(knots))[i]) for i in range(1, len(knots)-1)], axis=1)
    return refined, np.kron(np.eye(joint_count), np.kron(mapping, np.eye(3)))


def run(study, output):
    from scene_pair_problem import load_actors, ScenePairProblem
    from timed_rotation_edit import TimedRotationEdit
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh diagnostic destination required')
    request, original, files = load_bound_study(study)
    prepared = Path(request['prepared_request']).parent
    _, actors = load_actors(prepared)
    angular_policies = None
    if request.get('angular_motion'):
        from angular_motion_rows import AngularMotionRows
        angular_policies = [AngularMotionRows(a['model'], a['rig'].joints) for a in actors]
    rows = [read(study/'source'/name) for name in read(study/'source-index.json')]
    output.mkdir(); (output/'implementation').mkdir()
    names = set(request['implementation']) | {'diagnose_scene_pair_refinement.py', 'diagnose_scene_pair_limits.py'}
    methods = {}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        methods[name] = sha256(output/'implementation'/name)
    mappings = []; descriptions = []; checks = []
    for actor in actors:
        old = actor['model']; knots, mapping = refine_knots(old.knots, len(old.nodes))
        names = [old.document['nodes'][node]['name'] for node in old.nodes]
        model = TimedRotationEdit(old.document, old.binary, names, old.times, old.window, old.protected,
            knots=knots, limit_degrees=old.limit_degrees)
        for before, after in zip(old.entries, model.entries):
            np.testing.assert_array_equal(before['ids'], after['ids'])
            np.testing.assert_array_equal(before['original'], after['original'])
        # A known coarse curve must still be represented, including interpolation
        # around protected native keys. Do not recompute the original rate bins.
        coarse = np.random.default_rng(7801).normal(size=old.size)*1e-3
        error = float(np.abs(old.world(coarse)-model.world(mapping@coarse)).max())
        if error > 1e-12: raise ValueError('Refinement changed an embedded original curve')
        checks.append(dict(actor=actor['name'], embedded_world_error=error, identical_editable_keys=True))
        descriptions.append(dict(actor=actor['name'], original_knots_s=old.knots.tolist(), refined_knots_s=knots.tolist(),
            original_controls=old.size, refined_controls=model.size))
        mappings.append(mapping); actor['model'] = model
        # actor['rates'] deliberately remains the original MotionRows instance:
        # the same row membership, knot-span maxima, sample clock and radii.
    embedding = block_diag(*mappings); np.save(output/'embedding.npy', embedding)
    save(output/'request.json', dict(at=now(), study=str(study), inputs=files, implementation=methods, actors=descriptions,
        preserved_curve_checks=checks, embedding_sha256=sha256(output/'embedding.npy'),
        scope='Nested curve-space diagnosis; fixed original rate population, native key eligibility, contacts, witnesses and source-relative budgets. Affine solve only; no animation export or approval.', quality_approved=False))
    problem = ScenePairProblem(actors, rows)
    print(dict(status='linearizing', controls=problem.size), flush=True)
    linear = problem.linearize(np.zeros(problem.size))
    if angular_policies is not None:
        from scene_pair_angular_constraints import linearize_angular
        linear, angular_proofs = linearize_angular(actors, angular_policies, linear)
        save(output/'angular-derivative-proof.json', angular_proofs)
    for key in ['surface_vectors', 'gaps', 'depth_caps', 'vectors', 'radii']:
        np.testing.assert_allclose(linear[key], original[key], atol=1e-12, rtol=0)
    np.testing.assert_array_equal(linear['kinds'], original['kinds'])
    projection = {}
    for key in ['gap_jacobian', 'surface_jacobians', 'jacobians']:
        projection[key] = float(np.abs(linear[key]@embedding-original[key]).max())
    # Finite-difference derivatives need not be bit-identical in the larger basis.
    # Compare their effect at the declared trust radius, in the same row units.
    trust = np.deg2rad(request['trust_degrees'])
    if max(projection['gap_jacobian'], projection['surface_jacobians'])*trust > 1e-8 or projection['jacobians']*trust > 1e-6:
        raise ValueError('Refined affine model does not preserve the coarse derivatives')
    direction = np.random.default_rng(1729).normal(size=problem.size)*1e-6
    moved = problem.surface_rows([a['model'].world(p) for a, p in zip(actors, problem.split(direction))])
    derivative_error = float(np.abs(moved['gaps']-linear['gaps']-linear['gap_jacobian']@direction).max())
    if derivative_error > 1e-9: raise ValueError('Refined surface derivative failed')
    np.savez_compressed(output/'linearization.npz', **linear)
    population = constraint_population(linear)
    step, solver = solve(**{k: linear[k] for k in ['gaps', 'gap_jacobian', 'depth_caps']},
        **{k: population[k] for k in ['vectors', 'jacobians', 'radii']}, trust=trust, norm_tolerances=population['tolerances'])
    save(output/'solver.json', dict(solver=solver, step=None if step is None else step.tolist(),
        original_checks=None if step is None else original_checks(linear, population, step, trust),
        derivative_error=derivative_error, coarse_derivative_projection_errors=projection,
        trust_only_bound=trust_only_bound(linear['gaps'], linear['gap_jacobian'], trust)))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Source changed during refinement')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during refinement')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        linearization_sha256=sha256(output/'linearization.npz'), solver_sha256=sha256(output/'solver.json'),
        original_controls=embedding.shape[1], refined_controls=embedding.shape[0], quality_approved=False))
    print(dict(status='complete', proposed=step is not None, predicted_peak_mm=solver['predicted_peak_m']*1000), flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.study, args.output)
