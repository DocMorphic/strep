"""Offline reserve-guided bridge proposals with unchanged original acceptance.

This is a new edit epoch, not continuation of a previous optimizer. Existing
transition-fit methods and their archived studies remain unchanged.
"""
import argparse
import copy
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

import native_transition_scene_fit as correction
from action_worker_lock import worker_lock
from native_contact_reserve import guided_problem
from native_scene_conic import optimize, solver_identity
from native_scene_fit import merit
from native_scene_contacts import fields
from strep import read, save, sha256, now

SCHEMA = 'strep-native-transition-contact-fit-v1'
SCRIPT_ROOT = Path(__file__).resolve().parent
METHODS = tuple(dict.fromkeys(correction.METHODS + (
    'native_contact_reserve.py', 'native_transition_contact_fit.py')))
require = correction.require
equal = correction.equal


def bound_file(binding, base):
    fields(binding, ('path', 'sha256'), 'bound input file')
    require(isinstance(binding['path'], str) and binding['path'], 'Explicit input path required')
    require(isinstance(binding['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', binding['sha256']),
            'Exact input SHA256 required')
    path = (Path(base) / binding['path']).resolve()
    require(path.is_file() and sha256(path) == binding['sha256'], 'Bound input file changed')
    return path


def prepare(request, base):
    fields(request, ('schema', 'recipe', 'reserve', 'seed'), 'reserve-guided bridge request')
    require(request['schema'] == SCHEMA, 'Reserve-guided bridge schema required')
    recipe_path = bound_file(request['recipe'], base)
    problem = correction.Problem(read(recipe_path), recipe_path.parent)
    seed_path = None if request['seed'] is None else bound_file(request['seed'], base)
    initial = None if seed_path is None else read(seed_path)['controls']
    require(initial is None or (isinstance(initial, list) and all(type(v) in (int, float)
            and np.isfinite(v) for v in initial)), 'Explicit finite numeric seed controls required')
    guide, binding = guided_problem(problem.motion, request['reserve'],
                                    sha256(problem.folder / 'scene.json'), initial=initial)
    return problem, guide, binding, recipe_path, seed_path


def file_tree(folder):
    folder = Path(folder)
    require(folder.is_dir(), 'Complete artifact directory required')
    require(not any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
                    for p in [folder] + list(folder.rglob('*'))), 'Linked artifact trees are not supported')
    paths = [p for p in folder.rglob('*') if p.is_file()]
    require(len(paths) <= 4096 and sum(p.stat().st_size for p in paths) <= 2 * 1024**3,
            'Complete artifact tree exceeds its budget; no partial snapshot')
    return {p.relative_to(folder).as_posix(): sha256(p) for p in paths}


def cap_arrays(problem):
    arrays = {'times_s': problem.motion.uniform}
    for name, cap in problem.motion.caps.items():
        arrays.update({name + '_metric_' + str(i): a for i, a in enumerate(cap.caps)})
    return arrays


def arrays_equal(path, expected):
    with np.load(path, allow_pickle=False) as stored:
        require(set(stored.files) == set(expected) and all(
            stored[n].dtype == a.dtype and stored[n].shape == a.shape
            and stored[n].tobytes() == a.tobytes() for n, a in expected.items()),
            'Complete original observation/cap arrays changed')


def probe(problem, guide, value, folder, label, *, write):
    value = problem.edits.controls(value)
    require(np.all(value >= problem.motion.lower) and np.all(value <= problem.motion.upper),
            'Probe exceeds original control bounds')
    folder = Path(folder)
    paths = {n: folder / (str(i) + '.glb') for i, n in enumerate(problem.edits.actors)}
    with tempfile.TemporaryDirectory() as tmp:
        if write:
            require(not folder.exists(), 'Fresh probe folder required')
            folder.mkdir(parents=True)
        for i, (name, path) in enumerate(paths.items()):
            replay = path if write else Path(tmp) / (str(i) + '.glb')
            problem.edits.export(name, value, replay)
            require(problem.edits.audit(name, replay, problem.scene.actors[name]['animation_index'])['passed'],
                    'Probe exceeds original native edit bounds')
            require(write or sha256(replay) == sha256(path), 'Probe does not replay from original controls')
    original, worlds = problem.motion.decoded(paths, value)
    guided = guide.constraints(value, worlds)
    require(np.array_equal(original[:problem.motion.protected_rows], guided[:guide.protected_rows]),
            'Reserve changed protected original source rows')
    record = dict(label=label, controls=value.tolist(), original_merit=list(merit(original)),
                  guidance_merit=list(merit(guided)),
                  original_source_rows_pass=bool(np.all(original[:problem.motion.protected_rows] <= 0)),
                  original_contact_rows_pass=bool(np.all(original[problem.motion.protected_rows:] <= 0)),
                  files_sha256={n: sha256(p) for n, p in paths.items()})
    if write:
        save(folder / 'probe.json', record)
    else:
        require(equal(read(folder / 'probe.json'), record), 'Decoded probe decisions changed')
    return record, guided, worlds


