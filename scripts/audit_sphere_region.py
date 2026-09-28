"""Independently replay declared region placement and bounded skeleton projection."""
import argparse
import itertools
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_contact_binding import apply_region_binding
from audit_grasp_restoration import compare_record


def triangle_audit(points, ids, target, gaps, limits):
    """Scalar triple enumeration, independent of the generator's vectorized screen."""
    near = [i for i in range(len(ids)) if limits['clearance_m']-1e-6 <= gaps[i] <= limits['contact_gap_m']
            and np.linalg.norm(points[i]-target) <= limits['local_radius_m']]
    rows = []
    for indices in itertools.combinations(near, 3):
        a, b, c = points[list(indices)]
        spacing = min(np.linalg.norm(a-b), np.linalg.norm(b-c), np.linalg.norm(c-a))
        area = np.linalg.norm(np.cross(b-a, c-a))/2
        centroid = np.linalg.norm((a+b+c)/3-target)
        rows.append(dict(vertices=ids[list(indices)].tolist(), minimum_spacing_m=float(spacing), area_m2=float(area),
                         centroid_error_m=float(centroid), contact_gaps_m=gaps[list(indices)].tolist()))
    passing = [r for r in rows if r['minimum_spacing_m'] >= limits['spacing_m'] and r['area_m2'] >= limits['area_m2']
               and r['centroid_error_m'] <= limits['centroid_error_m']]
    chosen = min(passing, key=lambda r: (r['centroid_error_m'], -r['area_m2'], tuple(r['vertices']))) if passing else None
    diagnostic = dict(near_vertices=ids[near].tolist(), triple_count=len(rows),
                      maximum_area_m2=max([r['area_m2'] for r in rows], default=0.),
                      maximum_minimum_spacing_m=max([r['minimum_spacing_m'] for r in rows], default=0.))
    return chosen, diagnostic


