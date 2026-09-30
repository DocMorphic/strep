"""Audit the completed hand study's rounded-motion derivatives at fixed controls."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(study, output):
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
    from finite_difference_audit import audit
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh derivative audit required')
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
    objective = HandWitnessObjective([BoundSkin(rig) for rig in sources], actors, read(study / 'witnesses.json'))
    def evaluate(normalized):
        controls = normalized * scale
        evaluated = [model.evaluate_vector(controls) for model in models]
        world = [entry[0] for entry in evaluated]
        parts = [features(w, rig.joints) for w, rig in zip(world, sources)]
        payload = {key: np.concatenate([part[key] for part in parts], axis=1) for key in ['positions', 'rotations']}
        values = [(bound[ids[0]:ids[0]+len(value)] + .9*caps.tolerance - value)
                  / np.maximum(bound[ids[0]:ids[0]+len(value)], floor)
                  for value, bound, floor in zip(measures(payload, caps.dt), caps.caps, [.01, 1., .01, 1.])]
        depth = max(0., float(-objective.gaps(world).min()))
        return np.r_[np.concatenate([v.ravel() for v in values]),
                     (45.+1e-4-max(row[1] for row in evaluated))/45.,
                     margins(controls, native, plan['guide_rate_limits']), depth/.02]
    chosen = read(study / 'selected.json'); point = np.asarray(chosen['controls']) / scale
    replay = evaluate(point)
    if abs(replay[-1]*.02-chosen['witness_peak_m']) > 1e-10 or abs(replay[:-1].min()-chosen['minimum_margin']) > 1e-10:
        raise ValueError('Reconstructed diagnostic differs from selected optimizer measurement')
    groups = []; cursor = 0
    for name, order in zip(['positional_speed', 'positional_acceleration', 'angular_speed', 'angular_acceleration'], [1, 2, 1, 2]):
        stop = cursor + (len(ids)-order)*caps.joints
        groups.append(dict(name=name, start=cursor, stop=stop, is_margin=True)); cursor = stop
    for name, stop, margin in [('native_edit', cursor+1, True), ('guide', len(replay)-1, True), ('witness_depth', len(replay), False)]:
        groups.append(dict(name=name, start=cursor, stop=stop, is_margin=margin)); cursor = stop
    directions = np.random.default_rng(230930).normal(size=(4, len(scale)))
    directions /= np.max(np.abs(directions), axis=1)[:, None]
    steps = [1e-5, 1e-4, 1e-3]; radii = [1e-4, 5e-4]
    output.mkdir(); (output / 'implementation').mkdir(); methods = {}
    for name in sorted(set(request['implementation']) | {'audit_hand_derivatives.py', 'finite_difference_audit.py', 'diagnose_oriented_hand_returns.py'}):
        shutil.copyfile(ROOT / 'scripts' / name, output / 'implementation' / name)
        methods[name] = sha256(output / 'implementation' / name)
    points = dict(zero=np.zeros(len(scale)), selected=point)
    save(output / 'request.json', dict(at=now(), study=str(study), inputs=files, implementation=methods,
        points={name: value.tolist() for name, value in points.items()}, scale=scale.tolist(),
        steps=steps, radii=radii, directions=directions.tolist(), groups=groups,
        selected_measurement_reproduced=True,
        scope='Fixed-point derivative stability and separate directional predictions through float32-authored native rotations. Normalized margins and depth/0.02; no solve, geometry query, gate change or publication.', quality_approved=False))
    outputs = {}
    for name, point in points.items():
        def observe(count):
            if count % 50 == 0: print(dict(phase='derivative_audit', point=name, evaluations=count), flush=True)
        report = audit(evaluate, point, steps, directions, radii, groups, observe)
        save(output / (name+'.json'), report); outputs[name] = sha256(output / (name+'.json'))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Derivative audit input changed')
    for name, digest in methods.items():
        if sha256(ROOT / 'scripts' / name) != digest: raise ValueError('Derivative audit method changed')
    result = dict(at=now(), status='complete', request_sha256=sha256(output / 'request.json'),
                  reports=outputs, accepted_for_publication=False, quality_approved=False)
    save(output / 'result.json', result); print(result, flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.study, args.output)
