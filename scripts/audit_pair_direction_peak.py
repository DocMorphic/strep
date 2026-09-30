"""Measure a directional proposal at its source-peak time, retaining failures."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def selected(study, direction, index):
    from continuation_evidence import cumulative_controls
    study = Path(study).resolve(); result = read(study/'result.json')
    if result['status'] != 'complete' or type(index) is not int or index < 0:
        raise ValueError('Completed directional study and nonnegative trial required')
    files = {str(study/'result.json'):sha256(study/'result.json')}
    artifacts = {name.replace('\\', '/'):digest for name,digest in result['artifacts'].items()}
    if len(artifacts) != len(result['artifacts']): raise ValueError('Duplicate artifact aliases')
    for name, digest in artifacts.items():
        path = (study/name).resolve()
        if not path.is_relative_to(study) or sha256(path) != digest:
            raise ValueError('Directional artifact changed or escapes study')
        files[str(path)] = digest
    if not {'request.json', 'variants.json'} <= set(artifacts):
        raise ValueError('Bound request and variants required')
    request = read(study/'request.json')
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Directional input changed')
        files[path] = digest
    for name, digest in request['implementation'].items():
        if artifacts.get('implementation/'+name) != digest:
            raise ValueError('Bound method snapshot required')
    rows = [r for r in read(study/'variants.json') if r['direction'] == direction]
    if len(rows) != 1 or index >= len(rows[0]['trials']): raise ValueError('Unique existing trial required')
    trial = rows[0]['trials'][index]; folder = study/direction
    if folder.resolve().parent != study: raise ValueError('Direction path escapes study')
    names = [f'{direction}/solver.json', f'{direction}/trial-{index}/review.json']
    names += [f'{direction}/trial-{index}/'+a['path'] for a in trial['actors']]
    if not set(names) <= set(artifacts): raise ValueError('Bound solver, review and clips required')
    solver = read(folder/'solver.json')
    if solver['solver'] != rows[0]['solver'] or read(folder/f'trial-{index}/review.json') != trial:
        raise ValueError('Directional review differs')
    names = [a['actor'] for a in trial['actors']]
    if len(names) != 2 or len(set(names)) != 2 or [a['actor'] for a in trial['angular_rates']] != names:
        raise ValueError('Two distinct ordered actors required')
    for actor in trial['actors']:
        clip = (folder/f'trial-{index}'/actor['path']).resolve()
        if clip.parent != (folder/f'trial-{index}').resolve() or sha256(clip) != actor['sha256']:
            raise ValueError('Clip identity differs')
    cumulative_controls(request, solver, trial)
    return request, trial, files


def run(study, output, direction, index):
    from continuation_evidence import load_continuation, parent_trial
    from bound_evidence import bind_inputs
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from refined_reserve_inputs import install_refined_models
    from scene_pair_relinearization import refreshed_problem
    from study_scene_pair_fit import exported_motion
    from verify_scene_pair_fit import rate_check
    from scalar_angular_replay import angular_replay, compare_saved
    from convex_partner_surface import penetration
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh directional peak audit required')
    request, trial, files = selected(study, direction, index)
    source = Path(request['source']); continuation, _, _, required = load_continuation(source)
    parent_trial(continuation); files.update(bind_inputs(required, request['inputs']))
    np.testing.assert_array_equal(request['cumulative_controls'], continuation['cumulative_controls'])
    parent = Path(continuation['study']); original, _, required = load_bound_study(parent)
    files.update(bind_inputs(required, request['inputs']))
    _, actors = load_actors(Path(original['prepared_request']).parent)
    old_models = [a['model'] for a in actors]
    install_refined_models(actors, original['curve_actors'])
    samples = [read(parent/'source'/n) for n in read(parent/'source-index.json')]
    current = [read(source/'current'/n) for n in read(source/'current-index.json')]
    problem, refreshed = refreshed_problem(actors, samples, current)
    witness = request['objective_witness']; sample = witness['sample']
    if witness['time_s'] != problem.times[sample]: raise ValueError('Peak witness time differs')
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    names = set(request['implementation'])|{'audit_pair_direction_peak.py','verify_scene_pair_fit.py','scalar_angular_replay.py','bound_evidence.py'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name); methods[name] = sha256(output/'implementation'/name)
    save(output/'request.json', dict(at=now(), study=str(study), direction=direction, trial_index=index,
        inputs=files, implementation=methods, sample=sample, time_s=float(problem.times[sample]),
        scope='Exact export reconstruction and independent positional/scalar angular replay; fresh full-mesh depth at only the selected witness time. Original rejected conditions remain. No full-timeline, engine, publication or release approval.',quality_approved=False))
    records, worlds, bounds = exported_motion(problem, trial['controls'], output/'reconstruction')
    if records != trial['actors'] or bounds != trial['bounds']: raise ValueError('Decoded export differs')
    surface = refreshed.surface_rows(worlds)
    with np.load(source/'linearization.npz', allow_pickle=False) as linear:
        inside = linear['gaps'][:len(surface['gaps'])] < 0
    plane = float(np.maximum(-surface['gaps']-surface['depth_caps'],0).max(initial=0))
    distance = float(np.maximum(np.linalg.norm(surface['surface_vectors'][inside],axis=1)-surface['depth_caps'][inside],0).max(initial=0))
    if plane != trial['refreshed_plane_excess_m'] or distance != trial['refreshed_distance_excess_m']:
        raise ValueError('Refreshed decoded bounds differ')
    reviews = []
    for actor, old, world, saved, angular in zip(actors, old_models, worlds, records, trial['angular_rates']):
        joints = actor['rig'].joints
        pos = lambda w:w[:,joints,:,:][:,:,:3,3]@actor['rotation'].T+actor['translation']
        rates = rate_check(pos(old.source_world),pos(world),old.times,old.knots)
        if rates['failures'] != saved['rate_failures']: raise ValueError('Independent positional count differs')
        rot = lambda w:w[:,joints,:,:][:,:,:3,:3]
        angular_rates = angular_replay(rot(old.source_world),rot(world),old.times,old.knots)
        compare_saved(angular_rates,angular['rates'])
        reviews.append(dict(actor=actor['name'],positional=rates,angular=angular_rates))
    reasons = []
    if any(r['positional']['failures'] for r in reviews): reasons.append('exported_motion')
    if any(not r['preserved'] for r in records): reasons.append('preservation_or_budget')
    if max(bounds.values()) > 1e-6: reasons.append('original_surface_bounds')
    if any(v['exceeding_observations'] for r in reviews for v in r['angular'].values()): reasons.append('exported_angular_motion')
    if plane > 1e-6: reasons.append('refreshed_surface_planes')
    if distance > 1e-6: reasons.append('refreshed_surface_distance')
    if trial['reasons'] != reasons or trial['preliminary_pass'] != (not reasons):
        raise ValueError('Independent classification differs')
    save(output/'replay.json',dict(actors=reviews,reasons=reasons,exact_exports=2))
    print(dict(phase='replayed', reasons=reasons),flush=True)
    points = [a['rig'].vertices(w[sample])@a['rotation'].T+a['translation'] for a,w in zip(actors,worlds)]
    geometry = []
    for s,t in [(0,1),(1,0)]:
        geometry.append(dict(source=s,target=t,**penetration(points[s],points[t],actors[t]['faces'])))
        save(output/'geometry.json',geometry); print(dict(phase='geometry',directions=len(geometry)),flush=True)
    for path,digest in files.items():
        if sha256(path) != digest: raise ValueError('Peak audit input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Peak audit method changed')
    save(output/'result.json',dict(at=now(),status='complete',sample=sample,time_s=float(problem.times[sample]),
        raw_source_depth_m=max(d['maximum_depth_m'] for d in samples[sample]['directions']),
        base_continuous_depth_m=max(d['maximum_depth_m'] for d in current[sample]['directions']),
        candidate_depth_m=max(d['max_depth_m'] for d in geometry),reasons=reasons,
        request_sha256=sha256(output/'request.json'),replay_sha256=sha256(output/'replay.json'),geometry_sha256=sha256(output/'geometry.json'),
        full_timeline_geometry_checked=False,accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--direction',required=True);p.add_argument('--trial',type=int,required=True);a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(a.study,a.output,a.direction,a.trial)
