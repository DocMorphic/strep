"""Independent decoded audit plus coupled-block preservation checks."""
import argparse
from pathlib import Path
import numpy as np
from strep import read, save, sha256, now
from verify_guarded_release import run as decoded_audit
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from reconstruct_descent import reconstruct


def run(folder, output):
    if output.exists(): raise ValueError('Preserve prior audit')
    request = read(folder/'request.json'); freeze = read(folder/'freeze.json')
    for name, key in [('request.json', 'request_sha256'), ('envelope.json', 'envelope_sha256'), ('derivative-proof.json', 'derivative_sha256')]:
        if sha256(folder/name) != freeze[key]: raise ValueError('Frozen block protocol changed')
    if 'conic_sha256' in freeze:
        if sha256(folder/'conic-proof.json') != freeze['conic_sha256'] or not read(folder/'conic-proof.json')['passed']:
            raise ValueError('Conic protocol proof changed or failed')
    if read(folder/'pipeline.json')['status'] != 'complete': raise ValueError('Completed trial required')
    source = Path(request['source']); parameters = np.load(folder/'take/parameters.npz', allow_pickle=False)
    original = np.load(source/'take/parameters.npz', allow_pickle=False)['parameters']
    np.testing.assert_array_equal(parameters['initial'], original)
    changed = parameters['parameters']; frames = np.asarray(request['frames'])
    untouched = np.array([f for f in range(len(original)) if f not in set(frames)])
    np.testing.assert_array_equal(changed[untouched], original[untouched])
    protected = read(folder/'envelope.json')['protected_columns']
    np.testing.assert_array_equal(changed[:, protected], original[:, protected])
    solver = read(folder/'take/solver.json')
    if solver['variable_frames'] != request['frames'] or solver['free_columns'] != [i for i in range(original.shape[1]) if i not in protected]:
        raise ValueError('Optimizer coordinate mapping differs')
    expected = original.copy()
    if solver.get('method') in ['conic_descent','scheduled_conic_descent']:
        expected = reconstruct(original, solver, request, frames, solver['free_columns'])
    elif solver['accepted_fraction'] is not None:
        proposal = np.asarray(solver['proposed_coordinates']).reshape(len(frames), len(solver['free_columns']))
        selected = np.ix_(frames, solver['free_columns'])
        expected[selected] += solver['accepted_fraction']*(proposal-original[selected])
    np.testing.assert_allclose(changed, expected, atol=1e-14, rtol=0)
    output.mkdir(parents=True)
    decoded_audit(folder, output/'decoded.json')
    proof = read(output/'decoded.json')
    samplers = []
    for path in [source/'take/candidate/character.glb', folder/'take/candidate/character.glb']:
        rig = RigAsset.load(path); samplers.append(AnimationSampler(rig.document, rig.binary, 0))
    fps = read(folder/'take/spec.json')['fps']
    unaffected_error = max((float(np.abs(samplers[0].sample(float(np.float32(f/fps)))-samplers[1].sample(float(np.float32(f/fps)))).max()) for f in untouched), default=0.)
    if unaffected_error > 1e-12: raise ValueError('Untouched decoded frames changed')
    # Preserve every passing source event, even if multiple failures remain.
    source_audits = [Path(request['source_audit'])] if 'source_audit' in request else [Path(p) for p in request['inputs'] if p.endswith('guarded-release-serialized-audit-v1.json')]
    if len(source_audits) != 1: raise ValueError('One bound source release audit required')
    if request['inputs'].get(str(source_audits[0])) != sha256(source_audits[0]): raise ValueError('Source audit binding differs')
    source_audit = read(source_audits[0])
    old_events = {(e['side'], e['release_frame']): e for e in source_audit['events']}
    new_events = {(e['side'], e['release_frame']): e for e in proof['events']}
    if old_events.keys() != new_events.keys(): raise ValueError('Release population changed')
    new_failures = [list(key) for key, event in new_events.items() if old_events[key]['candidate_passed'] and not event['candidate_passed']]
    save(output/'completion.json', dict(at=now(), study_completion_sha256=sha256(folder/'completion.json'),
        decoded_audit_sha256=sha256(output/'decoded.json'), implementation_sha256=sha256(__file__),
        untouched_frames=len(untouched), untouched_decoded_max_matrix_error=unaffected_error,
        protected_parameters_unchanged=True, accepted_parameter_reconstruction=True,
        new_release_failures_relative_to_source=new_failures, failed_full_checks=proof['failed_full_checks'],
        envelope_checks=proof['envelope_checks'], engine_actor_frames=proof['engine_actor_frames'], quality_approved=False))
    print(read(output/'completion.json'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('folder', type=Path); p.add_argument('output', type=Path); a = p.parse_args(); run(a.folder.resolve(), a.output.resolve())
