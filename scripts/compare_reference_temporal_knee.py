"""Compare the two frozen temporal objectives using independently decoded audits."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rig_asset import RigAsset
from rig_transition import localize
from strep import ROOT, now, read, save, sha256


def verified_audit(folder):
    record = read(folder/'verification.json')
    for p, digest in record['inputs'].items():
        if sha256(p) != digest:
            raise ValueError('Audit input changed: '+p)
    for p, digest in record['details'].items():
        if sha256(folder/p) != digest:
            raise ValueError('Audit detail changed: '+p)
    return record


def peaks(folder):
    data = read(folder/'patch-tracks.json')
    result = {}
    for name, tracks in data['tracks'].items():
        result[name] = {}
        for stage in ('before', 'after'):
            speed = np.linalg.norm(np.diff(tracks[stage], axis=0), axis=1)*data['fps']
            idx = int(np.argmax(speed))
            result[name][stage] = dict(peak_m_s=float(speed[idx]),
                arrival_frame=data['start_frame']+(idx+1)*30/data['fps'])
    return result


def run(output):
    if output.exists():
        raise ValueError('Preserve earlier comparisons')
    studies = [ROOT/'reports'/n for n in ('knee-contact-temporal-v1', 'knee-contact-reference-v1')]
    audits = [ROOT/'reports'/n for n in ('knee-contact-temporal-audit-v1', 'knee-contact-reference-audit-v1')]
    records = [verified_audit(a) for a in audits]
    protocols = [read(s/'protocol.json') for s in studies]
    matched = ['case', 'input_result_sha256', 'input_pose_sha256', 'spec_sha256', 'frames',
               'max_sweeps', 'max_iterations_per_frame', 'budget_domain', 'contact_contract']
    for key in matched:
        if protocols[0][key] != protocols[1][key]:
            raise ValueError('Mismatched protocol: '+key)
    common = protocols[0]['implementation'].keys() & protocols[1]['implementation'].keys()
    for key in common:
        if protocols[0]['implementation'][key] != protocols[1]['implementation'][key]:
            raise ValueError('Common implementation differs: '+key)
    fits = []
    for study in studies:
        with np.load(study/'fit.npz', allow_pickle=False) as z:
            fits.append(dict(z))
    for key in ('initial', 'body', 'limb', 'weights'):
        np.testing.assert_array_equal(fits[0][key], fits[1][key])
    if sha256(studies[1]/'reference.npz') != protocols[1]['reference_sha256']:
        raise ValueError('Explicit reference changed')
    with np.load(studies[1]/'reference.npz', allow_pickle=False) as z:
        reference = z['parameters']
    np.testing.assert_array_equal(reference, fits[1]['reference'])
    spec = read(studies[1]/'spec.json')
    rig = RigAsset.load(studies[1]/'candidate.glb')
    limb, body = [localize(fits[1][k], rig.parents) for k in ('limb', 'body')]
    # Independently reconstruct the parameter reference from saved transforms.
    root = spec['root_node']
    reconstructed = np.zeros_like(reference)
    reconstructed[:, :3] = fits[1]['body'][:, root, :3, 3]-fits[1]['limb'][:, root, :3, 3]
    nodes = [item['node'] for item in spec['edit_joints'].values()]
    for i, node in enumerate(nodes):
        delta = limb[:, node, :3, :3].transpose(0, 2, 1) @ body[:, node, :3, :3]
        reconstructed[:, 3+3*i:6+3*i] = Rotation.from_matrix(delta).as_rotvec()
    np.testing.assert_allclose(reference, reconstructed, atol=1e-12, rtol=0)
    speed = [peaks(a) for a in audits]
    for name in speed[0]:
        if speed[0][name]['before'] != speed[1][name]['before']:
            raise ValueError('Motion reference tracks differ')
    fields = ['floor_worst', 'dense_floor_passed', 'center_contact_errors_m', 'center_contact_passed',
              'window_step_bounds_passed', 'global_step_bounds_passed', 'candidate_pose_bounds_passed',
              'outside_matrix_max_error', 'sample_count', 'engine_actor_frames', 'patch_speeds']
    result = dict(at=now(),case=protocols[0]['case'],matched_protocol_fields=matched,
        common_implementation=sorted(common), matched_arrays=['initial','body','limb','weights'],
        reference_parameter_max_error=float(abs(reference-reconstructed).max()),
        inputs={str(p):sha256(p) for p in [*(a/'verification.json' for a in audits), studies[1]/'reference.npz']},
        variants={label:dict(**{k:r[k] for k in fields}, peaks=speed[i],
            ordered_posture_proxy=r['after_posture']['upright_kneel_upright_proxy_present'])
            for i,(label,r) in enumerate(zip(('limb_zero_prior','body_reference_prior'),records))},
        quality_approved=False,human_review=None,
        scope='One development clip, one center-frame contact target, fixed four-sweep budget. No sustained-support, convergence, naturalness or generalization claim.')
    save(output/'comparison.json',result)
    print(result['variants'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    run(parser.parse_args().output.resolve())
