"""Replay every recorded restoration decision and verify the saved full-skin pose."""
import argparse
from pathlib import Path

import numpy as np
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem


def compare_record(actual, recorded):
    if isinstance(actual, dict):
        if actual.keys() != recorded.keys():
            raise ValueError('Audit fields changed')
        for key in actual:
            compare_record(actual[key], recorded[key])
    elif isinstance(actual, list):
        if len(actual) != len(recorded):
            raise ValueError('Audit row count changed')
        for a, b in zip(actual, recorded):
            compare_record(a, b)
    elif isinstance(actual, float):
        np.testing.assert_allclose(actual, recorded, atol=1e-9, rtol=1e-8)
    elif actual != recorded:
        raise ValueError('Audit value changed')


def coordinates(parameters, limits):
    theta = np.asarray(parameters[:-1]).reshape(-1, 3)
    fraction = np.sum(theta * theta, axis=1) / limits**2
    if np.any(fraction >= 1):
        raise ValueError('Recorded rotation outside open bounded map')
    return np.r_[(theta / np.sqrt(1 - fraction)[:, None]).ravel(), parameters[-1]]


def mapped(parameters, limits):
    # NumPy implementation, independent of the optimizer's Torch bound map.
    raw = parameters[:-1].reshape(-1, 3)
    theta = raw / np.sqrt(1 + np.sum(raw * raw, axis=1) / limits**2)[:, None]
    return np.r_[theta.ravel(), parameters[-1]]


def protected(audit, config):
    return bool(audit['rotation_norm_bounds_passed']
                and audit['minimum_floor_height_m'] >= config['clearance_m'] - 1e-6
                and all(c['error_m'] <= config['point_tolerance_m'] + 1e-6 for c in audit['contacts'])
                and all(n['error_degrees'] <= config['normal_tolerance_degrees'] + 1e-4 for n in audit['normals']))


def violation(audit, config):
    return max([0.] + [config['object_clearance_m'] - o['minimum_clearance_m'] for o in audit['objects']])


def run(report, seed_report, output):
    report, seed_report, output = map(lambda x: Path(x).resolve(), (report, seed_report, output))
    protocol, result = read(report/'protocol.json'), read(report/'result.json')
    mode = protocol.get('coordinate_mode', 'bounded')
    if mode not in ('bounded', 'physical'):
        raise ValueError('Unknown coordinate mode')
    for path, digest in [(report/'protocol.json', result['protocol_sha256']),
                         (report/'pose.npz', result['pose_sha256']),
                         (seed_report/'result.json', protocol['seed_result_sha256']),
                         (seed_report/'protocol.json', protocol['seed_protocol_sha256'])]:
        if sha256(path) != digest:
            raise ValueError(f'Artifact changed: {path.name}')
    for name, digest in protocol['inputs'].items():
        if sha256(ROOT/name) != digest:
            raise ValueError(f'Input changed: {name}')
    for name, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(report/'implementation'/name) != digest:
            raise ValueError(f'Implementation changed: {name}')
    fit = ROOT/protocol['study']/'fit'
    if sha256(fit/'summary.json') != protocol['fit_summary_sha256']:
        raise ValueError('Fit summary changed')
    summary = read(fit/'summary.json')
    if sha256(ASSET) != summary['mesh_sha256']:
        raise ValueError('Mesh changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    parameters = np.array(read(seed_report/'result.json')['parameters'])
    current, _ = p.independent(parameters)
    compare_record(current, result['seed'])
    decisions = 0
    accepted_stages = 0
    for stage_index, stage in enumerate(result['history']):
        if stage['stage'] != stage_index:
            raise ValueError('Stage order changed')
        compare_record(current, stage['before'])
        anchor = coordinates(parameters, p.limits) if mode == 'bounded' else parameters.copy()
        accepted = False
        for attempt_index, attempt in enumerate(stage['attempts']):
            if attempt['trust_degrees'] != protocol['limits']['trust_degrees'][attempt_index]:
                raise ValueError('Trust schedule changed')
            proposal = coordinates(attempt['proposal_parameters'], p.limits) if mode == 'bounded' else np.array(attempt['proposal_parameters'])
            radius = np.r_[np.full(p.dim-1, np.deg2rad(attempt['trust_degrees'])), protocol['limits']['root_trust_m']]
            if np.any(np.abs(proposal-anchor) > radius+1e-9):
                raise ValueError('Proposal exceeds declared trust region')
            for backtrack_index, item in enumerate(attempt['backtracks']):
                if item['fraction'] != .5**backtrack_index:
                    raise ValueError('Backtrack schedule changed')
                interpolated = anchor + item['fraction'] * (proposal-anchor)
                candidate = mapped(interpolated, p.limits) if mode == 'bounded' else interpolated
                audit, _ = p.independent(candidate)
                compare_record(audit, item['audit'])
                improvement = violation(current, p.config) - violation(audit, p.config)
                permitted = protected(audit, p.config)
                decision = bool(permitted and improvement >= protocol['limits']['minimum_improvement_m'])
                compare_record(permitted, item['protected_pass'])
                compare_record(improvement, item['clearance_improvement_m'])
                compare_record(decision, item['accepted'])
                decisions += 1
                if decision:
                    if backtrack_index != len(attempt['backtracks'])-1 or attempt_index != len(stage['attempts'])-1:
                        raise ValueError('Unreplayed decisions after acceptance')
                    parameters, current, accepted = candidate, audit, True
                    accepted_stages += 1
                    break
            if accepted:
                break
        compare_record(accepted, stage['accepted'])
        if accepted:
            compare_record(current, stage['after'])
    np.testing.assert_allclose(parameters, result['parameters'], atol=1e-10, rtol=1e-8)
    final, motion = p.independent(np.array(result['parameters']))
    compare_record(final, result['candidate'])
    with np.load(report/'pose.npz', allow_pickle=False) as saved:
        if set(saved.files) != set(motion):
            raise ValueError('Saved pose arrays changed')
        for key, value in motion.items():
            np.testing.assert_array_equal(saved[key], value)
    output.mkdir(parents=True, exist_ok=False)
    save(output/'verification.json', dict(at=now(), report=report.relative_to(ROOT).as_posix(),
         result_sha256=sha256(report/'result.json'), protocol_sha256=sha256(report/'protocol.json'),
         auditor_sha256=sha256(Path(__file__)), coordinate_mode=mode, replayed_decisions=decisions, accepted_stages=accepted_stages,
         saved_pose_arrays_exact=True, candidate=final, quality_approved=False,
         scope='NumPy replay in the declared coordinate space; SciPy/NumPy full-skin geometry shared with pose audit. Verifies decisions and exported single pose, not motion quality.'))
    print(dict(replayed_decisions=decisions, accepted_stages=accepted_stages, pose_witness_passed=final['pose_witness_passed']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('seed_report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.report, args.seed_report, args.output)