def write_candidate(problem, value, folder):
    folder = Path(folder)
    (folder / 'actors').mkdir(parents=True)
    spec = copy.deepcopy(problem.spec)
    for i, (name, actor) in enumerate(spec['actors'].items()):
        path = folder / 'actors' / (str(i) + '.glb')
        index = problem.append(name, value, path)
        actor.update(glb='actors/' + str(i) + '.glb', sha256=sha256(path), animation_index=index)
    save(folder / 'scene.json', spec)
    scene, spec, worlds, contacts, arrays, policy, geometry, checks, actors = problem.audit(folder, value, publish=True)
    save(folder / 'contacts-audit.json', contacts)
    np.savez_compressed(folder / 'contact-observations.npz', **arrays)
    save(folder / 'geometry-policy-proposal.json', policy)
    save(folder / 'geometry.json', geometry)
    request = read(problem.folder / 'game-tracks-request.json')
    save(folder / 'game-tracks-request.json', request)
    correction.write_tracks(problem, scene, spec, request, worlds, contacts, folder / 'tracks', sha256(folder / 'scene.json'))
    return checks, actors


def decision(output, problem, binding, checks, actors, final):
    output = Path(output)
    history = read(output / 'optimization.json')['history']
    require(len(history) <= problem.recipe['iterations'], 'Optimizer exceeds authored iteration budget')
    candidate_files = file_tree(output / 'candidate')
    require(set(candidate_files) == set(correction.artifact_names(problem)), 'Complete candidate artifact population required')
    return dict(schema=SCHEMA, status='complete', prepared_sha256=sha256(output / 'prepared.json'),
                binding=binding, initial_controls=read(output / 'probes/start/probe.json')['controls'],
                controls=final['controls'], guidance_final_merit=final['guidance_merit'],
                checks=checks, all_declared_samples_pass=all(checks.values()), actors=actors,
                requested_primary_iteration_budget=problem.recipe['iterations'], actual_primary_iterations=len(history),
                new_edit_epoch=True, optimizer_continuation=False,
                samples=len(problem.times), pose_vertex_population=problem.population,
                original_selected=True, original_clip_libraries_retained=True,
                original_acceptance_limits_unchanged=True, root_observations_are_native_only=True,
                engine_playback_verified=False, quality_approved=False, training_admitted=False, release_approved=False,
                files_sha256={n: sha256(output / n) for n in (
                    'optimization.json', 'source-rate-caps.npz', 'reserve-binding.json')},
                probe_files_sha256=file_tree(output / 'probes'), candidate_files_sha256=candidate_files,
                scope='Offline reserve-guided proposal under original source/phase/guard/edit/contact/geometry limits. '
                      'Explicit seed initializes a new epoch; it grants no inherited optimizer or approval evidence. '
                      'No imported resource, rendered motion, physical interaction, training or human quality approval.')