def fixture(report, seed_report):
    protocol = read(report/'protocol.json'); result = read(report/'result.json')
    sr, sp = read(seed_report/'result.json'), read(seed_report/'protocol.json')
    for path, digest in [(seed_report/'result.json', protocol['seed_result_sha256']), (seed_report/'protocol.json', protocol['seed_protocol_sha256']),
                         (seed_report/'pose.npz', sr['pose_sha256']), (ASSET, protocol['mesh_sha256']),
                         (report/'probe_sphere_region_support.py', protocol['implementation_sha256'])]:
        if sha256(path) != digest: raise ValueError(f'Artifact changed: {path.name}')
    for name, digest in protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Source input changed')
    fit = ROOT/protocol['study']/'fit'; summary = read(fit/'summary.json')
    if sha256(fit/'summary.json') != sp['fit_summary_sha256']: raise ValueError('Fixture changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    seed = np.array(sr['parameters']); audit, motion = p.independent(seed)
    if not audit['rotation_norm_bounds_passed']: raise ValueError('Seed bounds failed')
    saved = dict(np.load(seed_report/'pose.npz', allow_pickle=False))
    for name, array in motion.items(): np.testing.assert_array_equal(array, saved[name])
    vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
    return p, seed, motion, vertices, protocol, result


def audit_region(report, seed_report):
    p, seed, motion, vertices, protocol, result = fixture(report, seed_report)
    patch = protocol['patch']; hand = patch['hand']; wrist = p.names.index(hand)
    # Binding validates the exact face/vertex membership and skin influences.
    apply_region_binding(p, hand, patch['vertices'][0], patch)
    descendants = {wrist}
    for joint in range(len(p.parents)):
        if p.parents[joint] in descendants: descendants.add(joint)
    ids = np.array([i for i in range(len(vertices)) if all(j in descendants for j, w in zip(p.skin['lbs_indices'][i], p.skin['lbs_weights'][i]) if w > 0)])
    region_ids = np.array(patch['vertices']); faces = p.skin['faces'][patch['face_ids']]
    tri = vertices[faces]; normal = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0); normal /= np.linalg.norm(normal)
    target_n = next(n.numpy() for name, f, n in p.normals if name == ('left-grip' if hand == 'LeftHand' else 'right-grip'))
    target = np.array(next(c['target'] for c in p.contacts if c['region'] == hand)); limits = protocol['limits']
    base = Rotation.align_vectors(target_n[None], normal[None])[0].as_matrix()
    basis = np.cross(target_n, np.eye(3)[np.argmin(abs(target_n))]); basis /= np.linalg.norm(basis); second = np.cross(target_n, basis)
    sphere, _, center, _ = p.objects[0]
    if sphere.shape != 'sphere': raise ValueError('Sphere required')
    expected_q = target-limits['placement_gap_m']*target_n
    np.testing.assert_allclose(result['desired_anchor_point'], expected_q, atol=1e-12, rtol=0.)
    legacy = 'orientations' not in protocol
    orientations = protocol.get('orientations', [dict(tilt_degrees=0., azimuth_degrees=0., rotation_from_source=result['rotation_from_source'])])
    expected_count = len(orientations)*len(region_ids)
    if len(result['rows']) != expected_count: raise ValueError('Missing or duplicate placement rows')
    clear = []; passing = []; index = 0
    for orientation in orientations:
        tilt, azimuth = orientation['tilt_degrees'], orientation['azimuth_degrees']
        if not 0 <= tilt < p.config['normal_tolerance_degrees']: raise ValueError('Normal limit exceeded')
        axis = np.cos(np.deg2rad(azimuth))*basis+np.sin(np.deg2rad(azimuth))*second
        rotation = Rotation.from_rotvec(np.deg2rad(tilt)*axis).as_matrix()@base
        np.testing.assert_allclose(rotation, orientation['rotation_from_source'], atol=1e-12, rtol=0.)
        for anchor in region_ids:
            saved = result['rows'][index]; index += 1
            placed = (vertices-vertices[anchor])@rotation.T+expected_q
            gaps = np.linalg.norm(placed-center.numpy()[0], axis=1)-sphere.dimensions[0]
            minimum = float(gaps[ids].min()); full = minimum >= limits['clearance_m']-1e-6
            triangle, diagnostic = triangle_audit(placed[region_ids], region_ids, target, gaps[region_ids], limits) if full else (None, None)
            row = dict(anchor=int(anchor), tilt_degrees=tilt, azimuth_degrees=azimuth, rotation_from_source=rotation.tolist(), minimum_hand_clearance_m=minimum,
                       full_hand_clearance_passed=bool(full), contact_triangle=triangle, region_condition_passed=bool(full and triangle is not None))
            comparable = {k: v for k, v in row.items() if k not in ['tilt_degrees', 'azimuth_degrees', 'rotation_from_source']} if legacy else row
            compare_record(comparable, saved)
            if full: clear.append(dict(anchor=int(anchor), tilt_degrees=tilt, azimuth_degrees=azimuth, minimum_hand_clearance_m=minimum, contact_triangle=triangle, diagnostic=diagnostic))
            if row['region_condition_passed']: passing.append(row)
    best = min(passing, key=lambda r: (r['contact_triangle']['centroid_error_m'], -r['contact_triangle']['area_m2'], r['anchor'], r['tilt_degrees'], r['azimuth_degrees'])) if passing else None
    compare_record(best, result['best'])
    if len(clear) != result['hand_clearance_pass_count'] or len(passing) != result['region_pass_count']: raise ValueError('Summary counts changed')
    return dict(report=report.relative_to(ROOT).as_posix(), hand=hand, placements=expected_count, clearance_passes=len(clear), region_passes=len(passing), clear_candidates=clear,
                protocol_sha256=sha256(report/'protocol.json'), result_sha256=sha256(report/'result.json'), source_snapshot_verified=True)


