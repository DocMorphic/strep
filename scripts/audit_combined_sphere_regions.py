"""Verify saved two-region pose against its disjoint source projections and geometry."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from audit_sphere_region import audit_projection, fixture, triangle_audit
from audit_grasp_restoration import compare_record
from grasp_contact_binding import apply_region_binding


def run(report, output):
    report, output = Path(report).resolve(), Path(output).resolve()
    protocol, result = read(report/'protocol.json'), read(report/'result.json')
    for name, digest in protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Input changed')
    for name, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Combination implementation changed')
    if sha256(report/'protocol.json') != result['protocol_sha256'] or sha256(report/'pose.npz') != result['pose_sha256']: raise ValueError('Saved combined artifact changed')
    reports = [ROOT/n for n in protocol['projections']]
    if len(reports) != 2: raise ValueError('Two projections required')
    projections = [audit_projection(r) for r in reports]
    pr = [read(r/'protocol.json') for r in reports]; rr = [read(r/'result.json') for r in reports]
    if pr[0]['seed_report'] != pr[1]['seed_report']: raise ValueError('Shared seed required')
    region_reports = [ROOT/v['region_report'] for v in pr]; seed_report = ROOT/pr[0]['seed_report']
    p, seed, source, source_vertices, base_protocol, _ = fixture(region_reports[0], seed_report)
    expected = seed.copy(); changed = set(); regions = []
    for hand, projection, projection_result, region_report, verified in zip(['LeftHand', 'RightHand'], pr, rr, region_reports, projections):
        other, other_seed, _, _, rp, region_result = fixture(region_report, seed_report)
        if rp['study'] != base_protocol['study'] or rp['frame'] != base_protocol['frame'] or rp['patch']['hand'] != hand or not verified['target_reached']: raise ValueError('Mismatched source')
        np.testing.assert_array_equal(seed, other_seed)
        chain = [hand.removesuffix('Hand')+name for name in ['Shoulder', 'Arm', 'ForeArm', 'Hand']]
        cols = [3*p.lookup[p.names.index(joint)]+k for joint in chain for k in range(3)]
        if changed.intersection(cols): raise ValueError('Overlapping projection columns')
        changed.update(cols); delta = np.array(projection_result['parameters'])-seed
        np.testing.assert_array_equal(delta[np.setdiff1d(np.arange(p.dim), cols)], 0.)
        expected += delta; regions.append((rp, region_result))
    compare_record(sorted(changed), protocol['edited_columns'])
    physical = np.array(result['parameters']); np.testing.assert_allclose(physical, expected, atol=1e-15, rtol=0.)
    np.testing.assert_array_equal(physical[np.setdiff1d(np.arange(p.dim), list(changed))], seed[np.setdiff1d(np.arange(p.dim), list(changed))])
    original, original_motion = p.independent(physical); compare_record(original, result['original_condition'])
    for i, (rp, region_result) in enumerate(regions):
        binding = apply_region_binding(p, rp['patch']['hand'], region_result['best']['anchor'], rp['patch']); compare_record(binding, protocol['contact_bindings'][i])
    audit, motion = p.independent(physical); compare_record(audit, result['candidate'])
    saved = dict(np.load(report/'pose.npz', allow_pickle=False))
    for name, array in motion.items(): np.testing.assert_array_equal(array, saved[name])
    vertices = p.surface.vertices(saved['global_rot_mats'][0], saved['posed_joints'][0]); sphere, _, center, _ = p.objects[0]
    if sphere.shape != 'sphere': raise ValueError('Sphere required')
    gaps = np.linalg.norm(vertices-center.numpy()[0], axis=1)-sphere.dimensions[0]; contacts = []
    for rp, region_result in regions:
        ids = np.array(rp['patch']['vertices']); hand = rp['patch']['hand']; target = np.array(next(c['target'] for c in p.contacts if c['region'] == hand))
        triangle, diagnostic = triangle_audit(vertices[ids], ids, target, gaps[ids], rp['limits'])
        contacts.append(dict(hand=hand, contact_triangle=triangle, diagnostic=diagnostic))
    compare_record(contacts, result['contacts'])
    passed = bool(audit['pose_witness_passed'] and all(c['contact_triangle'] is not None for c in contacts))
    if passed != result['region_pose_passed']: raise ValueError('Combined acceptance changed')
    output.mkdir(parents=True, exist_ok=False)
    save(output/'verification.json', dict(at=now(), report=report.relative_to(ROOT).as_posix(), region_pose_passed=passed,
         original_condition_passed=original['pose_witness_passed'], candidate=audit, contacts=contacts, full_skin_vertices=len(vertices),
         disjoint_original_arm_edits_verified=True, frozen_parameters_exact=True, saved_pose_exact=True,
         result_sha256=sha256(report/'result.json'), protocol_sha256=sha256(report/'protocol.json'), auditor_sha256=sha256(Path(__file__)), quality_approved=False))
    print(dict(region_pose_passed=passed, original_condition_passed=original['pose_witness_passed'], full_skin_vertices=len(vertices), minimum_sphere_clearance_m=float(gaps.min())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.report, args.output)
