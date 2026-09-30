"""Replay margin rows with explicit stencils, then measure the new direction."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from coupled_pair_problem import PairProblem


def replay_rows(positions, reference, frames, windows, affected, active):
    """Independent row-order replay, without the fitter's motion_rows helper."""
    norms, caps, orders = [], [], []
    for order in [1, 2]:
        if order == 1:
            values = (positions[1:]-positions[:-1])*120
            original = (reference[1:]-reference[:-1])*120
        else:
            values = (positions[2:]-2*positions[1:-1]+positions[:-2])*14400
            original = (reference[2:]-2*reference[1:-1]+reference[:-2])*14400
        clock = frames[:-order]+order/8
        for index, time in enumerate(clock):
            if not any(active[index:index+order+1]):
                continue
            covering = [(clock >= start) & (clock <= end) for start, end in windows.values() if start <= time <= end]
            if not covering:
                raise ValueError('Uncovered changed stencil')
            for joint in affected:
                norms.append(float(np.sqrt(np.sum(values[index, joint]**2))))
                caps.append(min(float(np.sqrt(np.sum(original[mask, joint]**2, axis=1)).max()) for mask in covering))
                orders.append(order)
    return np.array(norms), np.array(caps), np.array(orders)


def run(calibration, original_audit, study, audit, witnesses, output):
    calibration, original_audit, study, audit, output = map(lambda p:Path(p).resolve(), [calibration, original_audit, study, audit, output])
    if output.exists():
        raise ValueError('Preserve previous reserve review')
    problem = PairProblem(witnesses)
    cr, cp = read(calibration/'result.json'), read(calibration/'request.json')
    inputs = {**problem.inputs, **cp['inputs']}
    if cr['status'] != 'complete' or cr['request_sha256'] != sha256(calibration/'request.json') or cr['reserve_sha256'] != sha256(calibration/'reserve.npz'):
        raise ValueError('Completed calibration required')
    for folder in [original_audit, audit]:
        proof, request = read(folder/'verification.json'), read(folder/'request.json')
        if proof['request_sha256'] != sha256(folder/'request.json'):
            raise ValueError('Bound export audit required')
        inputs.update(request['inputs'])
        for name, digest in proof['tracks'].items():
            inputs[str(folder/name)] = digest
        for name in ['verification.json', 'request.json']:
            inputs[str(folder/name)] = sha256(folder/name)
    sr, sp = read(study/'result.json'), read(study/'request.json')
    if sr['status'] != 'complete' or sr['request_sha256'] != sha256(study/'request.json') or sr['solver_sha256'] != sha256(study/'solver.json') or sp['fitting_reserve'] != str(calibration):
        raise ValueError('Matching reserved proposal required')
    inputs.update(sp['inputs'])
    for folder, names in [(calibration, ['request.json','result.json','reserve.npz']), (study,['request.json','result.json','solver.json','linearization.npz','fitting-radii.npz','trials.json'])]:
        for name in names:
            inputs[str(folder/name)] = sha256(folder/name)
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Review input changed')
    linear = dict(np.load(study/'linearization.npz', allow_pickle=False))
    saved = dict(np.load(calibration/'reserve.npz', allow_pickle=False))
    with np.load(cr['linearization_path'], allow_pickle=False) as original:
        for key, value in linear.items():
            np.testing.assert_array_equal(value, original[key])
    indices = np.round(problem.frames*4).astype(int)
    def observations(folder, factors, controls):
        predicted = np.array([np.linalg.norm(linear['vectors'] + (linear['jacobians'] @ (controls*factor)), axis=1) for factor in factors])
        actual = predicted.copy(); cursor = 0
        for actor in problem.actors:
            model = actor['model']; cursor += model.original_vectors.reshape(-1,3).shape[0]
            with np.load(folder/(actor['name']+'-tracks.npz'), allow_pickle=False) as tracks:
                reference = tracks['source'][indices]
                clock = model.base.channels[model.base.nodes[0]][1]
                active = (problem.frames/30 > float(clock[63])) & (problem.frames/30 < float(clock[75]))
                for index in range(len(factors)):
                    norms, caps, orders = replay_rows(tracks[f'exported_{index}'][indices], reference, problem.frames, problem.windows, model.base.affected, active)
                    end = cursor+len(norms)
                    np.testing.assert_allclose(caps, linear['radii'][cursor:end], atol=2e-9, rtol=0)
                    np.testing.assert_array_equal(linear['kinds'][cursor:end], np.where(orders==1,'speed','acceleration'))
                    actual[index,cursor:end] = norms
                cursor = end
        if cursor != len(linear['radii']):
            raise ValueError('Unaccounted rows')
        return predicted, actual
    original_study = Path(cr['linearization_path']).parent
    previous_controls = np.array(read(original_study/'solver.json')['controls'])
    predicted, observed = observations(original_audit, cp['trial_factors'], previous_controls)
    np.testing.assert_allclose(predicted, saved['predicted'], atol=2e-9, rtol=0)
    np.testing.assert_allclose(observed, saved['exported'], atol=2e-9, rtol=0)
    reserve = np.maximum(observed-predicted, 0).max(axis=0)*cp['multiplier']
    reserve[linear['kinds']=='edit'] = 0
    replay_error = float(np.abs(reserve-saved['reserve']).max())
    np.testing.assert_allclose(reserve, saved['reserve'], atol=4e-9, rtol=0)
    trials = read(study/'trials.json')
    new_prediction, new_actual = observations(audit, [t['factor'] for t in trials], np.array(read(study/'solver.json')['controls']))
    new_error = np.maximum(new_actual-new_prediction, 0)
    summaries = {}
    for kind in ['speed','acceleration']:
        mask = linear['kinds']==kind
        excess = new_error[:,mask]-saved['reserve'][mask]
        summaries[kind] = dict(maximum_observed_error=float(new_error[:,mask].max()), reserve_exceedances_over_1e_8=int((excess>1e-8).sum()),
            maximum_reserve_excess=float(max(0., excess.max())), maximum_original_cap_excess=float(max(0.,(new_actual[:,mask]-linear['radii'][mask]).max())))
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Review input changed during replay')
    output.mkdir(); shutil.copyfile(__file__, output/'implementation.py')
    save(output/'verification.json', dict(at=now(), inputs=inputs, implementation_sha256=sha256(__file__),
         replayed_motion_norms=int(len(cp['trial_factors'])*(linear['kinds']!='edit').sum()), maximum_reserve_replay_error=replay_error,
         new_direction=summaries, quality_approved=False,
         scope='Explicit finite-difference row replay and a new proposal direction. Reserve exceedances are reported, not suppressed; final complete-clip decoded acceptance remains separate.'))
    print(summaries, flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['calibration','original_audit','study','audit','witnesses','output']:
        p.add_argument(name,type=Path)
    a=p.parse_args()
    run(a.calibration,a.original_audit,a.study,a.audit,a.witnesses,a.output)