def run(request_path, output):
    request_path = Path(request_path).resolve()
    output = Path(output).resolve()
    require(not output.exists(), 'Fresh reserve-guided output required')
    with worker_lock(), threadpool_limits(limits=1):
        request_digest = sha256(request_path)
        problem, guide, binding, recipe_path, seed_path = prepare(read(request_path), request_path.parent)
        require(not output.is_relative_to(problem.folder) and not problem.folder.is_relative_to(output)
                and not request_path.is_relative_to(output) and not recipe_path.is_relative_to(output)
                and (seed_path is None or not seed_path.is_relative_to(output)), 'Output must be separate from every input')
        original_files = file_tree(problem.folder)
        problem.scene.check_inputs()
        methods = {n: sha256(SCRIPT_ROOT / n) for n in METHODS}
        solver = solver_identity()
        output.mkdir(parents=True)
        save(output / 'pipeline.json', dict(status='processing', original_selected=True))
        try:
            shutil.copyfile(request_path, output / 'request.json')
            shutil.copyfile(recipe_path, output / 'recipe.json')
            if seed_path is not None:
                shutil.copyfile(seed_path, output / 'seed.json')
            shutil.copytree(problem.folder, output / 'original-transition')
            (output / 'implementation').mkdir()
            for n in methods:
                shutil.copyfile(SCRIPT_ROOT / n, output / 'implementation' / n)
            save(output / 'reserve-binding.json', binding)
            np.savez(output / 'source-rate-caps.npz', **cap_arrays(problem))
            save(output / 'prepared.json', dict(schema=SCHEMA, at=now(), request_original=str(request_path),
                 request_sha256=request_digest, recipe_base=str(recipe_path.parent),
                 recipe_sha256=sha256(recipe_path), seed_sha256=None if seed_path is None else sha256(seed_path),
                 original_files_sha256=original_files, implementation_sha256=methods, conic_solver=solver))
            def evaluate(value, label):
                record, residual, _ = probe(problem, guide, value, output / 'probes' / label, label, write=True)
                if label == 'start':
                    require(record['original_source_rows_pass'], 'Seed violates original protected source conditions')
                return residual
            def anchors(value, label):
                paths = {n: output / 'probes' / label / (str(i) + '.glb') for i, n in enumerate(problem.edits.actors)}
                return problem.motion.decoded(paths, value)[1]
            value, optimization = optimize(guide, evaluate, problem.recipe['iterations'], .02,
                difference_step=.001, difference_source='continuous', protect_source_rows=True,
                protect_contact_rows=True, anchor_worlds=anchors, difference_scheme='central',
                serialized_ray_probes=64, restoration_steps=3, restoration_model='recentered')
            evaluate(value, 'final')
            save(output / 'optimization.json', optimization)
            checks, actors = write_candidate(problem, value, output / 'candidate')
            result = decision(output, problem, binding, checks, actors, read(output / 'probes/final/probe.json'))
            save(output / 'result.json', result)
            save(output / 'completion.json', dict(result_sha256=sha256(output / 'result.json')))
            save(output / 'pipeline.json', dict(status='complete', original_selected=True))
            verify(output)
            return result
        except Exception as exc:
            save(output / 'pipeline.json', dict(status='failed', error=str(exc), original_selected=True))
            raise


