"""Resumable native surface correction, with immutable inputs and decoded gates.

Preparation/status imports are lightweight. Numerical work belongs in the guarded
worker, under the shared worker lock. Accepted windows checkpoint atomically;
incomplete and rejected attempts remain on disk. No scene or quality approval.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import time
import uuid
from strep import ROOT, read, save, sha256


def require(condition, message):
    if not condition: raise ValueError(message)


def runtime():
    return dict(python=platform.python_version(), **{name: importlib.metadata.version(name)
                for name in ('numpy', 'scipy', 'threadpoolctl')})


def solver_options(value):
    caps = dict(epochs=100, iterations_per_epoch=1000, floor_batch_size=4096,
                maximum_new_samples_per_epoch=256)
    require(isinstance(value, dict) and set(value) == set(caps), 'Exact solver budgets required')
    require(all(type(value[k]) is int and 1 <= value[k] <= cap for k, cap in caps.items()),
            'Positive bounded integer solver budgets required')
    return dict(value)


def prepare(folder, source, initial, *, clip, solver):
    """Copy inputs once; no source-file or candidate mutation after preparation."""
    folder = Path(folder).resolve()
    require(isinstance(clip, dict), 'Explicit clip configuration required')
    solver = solver_options(solver)
    json.dumps(clip, allow_nan=False)
    methods = {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    versions = runtime()
    source, initial = Path(source).resolve(), Path(initial).resolve()
    hashes = [sha256(p) for p in (source, initial)]
    folder.mkdir(parents=True, exist_ok=False)
    for path, name, digest in zip((source, initial), ('source.glb', 'initial.glb'), hashes):
        shutil.copyfile(path, folder/name)
        require(sha256(path) == sha256(folder/name) == digest, 'Input changed during preparation')
    save(folder/'request.json', dict(schema='strep-surface-clip-job-v1', clip=clip,
         solver=solver, inputs=dict(zip(('source.glb', 'initial.glb'), hashes)),
         methods=methods, runtime=versions, quality_approved=False, release_approved=False))
    save(folder/'prepared.json', dict(request_sha256=sha256(folder/'request.json')))
    return folder


def request_for(folder):
    folder = Path(folder).resolve()
    request = read(folder/'request.json')
    require(sha256(folder/'request.json') == read(folder/'prepared.json')['request_sha256'],
            'Prepared correction request changed')
    require(request['schema'] == 'strep-surface-clip-job-v1', 'Unknown correction protocol')
    require(request['methods'] == {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
            'Correction implementation changed; preserve this job and prepare a new one')
    require(request['runtime'] == runtime(), 'Correction runtime changed')
    require(set(request['inputs']) == {'source.glb', 'initial.glb'}, 'Exact copied inputs required')
    for name, digest in request['inputs'].items():
        require(sha256(folder/name) == digest, 'Copied correction input changed')
    solver_options(request['solver'])
    return request


def artifact(folder, name):
    require(isinstance(name, str) and name and not Path(name).is_absolute(), 'Relative job artifact required')
    path = (folder/name).resolve()
    require(path != folder and path.is_relative_to(folder), 'Artifact escapes correction job')
    return path


def _resume(folder, context, request, attempt):
    """Verify receipt chain, then freshly decode the entire accepted prefix."""
    if not (folder/'state.json').exists():
        initial = context.audit(folder/'initial.glb', [0])
        save(attempt/'incoming-audit.json', initial)
        if not initial['passed']: return None
        state = dict(request_sha256=sha256(folder/'request.json'), current_clip='initial.glb',
                     clip_sha256=request['inputs']['initial.glb'], finalized_through=0,
                     validated_through=0, next_start=0, accepted=[], quality_approved=False,
                     release_approved=False)
        save(folder/'state.json', state)
        return state
    state = read(folder/'state.json')
    require(state['request_sha256'] == sha256(folder/'request.json'), 'Checkpoint request mismatch')
    require(isinstance(state['accepted'], list) and len(state['accepted']) <= len(context.keys)-1,
            'Bounded checkpoint chain required')
    expected_clip, expected_hash, finalized, validated, next_start = 'initial.glb', request['inputs']['initial.glb'], 0, 0, 0
    for receipt in state['accepted']:
        record_path = artifact(folder, receipt['path'])
        require(sha256(record_path) == receipt['sha256'], 'Accepted receipt changed')
        record = read(record_path)
        frames = list(range(next_start, min(next_start+3, len(context.keys)))) if next_start is not None else []
        require(frames and record['frames'] == frames and record['passed'] is True
                and record['previous_clip_sha256'] == expected_hash
                and record['request_sha256'] == state['request_sha256'], 'Invalid accepted window chain')
        for name in ('candidate.glb', 'decoded-audit.json', 'export.json'):
            require(sha256(record_path.parent/name) == record['artifacts'][name], 'Accepted artifact changed')
        audit = read(record_path.parent/'decoded-audit.json')
        export = read(record_path.parent/'export.json')
        require(audit['passed'] is True and audit['frames'] == frames
                and audit['clip_sha256'] == record['artifacts']['candidate.glb']
                and export['unchanged_key_values_verified'] is True
                and export['preserved_through'] == next_start
                and export['edited_keys'] == frames[1:], 'Invalid decoded acceptance evidence')
        expected_clip = (record_path.parent/'candidate.glb').relative_to(folder).as_posix()
        expected_hash = record['artifacts']['candidate.glb']
        validated = frames[-1]
        finalized = validated if validated == len(context.keys)-1 else frames[1]
        next_start = None if finalized == len(context.keys)-1 else frames[1]
    require((state['current_clip'], state['clip_sha256'], state['finalized_through'], state['validated_through'], state['next_start'])
            == (expected_clip, expected_hash, finalized, validated, next_start), 'Checkpoint position differs from accepted chain')
    replay = context.audit(artifact(folder, expected_clip), list(range(validated+1)))
    save(attempt/'resume-audit.json', replay)
    require(replay['passed'], 'Accepted prefix no longer passes decoded checks')
    return state


def _window(context, current, frames, folder, solver):
    import numpy as np
    from surface_pose_feasibility import propose
    from surface_pose_interpolation import SampledPoseWindow
    from surface_step_projection import project_steps
    from surface_pose_key_export import replace_keys
    seed = context.controls(current, frames)
    native, checks, samples, clock = context.build_window(frames, seed)
    bounds = np.asarray(native.bounds).reshape(len(frames), context.width, 2)
    original_rows, original_steps, original_pass = context.dense_check(native, checks, clock, frames, seed.reshape(-1))
    trials = []
    for label in (('current', 'hold', 'velocity') if len(frames) == 3 and not original_pass else ('current',)):
        trial = seed.copy()
        if label == 'hold': trial[2] = trial[1]
        if label == 'velocity':
            trial[2] = seed[1]+(seed[1]-seed[0])*(context.keys[frames[2]]-context.keys[frames[1]])/(context.keys[frames[1]]-context.keys[frames[0]])
        if label != 'current' or not original_pass:
            trial = np.clip(trial, bounds[:, :, 0], bounds[:, :, 1])
        rows, steps, passed = ((original_rows, original_steps, True) if original_pass else
                              context.dense_check(native, checks, clock, frames, trial.reshape(-1)))
        violation = max(max(r['violation'] for r in rows), steps['maximum_root_step_m']/context.settings['root_step_m']-1,
                        steps['maximum_rotation_step_degrees']/context.settings['rotation_step_degrees']-1, 0.)
        trials.append(dict(label=label, controls=trial.tolist(), passed=passed, violation=violation))
    selected = min(trials, key=lambda row: row['violation'])
    best = np.asarray(selected['controls']).reshape(-1)
    save(folder/'seeds.json', dict(selected=selected['label'], trials=trials))
    passed = selected['passed']
    history = []
    if not passed:
        for epoch in range(solver['epochs']):
            window = SampledPoseWindow(native, [v for _, v in sorted(samples.items())])
            window.grow(best, batch_size=solver['floor_batch_size'])
            best, report = propose(window, best, max_iterations=solver['iterations_per_epoch'])
            require(np.array_equal(best[:context.width], seed[0]), 'Frozen incoming key changed')
            additions = window.grow(best, batch_size=solver['floor_batch_size'])
            rows, steps, passed = context.dense_check(native, checks, clock, frames, best)
            projection = None
            if not passed and all(r['numerical_pose_pass'] for r in rows) and not steps['step_pass']:
                trial = project_steps(native.unpack(best), root_step_m=context.settings['root_step_m'],
                    rotation_step_degrees=context.settings['rotation_step_degrees'],
                    root_reserve_m=context.request['fit_step_reserve_m'],
                    rotation_reserve_radians=context.request['fit_step_reserve_radians']).reshape(-1)
                projected_rows, projected_steps, projected_pass = context.dense_check(native, checks, clock, frames, trial)
                projection = dict(passed=projected_pass, controls=trial.tolist(), steps=projected_steps)
                if projected_pass: best, rows, steps, passed = trial, projected_rows, projected_steps, True
            added_times = []
            if not passed:
                for row in sorted(rows, key=lambda r: r['violation'], reverse=True):
                    if len(samples) >= 64: break
                    t = row['time_s']
                    if row['violation'] > 0 and t in checks and t not in samples:
                        samples[t] = checks[t]; added_times.append(t)
                        if len(added_times) == solver['maximum_new_samples_per_epoch']: break
            history.append(dict(epoch=epoch, proposal=report, passed=passed, added_times=added_times,
                                added_floor_vertices=additions, step_projection=projection,
                                failed_samples=sum(not r['numerical_pose_pass'] for r in rows), **steps))
            save(folder/'optimizer-checkpoint.json', dict(controls=native.unpack(best).tolist(),
                 sample_times=sorted(samples), history=history))
            if passed: break
    controls = native.unpack(best)
    export = replace_keys(context.rig, current, root=context.root, rotations=context.nodes,
         edits={f: controls[i] for i, f in enumerate(frames) if i}, preserve_through=frames[0],
         output=folder/'candidate.glb', animation_index=context.animation_index)
    save(folder/'export.json', export)
    audit = context.audit(folder/'candidate.glb', frames)
    save(folder/'decoded-audit.json', audit)
    return audit


def _attempt(folder, *, maximum_windows, soft_seconds):
    """Internal worker entry: caller must hold the shared lock and resource guard."""
    import numpy as np
    from rig_asset import RigAsset
    from surface_clip import SurfaceClip
    require(type(maximum_windows) is int and 1 <= maximum_windows <= 10000, 'Bounded attempt window budget required')
    require(type(soft_seconds) in (int, float) and np.isfinite(soft_seconds) and 0 < soft_seconds <= 3600,
            'Bounded finite attempt duration required')
    folder = Path(folder).resolve(); request = request_for(folder)
    context = SurfaceClip(RigAsset.load(folder/'source.glb'), **request['clip'])
    attempt = folder/'attempts'/uuid.uuid4().hex; attempt.mkdir(parents=True)
    save(attempt/'attempt.json', dict(request_sha256=sha256(folder/'request.json'),
         maximum_windows=maximum_windows, soft_seconds=soft_seconds))
    started = time.monotonic()
    state = _resume(folder, context, request, attempt)
    reason = 'invalid_incoming_pose' if state is None else None
    attempted = 0
    if state is not None:
        while state['next_start'] is not None:
            if attempted >= maximum_windows or time.monotonic()-started >= soft_seconds:
                reason = 'attempt_budget'; break
            start = state['next_start']; frames = list(range(start, min(start+3, len(context.keys))))
            step = attempt/f'window-{start:06d}'; step.mkdir()
            current = RigAsset.load(artifact(folder, state['current_clip']))
            audit = _window(context, current, frames, step, request['solver'])
            attempted += 1
            record = dict(frames=frames, passed=audit['passed'], previous_clip_sha256=state['clip_sha256'],
                 request_sha256=sha256(folder/'request.json'), artifacts={name: sha256(step/name)
                 for name in ('candidate.glb', 'decoded-audit.json', 'export.json')}, quality_approved=False, release_approved=False)
            save(step/'result.json', record)
            require(request_for(folder) == request, 'Request changed during correction')
            if not audit['passed']:
                reason = 'unresolved_window'; break
            end = frames[-1]; final = end if end == len(context.keys)-1 else frames[1]
            state.update(current_clip=(step/'candidate.glb').relative_to(folder).as_posix(),
                         clip_sha256=record['artifacts']['candidate.glb'], finalized_through=final,
                         validated_through=end, next_start=None if final == len(context.keys)-1 else frames[1])
            state['accepted'].append(dict(path=(step/'result.json').relative_to(folder).as_posix(), sha256=sha256(step/'result.json')))
            save(folder/'state.json', state)
        final_audit = context.audit(artifact(folder, state['current_clip']), list(range(state['validated_through']+1)))
        save(attempt/'prefix-audit.json', final_audit)
        require(final_audit['passed'], 'Final decoded prefix check failed')
    require(request_for(folder) == request, 'Request changed during correction')
    complete = state is not None and state['next_start'] is None
    result = dict(status='complete_numerical_candidate' if complete else 'checkpointed' if reason == 'attempt_budget' else 'unresolved',
                  reason=reason, state=state, attempted_windows=attempted, whole_clip_sampled=complete,
                  engine_verified=False, scene_verified=False, quality_approved=False, release_approved=False)
    save(attempt/'result.json', result)
    save(folder/'latest-attempt.json', dict(path=attempt.relative_to(folder).as_posix(), result_sha256=sha256(attempt/'result.json')))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    for name in ('folder', 'source', 'initial', 'config'): prepare_parser.add_argument('--'+name, required=True)
    for name in ('run', 'worker'):
        p = commands.add_parser(name); p.add_argument('--folder', required=True)
        p.add_argument('--maximum-windows', type=int, default=10)
        p.add_argument('--soft-seconds', type=float, default=240)
    args = parser.parse_args()
    if args.command == 'prepare':
        config = read(args.config); prepare(args.folder, args.source, args.initial, **config); return
    if args.command == 'run':
        from run_guarded_job import run
        from resource_admission import ResourcePolicy
        from audit_guarded_job import audit
        folder = Path(args.folder).resolve(); request_for(folder)
        guard = folder/'guards'/uuid.uuid4().hex
        result = run(Path(__file__), guard, ResourcePolicy(expected_rss_bytes=512*1024**2,
            max_tree_rss_bytes=1024*1024**2, max_seconds=min(3600, args.soft_seconds+120), stable_seconds=10, admission_seconds=60),
            worker_args=['worker', '--folder', str(folder), '--maximum-windows', str(args.maximum_windows), '--soft-seconds', str(args.soft_seconds)])
        save(guard/'replay.json', audit(guard))
        print(json.dumps(result))
        return {'complete': 0, 'deferred': 2, 'failed': 1}[result['status']]
    from action_worker_lock import worker_lock
    with worker_lock():
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=1):
            result = _attempt(args.folder, maximum_windows=args.maximum_windows, soft_seconds=args.soft_seconds)
    print(json.dumps(dict(status=result['status'], reason=result['reason'])))


if __name__ == '__main__': raise SystemExit(main())
