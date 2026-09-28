"""Independently reconstruct bounded shapes and both rigid placement studies."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_orientation import hand_frame, align_direction, unit, angular_error
from rigid_grasp_bound import clearance_upper_bound
from audit_grasp_restoration import compare_record
from grasp_contact_binding import apply_contact_binding


def run(shapes, placements, joint, seed_report, output):
    shapes, placements, joint, seed_report, output = [Path(s).resolve() for s in (shapes, placements, joint, seed_report, output)]
    protocol = read(shapes/'protocol.json'); fit = ROOT/protocol['study']/'fit'; summary = read(fit/'summary.json')
    if sha256(fit/'summary.json') != protocol['fit_summary_sha256'] or sha256(seed_report/'result.json') != protocol['seed_result_sha256'] or sha256(ASSET) != summary['mesh_sha256']: raise ValueError('Study/seed changed')
    for name, digest in protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Input changed')
    for name, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(shapes/'implementation'/name) != digest: raise ValueError('Shape implementation changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    seed = np.array(read(seed_report/'result.json')['parameters']); contact = next(c for c in p.contacts if c['region'] == 'LeftHand'); _, faces, target_n = next(n for n in p.normals if n[0] == 'left-grip')
    sphere, _, center, _ = p.objects[0]; ids = np.array(protocol['patch_vertices']); slots = [i for i, j in enumerate(p.editable) if p.names[j] in protocol['variable_joints']]
    columns = np.array([3*i+k for i in slots for k in range(3)]); frozen = [i for i in range(p.dim) if i not in columns]; limits = p.limits[slots]
    wrist = p.names.index('LeftHand'); knuckles = [p.names.index('LeftHand'+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]
    t1 = unit(np.cross(target_n.numpy(), np.eye(3)[np.argmin(np.abs(target_n.numpy()))])); basis = np.c_[t1, np.cross(target_n.numpy(), t1)]
    def geometry(parameters, path, recorded_audit):
        x = np.array(parameters); np.testing.assert_array_equal(x[frozen], seed[frozen])
        audit, motion = p.independent(x); compare_record(audit, recorded_audit)
        if not audit['rotation_norm_bounds_passed']: raise ValueError('Original budgets failed')
        with np.load(path, allow_pickle=False) as saved:
            if set(saved.files) != set(motion): raise ValueError('Pose arrays changed')
            for key, value in motion.items(): np.testing.assert_array_equal(saved[key], value)
        vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
        point, normal, tangent = hand_frame(vertices, motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
        return vertices, point, normal, tangent
    shapes_summary = read(shapes/'summary.json'); shape_rows = []; shape_geometry = {}
    if len(shapes_summary['rows']) != len(protocol['settings']['starts']): raise ValueError('Missing shape trials')
    for row in shapes_summary['rows']:
        folder = ROOT/row['folder']; result = read(folder/'result.json')
        if sha256(folder/'result.json') != row['result_sha256'] or sha256(folder/'pose.npz') != result['pose_sha256'] or sha256(folder/'protocol.json') != result['protocol_sha256']: raise ValueError('Shape artifact changed')
        vertices, point, normal, tangent = geometry(result['parameters'], folder/'pose.npz', result['candidate'])
        upper = clearance_upper_bound(vertices[ids]-point, normal, contact['target'], target_n.numpy(), center.numpy()[0], sphere.dimensions[0], p.config['point_tolerance_m']+1e-6, p.config['normal_tolerance_degrees']+1e-4)+protocol['settings']['numeric_allowance_m']
        compare_record(float(upper.min()), result['minimum_rigid_upper_m']); compare_record(bool(upper.min() >= p.config['object_clearance_m']-1e-6), result['necessary_rigid_bound_passed'])
        shape_rows.append(dict(shape=row['folder'], minimum_rigid_upper_m=float(upper.min()), actual_pose_passed=result['candidate']['pose_witness_passed']))
        shape_geometry[row['folder']] = vertices, point, normal, tangent
    placement_protocol, placement_result = read(placements/'protocol.json'), read(placements/'result.json')
    if placement_protocol['shapes_summary_sha256'] != sha256(shapes/'summary.json') or placement_protocol['shapes_protocol_sha256'] != sha256(shapes/'protocol.json') or placement_protocol['implementation_sha256'] != sha256(ROOT/'scripts/study_grasp_placements.py'): raise ValueError('Placement binding changed')
    def check_placement(result, geo, settings, raw):
        vertices, point, normal, tangent = geo; raw = np.array(raw)
        delta = settings['point_limit_m']*raw[:3]/np.sqrt(1+raw[:3]@raw[:3]); tilt = settings['angle_limit_radians']*raw[3:]/np.sqrt(1+raw[3:]@raw[3:])
        matrix = Rotation.from_rotvec(basis@tilt).as_matrix()@align_direction(normal, target_n.numpy()); q = np.array(contact['target'])+delta
        np.testing.assert_allclose(q, result['desired_point'], atol=1e-12)
        np.testing.assert_allclose(matrix@normal, result['desired_normal'], atol=1e-12)
        np.testing.assert_allclose(matrix@tangent, result['desired_tangent'], atol=1e-12)
        if np.linalg.norm(delta) > settings['point_limit_m']+1e-12 or angular_error(matrix@normal, target_n.numpy()) > np.rad2deg(settings['angle_limit_radians'])+1e-8: raise ValueError('Original target limits failed')
        distance = np.linalg.norm((vertices[ids]-point)@matrix.T+q-center.numpy()[0], axis=1)-sphere.dimensions[0]
        compare_record(float(distance.min()), result['minimum_clearance_m']); compare_record(bool(distance.min() >= p.config['object_clearance_m']-1e-6), result['rigid_patch_clearance_passed'])
        return float(distance.min())
    placement_rows = []
    for row in placement_result['rows']:
        minimum = check_placement(row, shape_geometry[row['shape']], placement_protocol['settings'], row['raw'])
        placement_rows.append(dict(shape=row['shape'], start=row['start'], minimum_clearance_m=minimum))
    joint_protocol, joint_summary = read(joint/'protocol.json'), read(joint/'summary.json')
    if joint_protocol['shapes_protocol_sha256'] != sha256(shapes/'protocol.json') or joint_protocol['placements_result_sha256'] != sha256(placements/'result.json') or joint_protocol['seed_result_sha256'] != sha256(seed_report/'result.json') or joint_protocol['implementation_sha256'] != sha256(ROOT/'scripts/study_joint_grasp_patch.py') or joint_protocol['placement_source_sha256'] != sha256(ROOT/'scripts/study_grasp_placements.py'): raise ValueError('Joint binding changed')
    for name, digest in joint_protocol.get('implementation', {}).items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(joint/'implementation'/name) != digest: raise ValueError('Joint implementation changed')
    binding = joint_protocol.get('contact_binding')
    if binding is not None:
        applied = apply_contact_binding(p, binding['hand'], binding['vertex']); compare_record(applied, binding)
        contact = next(c for c in p.contacts if c['region'] == 'LeftHand')
        _, faces, target_n = next(n for n in p.normals if n[0] == 'left-grip')
    joint_rows = []
    for row in joint_summary['rows']:
        folder = ROOT/row['folder']; result = read(folder/'result.json')
        if sha256(folder/'result.json') != row['result_sha256'] or sha256(folder/'unprojected-shape.npz') != result['unprojected_pose_sha256']: raise ValueError('Joint artifact changed')
        raw = np.array(result['raw']); fingers = raw[:-5].reshape(-1, 3)
        physical = limits[:, None]*fingers/np.sqrt(1+np.sum(fingers*fingers, axis=1))[:, None]
        np.testing.assert_allclose(physical.ravel(), np.array(result['parameters'])[columns], atol=1e-13)
        geo = geometry(result['parameters'], folder/'unprojected-shape.npz', result['candidate_unprojected'])
        minimum = check_placement(result, geo, joint_protocol['settings'], raw[-5:])
        joint_rows.append(dict(start=row['start'], minimum_clearance_m=minimum, rigid_patch_passed=result['rigid_patch_clearance_passed']))
    output.mkdir(parents=True, exist_ok=False)
    save(output/'verification.json', dict(at=now(), shapes=shape_rows, placements=placement_rows, joint=joint_rows,
         summary_sha256=sha256(shapes/'summary.json'), placements_result_sha256=sha256(placements/'result.json'), joint_summary_sha256=sha256(joint/'summary.json'),
         auditor_sha256=sha256(Path(__file__)), contact_binding=binding, original_edit_and_target_limits_verified=True, frozen_parameters_exact=True, saved_pose_arrays_exact=True,
         scope='Independent NumPy/SciPy reconstruction of recorded bound, shape and rigid-patch placement results. Necessary-bound passes do not substitute for actual patch clearance; no actual projected skeleton pose or animation approval.', quality_approved=False))
    print(dict(shapes=len(shape_rows), placements=len(placement_rows), joint=len(joint_rows), any_joint_patch_pass=any(r['rigid_patch_passed'] for r in joint_rows)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('shapes', type=Path); parser.add_argument('placements', type=Path); parser.add_argument('joint', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.shapes, args.placements, args.joint, args.seed_report, args.output)
