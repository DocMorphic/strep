"""Several diagnosed windows with one original budget and whole-clip evaluation."""
import argparse
import os
import shutil
from pathlib import Path
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from action_worker_lock import worker_lock
from audit_authoring_intent import check_files
from study_coupled_breadth_population import verify_completion, snapshot
from study_coupled_breadth_block import make_problem
from coupled_breadth_conic import constraints
from coupled_clip_windows import choose_windows
from conic_root_descent import solve
from audit_coupled_breadth import audit
from verify_authored_root_correction import samples
from rig_loop import encode
from run_godot_rig_import import run as engine_import
from verify_coupled_start import verify_start


def metrics(path, frames, root, original_peak):
    _, world = samples(path, frames)
    acceleration = np.linalg.norm(np.diff(world[::2, root, :3, 3], n=2, axis=0)*900, axis=1)
    excess = np.maximum(acceleration-original_peak, 0.)
    return acceleration, dict(peak_m_s2=float(acceleration.max()), objective=float(excess@excess),
                             failing_centers=(np.flatnonzero(acceleration > original_peak+.0036)+1).tolist())


def verify_sequence(folder):
    done = read(folder/'completion.json')
    for field, name in [('request', 'request.json'), ('audit', 'audit.json'), ('comparison', 'comparison.json'), ('engine', 'engine/verification.json')]:
        if done[field+'_sha256'] != sha256(folder/name):
            raise ValueError('Completed sequence proof changed')
    audit_proof = read(folder/'audit.json')
    if audit_proof['candidate_sha256'] != sha256(folder/'take/candidate/character.glb'):
        raise ValueError('Completed sequence candidate changed')
    if audit_proof['source_sha256'] != sha256(folder/'source/candidate/character.glb'):
        raise ValueError('Completed sequence source changed')
    return done


def prepare(parent, output, previous=None):
    if output.exists():
        raise ValueError('Preserve previous sequence study')
    done = read(parent/'completion.json')
    if done['request_sha256'] != sha256(parent/'request.json') or done['results_sha256'] != sha256(parent/'results.json'):
        raise ValueError('Parent population changed')
    rows = read(parent/'results.json')['rows']
    if len(rows)!=9 or any(r['status']!='accepted' for r in rows):
        raise ValueError('Complete nine-case corrected population required')
    previous_rows = {}
    if previous is not None:
        prior_done, prior_request = read(previous/'completion.json'), read(previous/'request.json')
        if prior_done['request_sha256'] != sha256(previous/'request.json') or prior_done['results_sha256'] != sha256(previous/'results.json') or prior_done['failed']:
            raise ValueError('Complete unchanged prior sequence required')
        if prior_request['parent_completion_sha256'] != sha256(parent/'completion.json'):
            raise ValueError('Prior sequence starts from another population')
        previous_rows = {r['id']:r for r in read(previous/'results.json')['rows']}
        if set(previous_rows) != {r['id'] for r in rows}:
            raise ValueError('Previous sequence denominator differs')
    output.mkdir(parents=True)
    methods = snapshot(output)
    for name in [Path(__file__).name, 'coupled_clip_windows.py', 'verify_coupled_start.py']:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        methods[name] = sha256(output/'implementation'/name)
    cases = []
    for row in rows:
        source = Path(row['folder'])
        verify_completion(source)
        if row['completion_sha256'] != sha256(source/'completion.json'):
            raise ValueError('Selected parent changed')
        request = read(source/'request.json')
        check_files(source/'source', request['source_files'])
        folder = output/'takes'/row['id']
        folder.mkdir(parents=True)
        shutil.copytree(source/'source', folder/'source')
        shutil.copyfile(source/'parameters.npz', folder/'starting-parameters.npz')
        shutil.copyfile(source/'take/candidate/character.glb', folder/'starting.glb')
        spec = read(folder/'source/spec.json')
        peak = request['target']['limit_m_s2']
        acceleration, before = metrics(folder/'starting.glb', spec['frames'], spec['root_node'], peak)
        windows = choose_windows(acceleration, peak, spec['frames'], max_blocks=4)
        envelope = read(source/'envelope.json')
        # Keep earlier root improvements as well as the original source cap.
        envelope['root_safety_caps_m_s2'] = np.minimum(envelope['root_safety_caps_m_s2'], acceleration+.0036).tolist()
        save(folder/'envelope.json', envelope)
        request.update(frames=request['frames'], target=dict(centers=list(range(1, spec['frames']-1)), limit_m_s2=peak),
                       windows=windows, starting_metrics=before, maxiter=6, linear_screen=True,
                       max_blocks=4, sample_clock='float32', reference_parameters='Original whole-support source; never reset between windows.')
        save(folder/'request.json', request)
        reuse = None
        if row['id'] in previous_rows and previous_rows[row['id']]['status']=='accepted':
            old_row = previous_rows[row['id']]
            reuse = Path(old_row.get('selected_folder', str(previous/'takes'/row['id'])))
            proof = verify_sequence(reuse)
            if not proof['accepted'] or old_row['completion_sha256'] != sha256(reuse/'completion.json'):
                raise ValueError('Previously accepted sequence changed')
            if sha256(reuse/'starting.glb') != sha256(folder/'starting.glb'):
                raise ValueError('Previous sequence start differs')
        cases.append(dict(id=row['id'], parent=str(source), parent_completion_sha256=sha256(source/'completion.json'),
                          reuse_folder=str(reuse) if reuse else None, reused_row=previous_rows.get(row['id']) if reuse else None,
                          files={n: sha256(folder/n) for n in ['request.json', 'envelope.json', 'starting.glb', 'starting-parameters.npz']}))
    request = dict(at=now(), parent=str(parent), parent_completion_sha256=sha256(parent/'completion.json'), cases=cases,
                   implementation=methods, resources=read(parent/'request.json')['resources'],
                   scope='All nine cases, up to four preselected peak windows and six bounded conic iterations each, from verified current clips. Original total edit budgets; original source contact/geometry caps; root caps also preserve starting motion. Whole-clip error reduction must exceed 0.1% of starting error. No quality approval.')
    if previous is not None:
        request.update(previous=str(previous), previous_completion_sha256=sha256(previous/'completion.json'),
                       retry_scope='Keep all previously independently accepted sequences; rerun only rejected cases with matched float32 sampling clocks. Audit limits unchanged.')
    save(output/'request.json', request)
    save(output/'freeze.json', dict(request_sha256=sha256(output/'request.json')))
    save(output/'results.json', dict(rows=[dict(id=c['id'], status='pending') for c in cases], quality_approved=False))
    save(output/'pipeline.json', dict(status='prepared', at=now()))
    print('Prepared nine cases,', sum(len(read(output/'takes'/c['id']/'request.json')['windows']) for c in cases), 'windows', flush=True)


