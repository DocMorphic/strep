"""Matched single-window comparison for a verified between-key floor blocker."""
import argparse
import os
import shutil
from pathlib import Path
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from action_worker_lock import worker_lock
from study_coupled_breadth_population import snapshot
from study_coupled_clip_sequence import verify_sequence, fit_case, metrics
from study_coupled_breadth_block import make_problem
from coupled_half_floor import HalfFloorConstraints, half_floor_rows, half_floor_values


def prepare(parent, diagnostic, output):
    if output.exists():
        raise ValueError('Preserve previous pilot')
    done = read(parent/'completion.json')
    if done['request_sha256'] != sha256(parent/'request.json') or done['results_sha256'] != sha256(parent/'results.json'):
        raise ValueError('Parent population changed')
    case = 'motion-036-rig-02'
    row = next(r for r in read(parent/'results.json')['rows'] if r['id']==case)
    source = Path(row['selected_folder'])
    verified = verify_sequence(source)
    if not verified['accepted'] or row['completion_sha256'] != sha256(source/'completion.json'):
        raise ValueError('Accepted current source required')
    diagnosis = read(diagnostic)
    if Path(diagnosis['folder']).resolve()!=source.resolve() or diagnosis['block']!=1 or diagnosis['solver_sha256']!=sha256(source/'block-01-solver.json'):
        raise ValueError('Matched stopped-window diagnosis required')
    if not any(not r['measured']['checks']['half_floor'] for r in diagnosis['rows']):
        raise ValueError('No demonstrated half-frame floor failure')
    output.mkdir(parents=True)
    methods = snapshot(output)
    for name in [Path(__file__).name, 'coupled_half_floor.py', 'study_coupled_clip_sequence.py', 'coupled_clip_windows.py', 'verify_coupled_start.py']:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        methods[name]=sha256(output/'implementation'/name)
    old = read(source/'request.json')
    cases = []
    for method in ['keys_only', 'keys_and_halves']:
        folder = output/'takes'/method
        folder.mkdir(parents=True)
        shutil.copytree(source/'source', folder/'source')
        shutil.copyfile(source/'parameters.npz', folder/'starting-parameters.npz')
        shutil.copyfile(source/'take/candidate/character.glb', folder/'starting.glb')
        spec = read(folder/'source/spec.json')
        acceleration, before = metrics(folder/'starting.glb', spec['frames'], spec['root_node'], old['target']['limit_m_s2'])
        envelope = read(source/'envelope.json')
        envelope['root_safety_caps_m_s2'] = np.minimum(envelope['root_safety_caps_m_s2'], acceleration+.0036).tolist()
        save(folder/'envelope.json', envelope)
        touched = sorted(set(old['frames'])|{f for w in old['windows'] for f in w['frames']})
        request = {**old, 'frames':touched, 'windows':[old['windows'][0]], 'starting_metrics':before,
                   'maxiter':6, 'method':method, 'sample_clock':'float32', 'half_derivative_step':1e-5}
        save(folder/'request.json', request)
        cases.append(dict(id=method, files={n:sha256(folder/n) for n in ['request.json','envelope.json','starting.glb','starting-parameters.npz']}))
    folder = output/'takes/keys_and_halves'
    request = read(folder/'request.json')
    values = np.load(folder/'starting-parameters.npz')['parameters']
    with threadpool_limits(limits=1):
        problem = make_problem(folder, {**request, 'frames':request['windows'][0]['frames']}, initial_parameters=values)
        x = values[np.ix_(problem.frames, problem.free)].ravel()
        _, j, model = half_floor_rows(problem, x, False)
        rng = np.random.default_rng(954)
        errors = []
        for _ in range(3):
            d = rng.normal(size=len(x)); d /= np.linalg.norm(d)
            numerical = (half_floor_values(problem, x+1e-6*d, False)-half_floor_values(problem, x-1e-6*d, False))/2e-6
            errors.append(float(np.max(np.abs(numerical-j@d))))
        margins = half_floor_values(problem, x, True)
        preflight = dict(derivative_errors=errors, derivative_threshold=2e-4, minimum_serialized_half_margin=float(margins.min()),
                         actual_geometry=problem.geometric_guard(values), model=model)
    save(output/'preflight.json', preflight)
    if max(errors)>2e-4 or margins.min() < -1e-8 or not preflight['actual_geometry']:
        raise ValueError('Half-floor preflight failed')
    save(output/'request.json', dict(at=now(), parent=str(parent), parent_completion_sha256=sha256(parent/'completion.json'),
         source=str(source), source_completion_sha256=sha256(source/'completion.json'), diagnostic=str(diagnostic), diagnostic_sha256=sha256(diagnostic),
         cases=cases, implementation=methods, resources=read(parent/'request.json')['resources'],
         scope='Both methods start from the same latest verified clip. Same one stopped peak window, six iterations, three trusts/eight fractions, cumulative original budgets and independent whole-clip acceptance. Only extra half-floor proposal rows differ. No quality approval.'))
    save(output/'freeze.json', {n:sha256(output/n) for n in ['request.json','preflight.json']})
    save(output/'results.json', dict(rows=[dict(id=c['id'], status='pending') for c in cases], quality_approved=False))
    save(output/'pipeline.json', dict(status='prepared', at=now()))
    print(preflight, flush=True)


def run(output):
    request = read(output/'request.json')
    if read(output/'pipeline.json')['status']!='prepared':
        raise ValueError('Fresh prepared pilot required')
    check_files(output, read(output/'freeze.json'))
    for field, name in [('parent', 'completion.json'), ('source', 'completion.json')]:
        if sha256(Path(request[field])/name) != request[field+'_completion_sha256']:
            raise ValueError('Frozen parent changed')
    if sha256(Path(request['diagnostic'])) != request['diagnostic_sha256']:
        raise ValueError('Diagnostic changed')
    check_files(ROOT/'scripts', request['implementation']);check_files(output/'implementation', request['implementation'])
    check_files(Path('.'), request['resources'])
    save(output/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    results = read(output/'results.json')
    with worker_lock(), threadpool_limits(limits=1):
        for case, row in zip(request['cases'], results['rows']):
            folder = output/'takes'/case['id']
            save(output/'pipeline.json', dict(status='processing', method=case['id'], at=now()))
            row['status']='processing';save(output/'results.json', results)
            try:
                check_files(folder, case['files'])
                child = read(folder/'request.json')
                check_files(folder/'source', child['source_files'])
                row.update(fit_case(folder, child, proposal_builder_factory=HalfFloorConstraints if case['id']=='keys_and_halves' else None))
                check_files(folder, case['files']);check_files(folder/'source', child['source_files'])
            except Exception as exc:
                row.update(status='failed', error=str(exc))
            save(output/'results.json', results)
            print(case['id'], row['status'], flush=True)
    check_files(ROOT/'scripts', request['implementation']);check_files(Path('.'), request['resources'])
    rows = results['rows']
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), results_sha256=sha256(output/'results.json'),
         failed=sum(r['status']=='failed' for r in rows), new_engine_actor_frames=sum(r.get('engine_actor_frames',0) for r in rows), quality_approved=False))
    save(output/'pipeline.json', dict(status='complete_with_failures' if any(r['status']=='failed' for r in rows) else 'complete', at=now()))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare','run'])
    parser.add_argument('output', type=Path)
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--diagnostic', type=Path)
    args = parser.parse_args()
    if args.command=='prepare':
        prepare(args.parent.resolve(), args.diagnostic.resolve(), args.output.resolve())
    else:
        run(args.output.resolve())
