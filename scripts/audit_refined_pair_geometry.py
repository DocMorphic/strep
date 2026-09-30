"""Fresh full-mesh and engine observations for an explicitly reviewed refinement."""
import argparse
import math
import os
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now


def selected_trial(audit, index):
    audit = Path(audit).resolve(); result = read(audit/'result.json'); request = read(audit/'request.json')
    if type(index) is not int or index < 0: raise ValueError('Nonnegative trial index required')
    if result['status'] != 'complete': raise ValueError('Completed export audit required')
    for name in ['request', 'trials']:
        if sha256(audit/(name+'.json')) != result[name+'_sha256']: raise ValueError('Export audit changed')
    trials = read(audit/'trials.json')
    if index >= len(trials): raise ValueError('Trial index outside export audit')
    trial = trials[index]; folder = audit/f'trial-{index}'
    if read(folder/'review.json') != trial: raise ValueError('Trial record differs from completed audit')
    if trial['preliminary_checks_pass'] is not True or len(trial['actors']) != 2 or len(trial['independent_rates']) != 2:
        raise ValueError('Passing two-actor export review required')
    limits = list(trial['retained_surface'].values())
    if not limits or any(not math.isfinite(x) or x < 0 or x > 1e-6 for x in limits): raise ValueError('Retained surface check failed')
    actors = [r['actor'] for r in trial['actors']]
    if len(set(actors)) != 2 or [r['actor'] for r in trial['independent_rates']] != actors:
        raise ValueError('Matching distinct reviewed actors required')
    for actor, independent in zip(trial['actors'], trial['independent_rates']):
        if actor['preserved'] is not True or actor['rate_failures'] != 0 or independent['failures'] != 0:
            raise ValueError('Export motion or preservation failed')
        path = (folder/actor['path']).resolve()
        if path.parent != folder or sha256(path) != actor['sha256']: raise ValueError('Reviewed export changed')
    return request, trial


def run(audit, index, output):
    import numpy as np
    import psutil
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors, ScenePairProblem
    from timed_rotation_edit import TimedRotationEdit
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from study_scene_pair_fit import exported_geometry
    from run_godot_rig_import import run as engine_run
    audit, output = Path(audit).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh geometry audit required')
    audit_request, trial = selected_trial(audit, index)
    files = {str(audit/name): sha256(audit/name) for name in ['request.json', 'trials.json', 'result.json']}
    files[str(audit/f'trial-{index}/review.json')] = sha256(audit/f'trial-{index}/review.json')
    for path, digest in audit_request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Export audit input changed')
        files[path] = digest
    for name, digest in audit_request['implementation'].items():
        path = audit/'implementation'/name
        if sha256(path) != digest or sha256(ROOT/'scripts'/name) != digest: raise ValueError('Export audit method changed')
        files[str(path)] = digest
    refinement = Path(audit_request['refinement']); refined_request = read(refinement/'request.json')
    study = Path(refined_request['study']); original, _, bound_files = load_bound_study(study); files.update(bound_files)
    _, actors = load_actors(Path(original['prepared_request']).parent)
    if [a['name'] for a in actors] != [r['actor'] for r in trial['actors']]: raise ValueError('Scene actor order changed')
    step = np.asarray(read(refinement/'solver.json')['step'])
    np.testing.assert_array_equal(np.asarray(trial['controls']), step*trial['factor'])
    output.mkdir(); (output/'implementation').mkdir(); (output/'reconstruction').mkdir()
    methods = {}
    for name in sorted(set(audit_request['implementation']) | {'audit_refined_pair_geometry.py', 'run_godot_rig_import.py', 'godot_import_audit.gd'}):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name); methods[name] = sha256(output/'implementation'/name)
    save(output/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    save(output/'pipeline.json', dict(status='processing', stage='Reconstructing reviewed exports'))
    worlds = []; cases = []; offset = 0
    for number, (actor, record, specification) in enumerate(zip(actors, trial['actors'], refined_request['actors'])):
        old = actor['model']; np.testing.assert_array_equal(old.knots, specification['original_knots_s'])
        model = TimedRotationEdit(old.document, old.binary, [old.document['nodes'][n]['name'] for n in old.nodes],
            old.times, old.window, old.protected, knots=specification['refined_knots_s'], limit_degrees=old.limit_degrees)
        copied = output/'reconstruction'/f'actor-{number}.glb'
        model.export(np.asarray(trial['controls'])[offset:offset+model.size], copied); offset += model.size
        if sha256(copied) != record['sha256']: raise ValueError('Refined controls do not reconstruct reviewed export')
        path = audit/f'trial-{index}'/record['path']; files[str(path)] = record['sha256']
        rig = RigAsset.load(copied); sampler = AnimationSampler(rig.document, rig.binary, 0)
        worlds.append(np.array([sampler.sample(t) for t in old.times]))
        for label, source in [('input', actor['source']), ('candidate', copied)]:
            target = output/f'{label}-actor-{number}.glb'; shutil.copyfile(source, target)
            cases.append(dict(id=label+'-'+actor['name'], path=target.name, sha256=sha256(target),
                frames=int(round(sampler.duration*30))+1, fps=30, sample_by_time=True))
    if offset != len(trial['controls']): raise ValueError('Unused refined controls')
    save(output/'manifest.json', dict(cases=cases, quality_approved=False))
    save(output/'request.json', dict(at=now(), export_audit=str(audit), trial_index=index, factor=trial['factor'], inputs=files,
        implementation=methods, manifest_sha256=sha256(output/'manifest.json'),
        scope='Exact export reconstruction, native all-frame engine observations and complete source-vertex partner/floor queries at the unchanged local clock. No continuous collision, visual or release approval.', quality_approved=False))
    save(output/'pipeline.json', dict(status='processing', stage='Checking engine import'))
    engine_run(output, output/'engine')
    samples = [read(study/'source'/name) for name in read(study/'source-index.json')]
    problem = ScenePairProblem(actors, samples)
    save(output/'pipeline.json', dict(status='processing', stage='Checking full mesh at every sampled time', total=len(samples)))
    summary = exported_geometry(problem, worlds, output)
    reasons = []
    if summary['maximum_cap_excess_m'] > 1e-6: reasons.append('fresh_surface_caps')
    if summary['maximum_floor_increase_m'] > 1e-6: reasons.append('floor_regression')
    if summary['source_peak_m']-summary['candidate_peak_m'] < 1e-6: reasons.append('no_peak_improvement')
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Audit input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Audit method changed')
    save(output/'result.json', dict(at=now(), status='complete', geometry=summary, reasons=reasons, accepted_local_step=not reasons,
        request_sha256=sha256(output/'request.json'), manifest_sha256=sha256(output/'manifest.json'),
        engine_verification_sha256=sha256(output/'engine/verification.json'), quality_approved=False))
    save(output/'pipeline.json', dict(status='complete', stage='Full mesh and engine review complete', accepted_local_step=not reasons, quality_approved=False))
    print(dict(status='complete', reasons=reasons, geometry=summary), flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('audit', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--trial', type=int, required=True); args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.audit, args.trial, args.output)
