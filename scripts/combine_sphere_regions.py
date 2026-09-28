"""Combine independently reached left/right region targets with disjoint arm edits."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from audit_sphere_region import audit_projection, fixture, triangle_audit
from grasp_contact_binding import apply_region_binding


def run(left_report, right_report, output):
    reports = [Path(left_report).resolve(), Path(right_report).resolve()]; output = Path(output).resolve()
    verified = [audit_projection(report) for report in reports]
    protocols = [read(report/'protocol.json') for report in reports]; results = [read(report/'result.json') for report in reports]
    if protocols[0]['seed_report'] != protocols[1]['seed_report']: raise ValueError('Same original seed required')
    seed_report = ROOT/protocols[0]['seed_report']; region_reports = [ROOT/pr['region_report'] for pr in protocols]
    p, seed, source, source_vertices, _, _ = fixture(region_reports[0], seed_report)
    physical = seed.copy(); edited = set(); bindings = []; regions = []
    for expected_hand, protocol, result, verification, region_report in zip(['LeftHand', 'RightHand'], protocols, results, verified, region_reports):
        rp = read(region_report/'protocol.json'); rr = read(region_report/'result.json')
        if rp['patch']['hand'] != expected_hand or not verification['target_reached'] or verification['contact_triangle'] is None:
            raise ValueError('Reached matching hand and distributed contact required')
        _, other_seed, _, _, other_protocol, _ = fixture(region_report, seed_report)
        np.testing.assert_array_equal(seed, other_seed)
        if other_protocol['study'] != read(region_reports[0]/'protocol.json')['study'] or other_protocol['frame'] != p.frame: raise ValueError('Same fixture/frame required')
        columns = [3*p.lookup[p.names.index(joint)]+k for joint in protocol['edited_joints'] for k in range(3)]
        if edited.intersection(columns): raise ValueError('Arm edits overlap')
        values = np.array(result['parameters']); frozen = np.setdiff1d(np.arange(p.dim), columns)
        np.testing.assert_array_equal(values[frozen], seed[frozen])
        physical[columns] = values[columns]; edited.update(columns)
        bindings.append(apply_region_binding(p, expected_hand, rr['best']['anchor'], rp['patch'])); regions.append(rp)
    frozen = np.array(sorted(set(range(p.dim))-edited)); np.testing.assert_array_equal(physical[frozen], seed[frozen])
    audit, motion = p.independent(physical); vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
    sphere, _, center, _ = p.objects[0]; gaps = np.linalg.norm(vertices-center.numpy()[0], axis=1)-sphere.dimensions[0]
    contacts = []
    for rp in regions:
        ids = np.array(rp['patch']['vertices']); target = np.array(next(c['target'] for c in p.contacts if c['region'] == rp['patch']['hand']))
        triangle, diagnostic = triangle_audit(vertices[ids], ids, target, gaps[ids], rp['limits'])
        contacts.append(dict(hand=rp['patch']['hand'], contact_triangle=triangle, diagnostic=diagnostic))
    passed = bool(audit['pose_witness_passed'] and all(c['contact_triangle'] is not None for c in contacts))
    # Also retain the original authored-condition result; the new condition never replaces it.
    original, _, _, _, _, _ = fixture(region_reports[0], seed_report); original_audit, _ = original.independent(physical)
    output.mkdir(parents=True, exist_ok=False); np.savez(output/'pose.npz', **motion)
    implementation = {n: sha256(ROOT/'scripts'/n) for n in ['combine_sphere_regions.py', 'audit_sphere_region.py', 'grasp_contact_binding.py', 'grasp_pose_witness.py', 'floor_contact.py']}
    save(output/'protocol.json', dict(at=now(), projections=[r.relative_to(ROOT).as_posix() for r in reports],
         inputs={str((r/f).relative_to(ROOT).as_posix()): sha256(r/f) for r in reports for f in ['protocol.json', 'result.json', 'pose.npz']},
         implementation=implementation, contact_bindings=bindings, edited_columns=sorted(edited),
         scope='One development pose, new two-region condition. Combine disjoint bounded arm rotations from the same original seed; all fingers, torso, legs and root frozen. No animation, self-collision, anatomical or held-out approval.', quality_approved=False))
    result = dict(at=now(), parameters=physical.tolist(), candidate=audit, contacts=contacts, original_condition=original_audit,
                  region_pose_passed=passed, frozen_parameters_exact=True, pose_sha256=sha256(output/'pose.npz'), protocol_sha256=sha256(output/'protocol.json'), quality_approved=False)
    save(output/'result.json', result)
    print(dict(region_pose_passed=passed, original_condition_passed=original_audit['pose_witness_passed'], candidate=audit, contacts=contacts))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('left_report', type=Path); parser.add_argument('right_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.left_report, args.right_report, args.output)