def verify(output):
    output = Path(output).resolve()
    prepared = read(output / 'prepared.json')
    require(prepared['schema'] == SCHEMA and set(prepared['implementation_sha256']) == set(METHODS),
            'Complete reserve-guided method population required')
    for n, h in prepared['implementation_sha256'].items():
        require(sha256(SCRIPT_ROOT / n) == sha256(output / 'implementation' / n) == h, 'Reserve-guided method changed')
    require(solver_identity() == prepared['conic_solver'], 'Installed proposal solver changed')
    require(sha256(prepared['request_original']) == sha256(output / 'request.json') == prepared['request_sha256'],
            'Reserve-guided request changed')
    problem, guide, binding, recipe_path, seed_path = prepare(read(output / 'request.json'), Path(prepared['request_original']).parent)
    require(str(recipe_path.parent) == prepared['recipe_base']
            and sha256(recipe_path) == sha256(output / 'recipe.json') == prepared['recipe_sha256'], 'Original recipe changed')
    require(prepared['seed_sha256'] == (None if seed_path is None else sha256(seed_path)), 'Seed binding changed')
    require(not (output / 'seed.json').exists() if seed_path is None else sha256(output / 'seed.json') == prepared['seed_sha256'],
            'Seed snapshot changed')
    require(file_tree(problem.folder) == file_tree(output / 'original-transition') == prepared['original_files_sha256'],
            'Original transition population or snapshot changed')
    problem.scene.check_inputs()
    require(equal(read(output / 'reserve-binding.json'), binding), 'Guidance target or original acceptance changed')
    arrays_equal(output / 'source-rate-caps.npz', cap_arrays(problem))
    result = read(output / 'result.json')
    require(result['quality_approved'] is False and result['release_approved'] is False
            and result['engine_playback_verified'] is False and result['training_admitted'] is False,
            'A proposal cannot approve quality, release, training or engine playback')
    folders = {p.name: p for p in (output / 'probes').iterdir()}
    require({'start', 'final'} <= set(folders) and all(p.is_dir() and
            (name in ('start', 'final') or re.fullmatch(r'[1-9][0-9]*-(?:[0-9]+|(?:recenter|restore|storage|ray)-[0-9]+(?:-[0-9]+)?)', name))
            for name, p in folders.items()), 'Exact optimizer probe folders required')
    expected_probe_files = {'probe.json'} | {str(i) + '.glb' for i in range(len(problem.edits.actors))}
    for label, folder in folders.items():
        require({p.name for p in folder.iterdir()} == expected_probe_files, 'Complete probe artifact population required')
        if label not in ('start', 'final'):
            probe(problem, guide, read(folder / 'probe.json')['controls'], folder, label, write=False)
    start = read(output / 'probes/start/probe.json')
    require(equal(start['controls'], guide.initial.tolist()), 'Initial seed controls changed')
    start, _, _ = probe(problem, guide, guide.initial, output / 'probes/start', 'start', write=False)
    require(start['original_source_rows_pass'], 'Seed violates original protected source conditions')
    value = problem.edits.controls(result['controls'])
    final, _, _ = probe(problem, guide, value, output / 'probes/final', 'final', write=False)
    candidate = output / 'candidate'
    scene, spec, worlds, contacts, arrays, policy, geometry, checks, actors = problem.audit(candidate, value)
    require(equal(read(candidate / 'contacts-audit.json'), contacts)
            and equal(read(candidate / 'geometry-policy-proposal.json'), policy)
            and equal(read(candidate / 'geometry.json'), geometry), 'Original acceptance observations changed')
    arrays_equal(candidate / 'contact-observations.npz', arrays)
    request = read(problem.folder / 'game-tracks-request.json')
    require(equal(read(candidate / 'game-tracks-request.json'), request), 'Transferred timing intent changed')
    with tempfile.TemporaryDirectory() as tmp:
        correction.write_tracks(problem, scene, spec, request, worlds, contacts, Path(tmp) / 'tracks', sha256(candidate / 'scene.json'))
        for n in ('root-motion.json', 'root-observations.npz', 'contacts.json', 'events.json', 'request.json'):
            require(sha256(Path(tmp) / 'tracks' / n) == sha256(candidate / 'tracks' / n), 'Native tracks or unconfirmed events changed')
    require(equal(result, decision(output, problem, binding, checks, actors, final)),
            'Reserve-guided decisions or complete artifact population changed')
    require(equal(read(output / 'completion.json'), dict(result_sha256=sha256(output / 'result.json')))
            and equal(read(output / 'pipeline.json'), dict(status='complete', original_selected=True)),
            'Completed reserve-guided artifact required')
    problem.scene.check_inputs()
    require(file_tree(problem.folder) == prepared['original_files_sha256']
            and sha256(prepared['request_original']) == prepared['request_sha256']
            and sha256(recipe_path) == prepared['recipe_sha256']
            and (seed_path is None or sha256(seed_path) == prepared['seed_sha256']), 'Inputs changed during replay')
    require(all(sha256(SCRIPT_ROOT / n) == sha256(output / 'implementation' / n) == h
                for n, h in prepared['implementation_sha256'].items()), 'Methods changed during replay')
    require(solver_identity() == prepared['conic_solver'], 'Proposal solver changed during replay')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    generate = commands.add_parser('run', help='Create a fresh reserve-guided proposal')
    generate.add_argument('request', type=Path)
    generate.add_argument('output', type=Path)
    replay = commands.add_parser('verify', help='Replay an existing output without solving')
    replay.add_argument('output', type=Path)
    args = parser.parse_args()
    print(verify(args.output) if args.command == 'verify' else run(args.request, args.output))
