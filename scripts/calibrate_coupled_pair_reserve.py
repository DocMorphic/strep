"""Bind empirical curvature/export reserves to one retained local linearization."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from coupled_pair_problem import PairProblem
from coupled_pair_proposal import motion_rows
from coupled_pair_reserve import empirical_reserve, tightened_radii


def run(study, audit, witnesses, output):
    study, audit, output = map(lambda p: Path(p).resolve(), [study, audit, output])
    if output.exists():
        raise ValueError('Preserve previous calibration')
    problem = PairProblem(witnesses)
    result, solver = read(study/'result.json'), read(study/'solver.json')
    review, protocol = read(audit/'verification.json'), read(audit/'request.json')
    if result['status'] != 'complete' or result['request_sha256'] != sha256(study/'request.json') or result['solver_sha256'] != sha256(study/'solver.json'):
        raise ValueError('Completed bound proposal required')
    if review['request_sha256'] != sha256(audit/'request.json') or protocol['inputs'].get(str(study/'solver.json')) != sha256(study/'solver.json'):
        raise ValueError('Matching export replay required')
    if solver['linearization_sha256'] != sha256(study/'linearization.npz'):
        raise ValueError('Linearization changed')
    inputs = {**problem.inputs, **protocol['inputs']}
    for path in [study/'result.json', study/'solver.json', study/'linearization.npz', audit/'request.json', audit/'verification.json']:
        inputs[str(path)] = sha256(path)
    for name, digest in review['tracks'].items():
        inputs[str(audit/name)] = digest
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Calibration input changed')
    linear = dict(np.load(study/'linearization.npz', allow_pickle=False))
    trials = read(study/'trials.json')
    controls = np.asarray(solver['controls'])
    predicted = np.array([np.linalg.norm(linear['vectors'] + np.einsum('nid,d->ni', linear['jacobians'], controls*t['factor']), axis=1) for t in trials])
    observed_parts = []
    indices = np.round(problem.frames*4).astype(int)
    cursor = 0
    for actor in problem.actors:
        model = actor['model']
        edit_count = model.original_vectors.reshape(-1, 3).shape[0]
        observed_parts.append(predicted[:, cursor:cursor+edit_count])
        cursor += edit_count
        with np.load(audit/(actor['name']+'-tracks.npz'), allow_pickle=False) as tracks:
            reference = tracks['source'][indices]
            dummy = np.zeros(reference.shape+(1,))
            clock = model.base.channels[model.base.nodes[0]][1]
            active = (problem.frames/30 > float(clock[63])) & (problem.frames/30 < float(clock[75]))
            source, _, caps, orders = motion_rows(reference, dummy, reference, problem.frames, problem.windows, model.base.affected, active)
            end = cursor+len(caps)
            np.testing.assert_allclose(linear['vectors'][cursor:end], source, atol=2e-10, rtol=0)
            np.testing.assert_array_equal(linear['radii'][cursor:end], caps)
            np.testing.assert_array_equal(linear['kinds'][cursor:end], np.where(orders == 1, 'speed', 'acceleration'))
            norms = []
            for index in range(len(trials)):
                values, _, _, _ = motion_rows(tracks[f'exported_{index}'][indices], dummy, reference, problem.frames, problem.windows, model.base.affected, active)
                norms.append(np.linalg.norm(values, axis=1))
            observed_parts.append(np.array(norms))
            cursor = end
    if cursor != len(linear['radii']):
        raise ValueError('Unaccounted norm rows')
    observed = np.concatenate(observed_parts, axis=1)
    reserve, error = empirical_reserve(predicted, observed, linear['kinds'])
    tightened = tightened_radii(linear['radii'], reserve, linear['kinds'])
    output.mkdir()
    snapshot = output/'implementation'; snapshot.mkdir()
    methods = ['calibrate_coupled_pair_reserve.py', 'coupled_pair_reserve.py', 'coupled_pair_proposal.py', 'coupled_pair_problem.py', 'strep.py']
    for name in methods:
        shutil.copyfile(ROOT/'scripts'/name, snapshot/name)
    np.savez_compressed(output/'reserve.npz', reserve=reserve, positive_error=error, predicted=predicted, exported=observed, tightened_radii=tightened)
    request = dict(at=now(), inputs=inputs, implementation={name:sha256(snapshot/name) for name in methods}, multiplier=2., trial_factors=[t['factor'] for t in trials],
                   scope='Twice the largest observed positive exported-minus-affine norm error per motion row, over four retained directions on one line. No edit reserve, no cap clipping, no universal error bound. Independent final gates unchanged.')
    save(output/'request.json', request)
    stats = {}
    for kind in ['edit', 'speed', 'acceleration']:
        values = reserve[linear['kinds'] == kind]
        stats[kind] = dict(rows=len(values), nonzero=int((values > 0).sum()), maximum=float(values.max(initial=0)))
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Input changed during calibration')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'), reserve_sha256=sha256(output/'reserve.npz'),
         linearization_path=str(study/'linearization.npz'), linearization_sha256=sha256(study/'linearization.npz'), rows=cursor, statistics=stats, quality_approved=False))
    print(stats, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['study', 'audit', 'witnesses', 'output']:
        p.add_argument(name, type=Path)
    a = p.parse_args()
    run(a.study, a.audit, a.witnesses, a.output)
