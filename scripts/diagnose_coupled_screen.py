"""Matched full-row/screened proposals at every stopped coupled population case."""
import argparse
import os
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from action_worker_lock import worker_lock
from study_coupled_breadth_population import verify_completion, snapshot
from study_coupled_breadth_block import make_problem
from coupled_breadth_conic import constraints
from conic_root_descent import direction


def run(parent, output):
    if output.exists():
        raise ValueError('Preserve prior diagnostic')
    complete = read(parent/'completion.json')
    if complete['results_sha256'] != sha256(parent/'results.json') or complete['request_sha256'] != sha256(parent/'request.json'):
        raise ValueError('Completed population changed')
    cases = []
    for row in read(parent/'results.json')['rows']:
        folder = Path(row['folder'])
        verify_completion(folder)
        solver = read(folder/'solver.json')
        if solver['history'][-1]['accepted']:
            continue
        cases.append(dict(id=row['id'], folder=str(folder), files={n: sha256(folder/n) for n in ['parameters.npz', 'solver.json', 'request.json', 'completion.json']}))
    output.mkdir(parents=True)
    implementation = snapshot(output)
    name = Path(__file__).name
    shutil.copyfile(__file__, output/'implementation'/name)
    implementation[name] = sha256(__file__)
    request = dict(parent=str(parent), parent_completion_sha256=sha256(parent/'completion.json'), cases=cases,
                   resources=read(parent/'request.json')['resources'], implementation=implementation,
                   method='Both full and safely screened affine rows, all three fixed trusts and eight original safeguard fractions, at every stopped final point. No retained-motion replacement.', at=now())
    save(output/'request.json', request)
    save(output/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    check_files(Path('.'), request['resources'])
    results = []
    with worker_lock(), threadpool_limits(limits=1):
        for case in cases:
            save(output/'pipeline.json', dict(status='processing', case=case['id'], at=now()))
            folder = Path(case['folder'])
            check_files(folder, case['files'])
            child = read(folder/'request.json')
            check_files(folder/'source', child['source_files'])
            problem = make_problem(folder, child)
            values = np.load(folder/'parameters.npz')['parameters']
            x = values[np.ix_(problem.frames, problem.free)].ravel()
            initial = problem.evaluate(x)
            if initial[2].min() < -1e-8 or not problem.geometric_guard(values):
                raise ValueError('Saved final source no longer feasible')
            attempts = []
            for trust in child['trusts']:
                for screened in [False, True]:
                    started = time.perf_counter()
                    delta, proof = direction(problem, x, trust, constraint_builder=constraints, linear_screen=screened)
                    proof.update(screened=screened, elapsed_s=time.perf_counter()-started, trials=[])
                    if delta is not None and proof['predicted_objective_change'] < 0:
                        proof['proposed_delta'] = delta.tolist()
                        for i in range(8):
                            alpha = .5**i
                            trial = problem.evaluate(x+alpha*delta)
                            feasible = bool(np.isfinite(trial[0]) and np.isfinite(trial[2]).all() and trial[2].min() >= -1e-8)
                            geometry = problem.geometric_guard(trial[5]) if feasible else False
                            improved = trial[0] < initial[0]-1e-9
                            proof['trials'].append(dict(alpha=alpha, objective=trial[0], minimum_constraint=float(trial[2].min()),
                                                        feasible=feasible, geometry=geometry, accepted=bool(feasible and geometry and improved)))
                    attempts.append(proof)
                    print(case['id'], trust, 'screened' if screened else 'full', proof['status'], sum(t['accepted'] for t in proof['trials']), flush=True)
            results.append(dict(id=case['id'], objective_before=initial[0], attempts=attempts))
            save(output/'results.json', dict(rows=results, quality_approved=False))
            check_files(folder, case['files'])
    check_files(ROOT/'scripts', implementation)
    check_files(output/'implementation', implementation)
    check_files(Path('.'), request['resources'])
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), results_sha256=sha256(output/'results.json'),
         tested_cases=len(results), proposal_count=sum(len(r['attempts']) for r in results), quality_approved=False))
    save(output/'pipeline.json', dict(status='complete', at=now()))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('parent', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        run(args.parent.resolve(), args.output.resolve())
    except Exception as exc:
        if args.output.exists():
            save(args.output/'failure.json', dict(at=now(), error=str(exc)))
        raise
