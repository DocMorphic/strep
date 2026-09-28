"""Replay physical LP proposals, nonlinear acceptance and saved pose arrays."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem, norm_slack_and_jacobian
from grasp_physical_step import norm_remainder
from audit_grasp_restoration import compare_record, protected, violation


def run(report, seed_report, output):
    report, seed_report, output = [Path(s).resolve() for s in (report, seed_report, output)]
    protocol, result = read(report/'protocol.json'), read(report/'result.json')
    for path, digest in [(report/'protocol.json', result['protocol_sha256']), (report/'pose.npz', result['pose_sha256']),
                         (seed_report/'result.json', protocol['seed_result_sha256']), (seed_report/'protocol.json', protocol['seed_protocol_sha256'])]:
        if sha256(path) != digest: raise ValueError('Artifact changed')
    for n, digest in protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Input changed')
    for n, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/n) != digest or sha256(report/'implementation'/n) != digest: raise ValueError('Implementation changed')
    fit = ROOT/protocol['study']/'fit'; summary = read(fit/'summary.json')
    if sha256(fit/'summary.json') != protocol['fit_summary_sha256'] or sha256(ASSET) != summary['mesh_sha256']:
        raise ValueError('Fit or mesh changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    x = np.array(read(seed_report/'result.json')['parameters']); current, _ = p.independent(x)
    compare_record(current, result['seed']); decisions = 0; accepted_stages = 0
    for index, stage in enumerate(result['history']):
        compare_record(index, stage['stage']); compare_record(current, stage['before'])
        linear_file = report/f'linearization-{index:02d}.npz'
        if sha256(linear_file) != stage['linearization_sha256']: raise ValueError('Linearization changed')
        with np.load(linear_file, allow_pickle=False) as saved: linear = dict(saved)
        np.testing.assert_allclose(linear['parameters'], x, atol=1e-13)
        norm, nj = norm_slack_and_jacobian(x, p.limits)
        np.testing.assert_allclose(linear['protected'][-len(norm):], norm, atol=1e-12)
        np.testing.assert_allclose(linear['protected_jac'][-len(norm):], nj, atol=1e-12)
        accepted = False
        for ai, attempt in enumerate(stage['attempts']):
            trust = protocol['limits']['trusts_degrees'][ai]
            compare_record(trust, attempt['trust_degrees'])
            if 'delta' not in attempt:
                if attempt['lp']['success'] or attempt['backtracks']: raise ValueError('Missing LP proposal')
                continue
            delta = np.array(attempt['delta'])
            radius = np.r_[np.full(p.dim-1, np.deg2rad(trust)), protocol['limits']['root_trust_at_largest_m']*trust/protocol['limits']['trusts_degrees'][0]]
            if np.any(np.abs(delta) > radius+1e-9) or not 0 <= (x+delta)[-1] <= p.config['max_root_lift_m']:
                raise ValueError('Proposal outside trust/root bounds')
            margin = np.r_[np.full(len(linear['protected'])-len(norm), protocol['limits']['protected_margin_normalized']), norm_remainder(radius, p.limits)]
            if (linear['protected']+linear['protected_jac']@delta-margin).min() < -2e-8:
                raise ValueError('LP violates protected linear model')
            t = attempt['lp']['predicted_worst_violation_normalized']
            if (linear['surface']+linear['surface_jac']@delta+t).min() < -2e-8:
                raise ValueError('LP epigraph mismatch')
            if norm_slack_and_jacobian(x+delta, p.limits)[0].min() < -2e-8:
                raise ValueError('Norm remainder failed')
            for bi, item in enumerate(attempt['backtracks']):
                compare_record(item['fraction'], .5**bi)
                candidate = x+item['fraction']*delta; audit, _ = p.independent(candidate)
                compare_record(audit, item['audit'])
                improved = violation(current, p.config)-violation(audit, p.config)
                permitted = protected(audit, p.config)
                decision = bool(permitted and improved >= protocol['limits']['minimum_improvement_m'])
                compare_record(improved, item['improvement_m']); compare_record(permitted, item['protected_pass']); compare_record(decision, item['accepted'])
                decisions += 1
                if decision:
                    if bi != len(attempt['backtracks'])-1 or ai != len(stage['attempts'])-1: raise ValueError('Unreplayed decisions')
                    x, current, accepted = candidate, audit, True; accepted_stages += 1; break
            if accepted: break
        compare_record(accepted, stage['accepted'])
        if accepted: compare_record(current, stage['after'])
    np.testing.assert_allclose(x, result['parameters'], atol=1e-13)
    final, motion = p.independent(x); compare_record(final, result['candidate'])
    with np.load(report/'pose.npz', allow_pickle=False) as saved:
        if set(saved.files) != set(motion): raise ValueError('Pose arrays changed')
        for key, value in motion.items(): np.testing.assert_array_equal(saved[key], value)
    output.mkdir(parents=True, exist_ok=False)
    save(output/'verification.json', dict(at=now(), result_sha256=sha256(report/'result.json'), auditor_sha256=sha256(Path(__file__)),
         replayed_decisions=decisions, accepted_stages=accepted_stages, saved_pose_arrays_exact=True, candidate=final, quality_approved=False,
         scope='Validates stored LP rows, trust/norm bounds and all nonlinear full-skin decisions; not an optimality or motion quality certificate.'))
    print(dict(replayed_decisions=decisions, accepted_stages=accepted_stages, pose_witness_passed=final['pose_witness_passed']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.report, args.seed_report, args.output)
