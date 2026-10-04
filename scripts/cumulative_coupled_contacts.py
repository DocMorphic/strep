"""Offline repeated native/contact proposals with one final complete geometry audit.

Every edit remains relative to the original curves and source-rate caps.
Intermediate native/contact improvements are provisional, never retained clips.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem, METHODS as FIT_METHODS
from native_surface_model import include_times
from native_scene_geometry import policy_for
from central_coupled_contacts import CentralCoupledContactModel
from coupled_native_contacts import acceptable
from native_contact_norms import score, row_regression
from budgeted_native_conic import direction, solver_identity
from native_geometry_cache import Donor, evaluate_to_cache, methods as geometry_methods

METHODS = sorted(set(FIT_METHODS) | set(geometry_methods()) | {
    'cumulative_coupled_contacts.py', 'central_coupled_contacts.py',
    'coupled_native_contacts.py', 'cached_contact_norms.py', 'budgeted_native_conic.py'})


def settings(iterations, backoffs, trust, difference_step, phase_seconds, maximum_iterations,
             maximum_array_bytes, maximum_logical_bytes):
    if (type(iterations) is not int or not 1 <= iterations <= 4
            or type(backoffs) is not int or not 1 <= backoffs <= 10
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .1
            or type(difference_step) not in (int, float) or not np.isfinite(difference_step) or not 1e-6 <= difference_step <= .01
            or type(phase_seconds) not in (int, float) or not np.isfinite(phase_seconds) or not 1 <= phase_seconds <= 300
            or type(maximum_iterations) is not int or not 1 <= maximum_iterations <= 500
            or type(maximum_array_bytes) is not int or maximum_array_bytes <= 0
            or type(maximum_logical_bytes) is not int or not 1024 <= maximum_logical_bytes <= 1024**4):
        raise ValueError('Explicit bounded iteration, difference, trust, solver and archive settings required')


def conditions(native, contact):
    native, contact = [np.asarray(a, float) for a in (native, contact)]
    if any(a.ndim != 1 or not len(a) or not np.isfinite(a).all() for a in (native, contact)):
        raise ValueError('Complete finite native and contact populations required')
    return dict(native_pass=bool(np.all(native <= 0)), native_failed_rows=int((native > 0).sum()),
                native_maximum_excess=float(native.max()), contact_score=score(contact).tolist(),
                surface_contacts_pass=bool(np.all(contact <= 0)), surface_failed_rows=int((contact > 0).sum()))


def provisional(before_native, after_native, before_contact, after_contact):
    """Strict decoded progress only; deliberately grants no geometry approval."""
    before_native, after_native, before_contact, after_contact = [np.asarray(a, float) for a in
        (before_native, after_native, before_contact, after_contact)]
    old, new = conditions(before_native, before_contact), conditions(after_native, after_contact)
    if before_native.shape != after_native.shape or before_contact.shape != after_contact.shape:
        raise ValueError('Original complete condition populations must match')
    regression = row_regression(before_contact, after_contact)
    guard = bool(np.all(regression <= 0))
    improves = bool(new['contact_score'][0] <= old['contact_score'][0]
                    and new['contact_score'][1] < old['contact_score'][1] - 1e-12)
    return dict(**new, individual_contact_guard_pass=guard,
                maximum_contact_regression=float(np.maximum(regression, 0).max()),
                objective_improves=improves,
                provisional_native_contact_progress=bool(old['native_pass'] and new['native_pass'] and guard and improves),
                full_geometry_checked=False, retained=False)


def run(contacts_path, permissions_path, surface_policy_path, geometry_policy_path, output, *,
        start_controls=None, geometry_donor=None, iterations=3, backoffs=10, trust=.02,
        difference_step=.001, phase_seconds=120., maximum_iterations=200,
        maximum_array_bytes=256*1024**2, maximum_logical_bytes=16*1024**3, progress=None):
    settings(iterations, backoffs, trust, difference_step, phase_seconds, maximum_iterations,
             maximum_array_bytes, maximum_logical_bytes)
    paths = [Path(p).resolve() for p in (contacts_path, permissions_path, surface_policy_path, geometry_policy_path)]
    contacts_path, permissions_path, surface_policy_path, geometry_policy_path = paths
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh cumulative proposal output required')
    with worker_lock(), threadpool_limits(limits=1):
        source = read(contacts_path); digest = sha256(contacts_path)
        scene = SceneContacts(source, contacts_path.parent)
        edits = SceneEdits(read(permissions_path), scene, digest, rotation_storage_policy='source-scale')
        problem = SceneProblem(scene, edits)
        policy = read(geometry_policy_path)
        times = policy_for(policy, scene, digest)[0]
        include_times(problem, times)
        model = CentralCoupledContactModel(problem, read(surface_policy_path), digest, maximum_contact_rows=50000)
        source_native = problem.constraints(problem.initial, problem.source_world)
        source_contact = model.contact.residual(problem.source_world)
        original = conditions(source_native, source_contact)
        if not original['native_pass']:
            raise ValueError('This contact-improvement stage requires originally feasible native conditions')
        inputs = {str(p): sha256(p) for p in paths}; inputs.update(scene.inputs)
        x = problem.initial.copy()
        if start_controls is not None:
            start_controls = Path(start_controls).resolve()
            inputs[str(start_controls)] = sha256(start_controls)
            x = edits.controls(np.load(start_controls, allow_pickle=False)).copy()
        if np.any(x < problem.lower) or np.any(x > problem.upper):
            raise ValueError('Initial cumulative controls must fit the original boxes')
        donor = Donor(geometry_donor) if geometry_donor is not None else None
        implementation = {n: sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True); (output/'implementation').mkdir()
        for n in METHODS:
            shutil.copyfile(ROOT/'scripts'/n, output/'implementation'/n)
        for p, name in zip(paths, ('source-contacts.json', 'permissions.json', 'surface-policy.json', 'geometry-policy.json')):
            shutil.copyfile(p, output/name)
        request = dict(schema='strep-cumulative-coupled-contacts-request-v1', at=now(),
            source_base=str(contacts_path.parent), inputs_sha256=inputs, implementation_sha256=implementation,
            iterations=iterations, backoffs=backoffs, trust=trust, difference_step=difference_step,
            phase_seconds=phase_seconds, maximum_iterations=maximum_iterations, solver=solver_identity(),
            rotation_storage_policy='source-scale', maximum_array_bytes=maximum_array_bytes,
            maximum_logical_bytes=maximum_logical_bytes, geometry_donor=None if donor is None else str(donor.folder),
            original_source_caps_and_authored_limits_preserved=True, intermediate_geometry_approved=False,
            maximum_final_geometry_audits=1, geometry_times=times.tolist(), motion_times=problem.times.tolist(),
            uniform_rate_times=problem.uniform.tolist())
        save(output/'request.json', request)

        generated = {}

        def pipeline(stage, **details):
            record = dict(details, stage=stage, status='processing')
            save(output/'pipeline.json', record)
            if progress is not None:
                progress(record)

        def audit(value, folder):
            folder.mkdir()
            files = {n: folder/(n+'.glb') for n in edits.actors}
            for name, path in files.items():
                edits.export(name, value, path)
            static = {n: edits.audit(n, p, scene.actors[n]['animation_index']) for n, p in files.items()}
            native, worlds = problem.decoded(files, value)
            contact = model.contact.residual(worlds)
            conditions(native, contact)
            np.savez_compressed(folder/'conditions.npz', controls=value, native=native, contact=contact,
                                **{'world_'+n: w for n, w in worlds.items()})
            save(folder/'edit-audits.json', static)
            generated.update({str(p): sha256(p) for p in (*files.values(), folder/'conditions.npz', folder/'edit-audits.json')})
            return files, native, worlds, contact, all(a['passed'] for a in static.values())

        def check():
            model.check_caps(); scene.check_inputs()
            if any(sha256(p) != d for p, d in inputs.items()):
                raise ValueError('Original cumulative source inputs changed')
            if any(sha256(p) != d for p, d in generated.items()):
                raise ValueError('Audited serialized candidate or observations changed')
            if any(sha256(ROOT/'scripts'/n) != d or sha256(output/'implementation'/n) != d for n, d in implementation.items()):
                raise ValueError('Cumulative proposal implementation changed')
            if donor is not None:
                donor.check()

        try:
            caps = {n+'_metric_'+str(i): c for n, rate in problem.caps.items() for i, c in enumerate(rate.caps)}
            np.savez_compressed(output/'source.npz', controls=problem.initial, native=source_native,
                contact=source_contact, times_s=problem.times, rate_times_s=problem.uniform, **caps,
                **{'world_'+n: w for n, w in problem.source_world.items()})
            pipeline('serialized-start')
            files, native, worlds, contact, static = audit(x, output/'start')
            if (not static or not conditions(native, contact)['native_pass']
                    or np.any(row_regression(source_contact, contact) > 0)):
                raise ValueError('Serialized start must preserve every original native and contact guard')
            history = []; steps = 0
            for iteration in range(1, iterations+1):
                if np.all(contact <= 0):
                    break
                folder = output/f'iteration-{iteration}'; folder.mkdir()
                pipeline('complete-coupled-linearization', iteration=iteration)
                system, jac, identity = model.linearize(x, worlds, trust, step=difference_step)
                np.savez_compressed(folder/'model.npz', vectors=system.vectors, caps=system.caps, scales=system.scales,
                    jac_data=jac.data, jac_indices=jac.indices, jac_indptr=jac.indptr, jac_shape=jac.shape)
                save(folder/'model.json', identity)
                pipeline('bounded-conic-proposal', iteration=iteration)
                delta, proposal = direction(system, jac, x, problem.lower, problem.upper, trust,
                    hard_rows=identity['hard_rows'], phase_seconds=phase_seconds, maximum_iterations=maximum_iterations)
                save(folder/'proposal.json', proposal)
                probes = []; chosen = None
                if delta is not None:
                    delta = edits.controls(delta)
                    if np.any(np.abs(delta) > trust + 1e-12):
                        raise ValueError('Solver proposal exceeded the declared trust box')
                    np.save(folder/'direction.npy', delta)
                    for backoff in range(backoffs):
                        label = f'backoff-{backoff}'; fraction = .5**backoff
                        value = np.clip(x + fraction*delta, problem.lower, problem.upper)
                        pipeline('serialized-curve-audit', iteration=iteration, label=label)
                        newfiles, after, newworlds, newcontact, newstatic = audit(value, folder/label)
                        decision = provisional(native, after, contact, newcontact)
                        original_guard = bool(np.all(row_regression(source_contact, newcontact) <= 0))
                        decision.update(label=label, fraction=fraction, static_edit_audit_pass=newstatic,
                            original_contact_guard_pass=original_guard, controls_relative_to_original_source=True)
                        okay = decision['provisional_native_contact_progress'] and newstatic and original_guard
                        decision['provisional_native_contact_progress'] = bool(okay)
                        save(folder/label/'decision.json', decision); probes.append(decision)
                        if okay:
                            x, files, native, worlds, contact = value, newfiles, after, newworlds, newcontact
                            chosen = label; steps += 1; break
                save(folder/'trials.json', probes)
                history.append(dict(iteration=iteration, provisional_step=chosen, solver_status=proposal['status'], trials=len(probes)))
                check()
                if chosen is None:
                    break
            save(output/'history.json', history)
            np.save(output/'provisional-controls.npy', x)
            final = provisional(source_native, native, source_contact, contact)
            geometry = None
            if final['provisional_native_contact_progress']:
                candidate = copy.deepcopy(source)
                for name, entry in candidate['actors'].items():
                    entry['glb'] = str(files[name] if name in files else (contacts_path.parent/entry['glb']).resolve())
                    entry['sha256'] = sha256(entry['glb'])
                save(output/'candidate-contacts.json', candidate)
                new_policy = copy.deepcopy(policy); new_policy['contacts_sha256'] = sha256(output/'candidate-contacts.json')
                save(output/'candidate-geometry-policy.json', new_policy)
                pipeline('final-complete-geometry')
                def geometry_progress(record):
                    pipeline('final-complete-geometry', **record)
                geometry = evaluate_to_cache(output/'candidate-contacts.json', output/'candidate-geometry-policy.json',
                    output/'geometry', donor=donor, progress=geometry_progress,
                    maximum_array_bytes=maximum_array_bytes, maximum_logical_bytes=maximum_logical_bytes)
            keep = acceptable(source_native, native, source_contact, contact, geometry)
            check()
            np.save(output/'retained-controls.npy', x if keep else problem.initial)
            result = dict(schema='strep-cumulative-coupled-contacts-result-v1', at=now(), status='complete',
                request_sha256=sha256(output/'request.json'), provisional_steps=steps, history=history,
                original=original, final=conditions(native, contact), retained_partial_improvement=keep,
                geometry_checked=geometry is not None, complete_geometry_pass=None if geometry is None else geometry['sampled_conditions_pass'],
                candidate_files={n: dict(path=str(p), sha256=sha256(p)) for n, p in files.items()},
                original_selected=True, quality_approved=False, release_approved=False,
                geometry_queries_rerun_by_independent_verifier=False, imported_skin_checked=False,
                self_or_continuous_collision_checked=False, human_reviewed=False,
                files_sha256={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*')
                              if p.is_file() and p not in (output/'result.json', output/'pipeline.json')})
            save(output/'result.json', result)
            save(output/'pipeline.json', dict(status='complete', original_selected=True))
            return result
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error=str(exc), original_selected=True))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('contacts', 'permissions', 'surface_policy', 'geometry_policy', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--start-controls', type=Path)
    parser.add_argument('--geometry-donor', type=Path)
    parser.add_argument('--iterations', type=int, default=3)
    parser.add_argument('--backoffs', type=int, default=10)
    parser.add_argument('--trust', type=float, default=.02)
    parser.add_argument('--difference-step', type=float, default=.001)
    parser.add_argument('--phase-seconds', type=float, default=120.)
    parser.add_argument('--maximum-iterations', type=int, default=200)
    parser.add_argument('--maximum-array-bytes', type=int, default=256*1024**2)
    parser.add_argument('--maximum-logical-bytes', type=int, default=16*1024**3)
    args = vars(parser.parse_args())
    contacts, permissions, surface, geometry, output = [args.pop(k) for k in ('contacts', 'permissions', 'surface_policy', 'geometry_policy', 'output')]
    run(contacts, permissions, surface, geometry, output,
        progress=lambda record: print(record, flush=True), **args)