def audit_projection(report):
    protocol, result = read(report/'protocol.json'), read(report/'result.json')
    for name, digest in protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Projection input changed')
    for name, digest in protocol['implementation'].items():
        if sha256(report/'implementation'/name) != digest: raise ValueError('Projection snapshot changed')
    for path, digest in [(report/'protocol.json', result['protocol_sha256']), (report/'pose.npz', result['pose_sha256'])]:
        if sha256(path) != digest: raise ValueError('Projection artifact changed')
    region_report = ROOT/protocol['region_report']; seed_report = ROOT/protocol['seed_report']
    for name in ['protocol', 'result']:
        if sha256(region_report/f'{name}.json') != protocol[f'region_{name}_sha256']: raise ValueError('Region input changed')
    p, seed, source, source_v, rp, rr = fixture(region_report, seed_report)
    hand = rp['patch']['hand']; best = rr['best']; patch_ids = np.array(rp['patch']['vertices'])
    binding = apply_region_binding(p, hand, best['anchor'], rp['patch']); compare_record(binding, protocol['contact_binding'])
    prefix = hand.removesuffix('Hand'); expected_joints = [prefix+n for n in ['Shoulder', 'Arm', 'ForeArm', 'Hand']]
    if protocol['edited_joints'] != expected_joints: raise ValueError('Unexpected editable chain')
    slots = np.array([p.lookup[p.names.index(n)] for n in expected_joints]); limits = p.limits[slots]
    cols = np.array([3*i+k for i in slots for k in range(3)]); frozen = np.setdiff1d(np.arange(p.dim), cols)
    raw = np.array(result['raw_parameters']).reshape(-1, 3); physical = np.array(result['parameters'])
    theta = raw/np.sqrt(1+np.sum(raw**2, axis=1)/limits**2)[:, None]
    np.testing.assert_allclose(physical[cols], theta.ravel(), atol=1e-12, rtol=0.); np.testing.assert_array_equal(physical[frozen], seed[frozen])
    audit, motion = p.independent(physical); compare_record(audit, result['candidate'])
    saved = dict(np.load(report/'pose.npz', allow_pickle=False))
    for name, array in motion.items(): np.testing.assert_array_equal(array, saved[name])
    vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0]); faces = p.skin['faces'][rp['patch']['face_ids']]
    knuckles = [p.names.index(hand+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]; wrist = p.names.index(hand)
    def directions(v, joints):
        triangles = v[faces]; n = sum((np.cross(b-a, c-a) for a, b, c in triangles), np.zeros(3)); n /= np.linalg.norm(n)
        d = np.mean(joints[knuckles], axis=0)-joints[wrist]; t = d-n*np.dot(n, d); t /= np.linalg.norm(t)
        return n, t
    def angle(a, b): return float(np.rad2deg(np.arccos(np.clip(np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b)), -1., 1.))))
    source_n, source_t = directions(source_v, source['posed_joints'][0]); rotation = np.array(best['rotation_from_source'])
    desired_n, desired_t = rotation@source_n, rotation@source_t
    np.testing.assert_allclose(desired_n, protocol['target_normal'], atol=1e-12); np.testing.assert_allclose(desired_t, protocol['target_tangent'], atol=1e-12)
    np.testing.assert_allclose(protocol['target_point'], rr['desired_anchor_point'], atol=1e-12)
    normal, tangent = directions(vertices, motion['posed_joints'][0])
    reach = dict(point_error_m=float(np.linalg.norm(vertices[best['anchor']]-rr['desired_anchor_point'])), normal_error_degrees=angle(normal, desired_n), tangent_error_degrees=angle(tangent, desired_t))
    for key in reach: np.testing.assert_allclose(reach[key], result['reach'][key], atol=2e-6 if key.endswith('degrees') else 1e-10, rtol=0.)
    settings = protocol['settings']; reached = reach['point_error_m'] <= settings['reach_point_m'] and max(reach['normal_error_degrees'], reach['tangent_error_degrees']) <= settings['reach_direction_degrees']
    target = np.array(next(c['target'] for c in p.contacts if c['region'] == hand)); sphere, _, center, _ = p.objects[0]
    gaps = np.linalg.norm(vertices-center.numpy()[0], axis=1)-sphere.dimensions[0]
    triangle, diagnostic = triangle_audit(vertices[patch_ids], patch_ids, target, gaps[patch_ids], rp['limits']); compare_record(triangle, result['contact_triangle'])
    passed = bool(reached and triangle is not None and audit['pose_witness_passed'])
    if reached != result['target_reached'] or passed != result['region_pose_passed']: raise ValueError('Pose acceptance changed')
    worst = int(np.argmin(gaps)); influences = [dict(joint=p.names[j], weight=float(w)) for j, w in zip(p.skin['lbs_indices'][worst], p.skin['lbs_weights'][worst]) if w > 0]
    return dict(report=report.relative_to(ROOT).as_posix(), target_reached=bool(reached), region_pose_passed=passed, candidate=audit, contact_triangle=triangle,
                worst_sphere_vertex=worst, worst_vertex_influences=influences, frozen_parameters_exact=True, saved_pose_exact=True,
                original_edit_bounds_verified=True, protocol_sha256=sha256(report/'protocol.json'), result_sha256=sha256(report/'result.json'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--regions', type=Path, nargs='+', required=True); parser.add_argument('--projection', type=Path)
    args = parser.parse_args(); rows = [audit_region(p.resolve(), args.seed_report.resolve()) for p in args.regions]
    projection = audit_projection(args.projection.resolve()) if args.projection else None
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output/'verification.json', dict(at=now(), regions=rows, projection=projection, auditor_sha256=sha256(Path(__file__)), quality_approved=False))
    print(dict(regions=[{k:r[k] for k in ['hand', 'placements', 'clearance_passes', 'region_passes']} for r in rows], projection=None if projection is None else dict(target_reached=projection['target_reached'], region_pose_passed=projection['region_pose_passed'], worst_vertex=projection['worst_sphere_vertex'])))