def fit_case(folder, request):
    values = np.load(folder/'starting-parameters.npz')['parameters'].copy()
    touched = set(request['frames'])
    blocks = []
    for index, window in enumerate(request['windows']):
        block_request = {**request, 'frames': window['frames']}
        problem = make_problem(folder, block_request, initial_parameters=values)
        if index==0:
            save(folder/'start-verification.json', verify_start(problem, folder/'starting.glb'))
        def progress(row):
            save(folder/'pipeline.json', dict(status='fitting', block=index+1, at=now(), **row))
            print(folder.name, 'block', index+1, row, flush=True)
        values, solver = solve(problem, request['maxiter'], tuple(request['trusts']), progress,
                               constraint_builder=constraints, linear_screen=True)
        save(folder/f'block-{index+1:02d}-solver.json', solver)
        np.savez_compressed(folder/f'block-{index+1:02d}-parameters.npz', parameters=values)
        touched.update(window['frames'])
        blocks.append(dict(window=window, accepted_steps=sum(h['accepted'] for h in solver['history']),
                           objective_before=solver['objective_before'], objective_after=solver['objective_after']))
    if not blocks:
        raise ValueError('No remaining diagnosed work')
    save(folder/'blocks.json', blocks)
    np.savez_compressed(folder/'parameters.npz', parameters=values)
    take = folder/'take'
    take.mkdir()
    shutil.copytree(folder/'source/input', take/'input')
    (take/'candidate').mkdir()
    for name in ['spec.json', 'request.json']:
        shutil.copyfile(folder/'source'/name, take/name)
    shutil.copyfile(folder/'source/candidate/contacts.json', take/'candidate/contacts.json')
    world = np.array([problem.fitter.pose(f, x)[0] for f, x in enumerate(values)])
    animated = {c['target']['node'] for c in problem.fitter.rig.document['animations'][0]['channels']}|set(problem.fitter.nodes)
    times, _ = encode(problem.fitter.rig, world, animated, problem.root, take/'candidate/character.glb', 'Whole-clip coupled development candidate')
    save(take/'candidate/root-motion.json', dict(node=problem.root, times_s=times.tolist(), positions_m=world[:, problem.root, :3, 3].tolist(),
                                              rotations_xyzw=Rotation.from_matrix(world[:, problem.root, :3, :3]).as_quat().tolist()))
    proof = audit(take, folder/'source/candidate/character.glb', sorted(touched), request['target']['centers'], request['target']['limit_m_s2'])
    after_acceleration, after = metrics(take/'candidate/character.glb', len(values), problem.root, request['target']['limit_m_s2'])
    before_acceleration, before = metrics(folder/'starting.glb', len(values), problem.root, request['target']['limit_m_s2'])
    preserve_starting_root = bool(np.all(after_acceleration <= before_acceleration+.0036))
    improved = after['objective'] < before['objective']-max(1e-9, .001*before['objective'])
    accepted = proof['all_guards_passed'] and preserve_starting_root and improved
    save(folder/'audit.json', proof)
    save(folder/'comparison.json', dict(before=before, after=after, preserve_starting_root=preserve_starting_root,
                                      useful_whole_clip_improvement=improved, accepted=accepted, quality_approved=False))
    save(folder/'manifest.json', dict(cases=[dict(id=name, path=str(path.resolve()), sha256=sha256(path), frames=len(values), fps=30, sample_by_time=True)
         for name, path in [('starting', folder/'starting.glb'), ('candidate', take/'candidate/character.glb')]]))
    engine_import(folder, folder/'engine')
    save(folder/'completion.json', dict(at=now(), request_sha256=sha256(folder/'request.json'), audit_sha256=sha256(folder/'audit.json'),
         comparison_sha256=sha256(folder/'comparison.json'), engine_sha256=sha256(folder/'engine/verification.json'), accepted=accepted, quality_approved=False))
    save(folder/'pipeline.json', dict(status='complete', accepted=accepted, at=now()))
    return dict(status='accepted' if accepted else 'no_accepted_correction', before=before, after=after, accepted_steps=sum(b['accepted_steps'] for b in blocks),
                blocks=len(blocks), all_guards_passed=proof['all_guards_passed'], preserve_starting_root=preserve_starting_root, engine_actor_frames=2*len(values),
                completion_sha256=sha256(folder/'completion.json'))


def run(output):
    request = read(output/'request.json')
    if read(output/'pipeline.json')['status']!='prepared' or read(output/'freeze.json')['request_sha256']!=sha256(output/'request.json'):
        raise ValueError('Fresh frozen sequence required')
    if sha256(Path(request['parent'])/'completion.json') != request['parent_completion_sha256']:
        raise ValueError('Parent changed')
    if 'previous' in request and sha256(Path(request['previous'])/'completion.json') != request['previous_completion_sha256']:
        raise ValueError('Previous sequence changed')
    check_files(ROOT/'scripts', request['implementation'])
    check_files(output/'implementation', request['implementation'])
    check_files(Path('.'), request['resources'])
    save(output/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    results = read(output/'results.json')
    with worker_lock(), threadpool_limits(limits=1):
        for case, row in zip(request['cases'], results['rows']):
            folder = output/'takes'/case['id']
            row['status']='processing'
            save(output/'results.json', results)
            save(output/'pipeline.json', dict(status='processing', case=case['id'], at=now()))
            try:
                check_files(folder, case['files'])
                child = read(folder/'request.json')
                check_files(folder/'source', child['source_files'])
                if case.get('reuse_folder'):
                    reused = Path(case['reuse_folder'])
                    verify_sequence(reused)
                    if sha256(reused/'completion.json') != case['reused_row']['completion_sha256']:
                        raise ValueError('Frozen reused sequence changed')
                    row.update(case['reused_row'], reused=True, selected_folder=str(reused), engine_actor_frames=0)
                else:
                    row.update(fit_case(folder, child), reused=False, selected_folder=str(folder))
                check_files(folder, case['files'])
                check_files(folder/'source', child['source_files'])
            except Exception as exc:
                row.update(status='failed', error=str(exc))
            save(output/'results.json', results)
            print(case['id'], row['status'], flush=True)
    check_files(ROOT/'scripts', request['implementation'])
    check_files(Path('.'), request['resources'])
    rows = results['rows']
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), results_sha256=sha256(output/'results.json'),
         accepted=sum(r['status']=='accepted' for r in rows), failed=sum(r['status']=='failed' for r in rows),
         new_engine_actor_frames=sum(r.get('engine_actor_frames', 0) for r in rows), quality_approved=False))
    save(output/'pipeline.json', dict(status='complete_with_failures' if any(r['status']=='failed' for r in rows) else 'complete', at=now()))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('output', type=Path)
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    if args.command=='prepare':
        prepare(args.parent.resolve(), args.output.resolve(), args.previous.resolve() if args.previous else None)
    else:
        run(args.output.resolve())
