"""Verify twist seeds and diagnose their fixed-shape rigid sphere limitation."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_orientation import hand_frame, twist_target, angular_error
from rigid_grasp_bound import clearance_upper_bound
from audit_grasp_restoration import compare_record, protected, violation


def run(report, seed_report, output):
    report, seed_report, output = [Path(s).resolve() for s in (report, seed_report, output)]
    protocol, summary = read(report/'protocol.json'), read(report/'summary.json')
    if sha256(seed_report/'result.json') != protocol['seed_result_sha256'] or sha256(seed_report/'protocol.json') != protocol['seed_protocol_sha256']:
        raise ValueError('Seed changed')
    for n, digest in protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Input changed')
    for n, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/n) != digest or sha256(report/'implementation'/n) != digest: raise ValueError('Implementation changed')
    fit = ROOT/protocol['study']/'fit'; fit_summary = read(fit/'summary.json')
    if sha256(fit/'summary.json') != protocol['fit_summary_sha256'] or sha256(ASSET) != fit_summary['mesh_sha256']: raise ValueError('Study or mesh changed')
    p = PoseProblem(fit/'assets'/fit_summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    seed = np.array(read(seed_report/'result.json')['parameters']); seed_audit, seed_motion = p.independent(seed)
    compare_record(seed_audit, summary['seed'])
    vertices = p.surface.vertices(seed_motion['global_rot_mats'][0], seed_motion['posed_joints'][0])
    contact = next(c for c in p.contacts if c['region'] == 'LeftHand')
    _, faces, target_normal = next(n for n in p.normals if n[0] == 'left-grip')
    wrist = p.names.index('LeftHand'); knuckles = [p.names.index('LeftHand'+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]
    point, normal, tangent = hand_frame(vertices, seed_motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
    free = [3*p.lookup[p.names.index(n)]+k for n in protocol['edited_joints'] for k in range(3)]
    frozen = [i for i in range(p.dim) if i not in free]
    descendants = []
    for j in range(len(p.parents)):
        while j >= 0 and j != wrist: j = p.parents[j]
        descendants.append(j == wrist)
    patch = np.all(np.array(descendants)[p.skin['lbs_indices']] | (p.skin['lbs_weights'] == 0), axis=1)
    if not np.all(patch[np.unique(faces)]) or not patch[contact['vertex']]: raise ValueError('Contact frame is not wholly in the fixed hand subtree')
    ids = np.flatnonzero(patch)
    sphere, name, center, _ = p.objects[0]
    if sphere.shape != 'sphere': raise ValueError('Sphere required for this diagnostic')
    radial = np.asarray(contact['target'])-center.numpy()[0]
    if np.linalg.norm(np.cross(radial, target_normal.numpy())) > 1e-10:
        raise ValueError('Radial authored normal required for twist-symmetry check')
    rows = []; distances = []
    if len(summary['rows']) != len(protocol['settings']['angles_degrees']): raise ValueError('Missing twist trials')
    for row, angle in zip(summary['rows'], protocol['settings']['angles_degrees']):
        compare_record(row['angle_degrees'], angle)
        folder = ROOT/row['folder']; result = read(folder/'result.json'); trial_protocol = read(folder/'protocol.json')
        if sha256(folder/'result.json') != row['result_sha256'] or sha256(folder/'pose.npz') != result['pose_sha256'] or sha256(folder/'protocol.json') != result['protocol_sha256']:
            raise ValueError('Trial artifact changed')
        if trial_protocol['parent_protocol_sha256'] != sha256(report/'protocol.json'): raise ValueError('Trial protocol binding changed')
        target = twist_target(normal, tangent, target_normal.numpy(), angle)
        np.testing.assert_allclose(target, trial_protocol['tangent_target'], atol=1e-12)
        x = np.array(result['parameters']); np.testing.assert_array_equal(x[frozen], seed[frozen])
        audit, motion = p.independent(x); compare_record(audit, result['candidate']); compare_record(audit, row['candidate'])
        with np.load(folder/'pose.npz', allow_pickle=False) as saved:
            if set(saved.files) != set(motion): raise ValueError('Pose arrays changed')
            for key, value in motion.items(): np.testing.assert_array_equal(saved[key], value)
        skin = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
        q, n, t = hand_frame(skin, motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
        reach = dict(point_error_m=float(np.linalg.norm(q-contact['target'])), normal_error_degrees=angular_error(n, target_normal.numpy()), tangent_error_degrees=angular_error(t, target))
        compare_record(reach, result['reach'])
        reached = reach['point_error_m'] <= protocol['settings']['reach_point_tolerance_m'] and max(reach['normal_error_degrees'], reach['tangent_error_degrees']) <= protocol['settings']['reach_direction_tolerance_degrees']
        compare_record(bool(reached), result['target_reached']); compare_record(protected(audit, p.config), result['protected_pass'])
        compare_record(violation(audit, p.config), row['clearance_violation_m'])
        distances.append(np.linalg.norm(skin[ids]-center.numpy()[0], axis=1)-sphere.dimensions[0])
        rows.append(dict(angle_degrees=angle, reach=reach, candidate=audit, saved_pose_arrays_exact=True, frozen_parameters_exact=True))
    distance_spread = float(np.ptp(np.array(distances), axis=0).max())
    tolerance_m = 2e-6
    if distance_spread > tolerance_m: raise ValueError('Measured twists do not confirm rigid sphere symmetry within tolerance')
    violation_spread = float(np.ptp([violation(row['candidate'], p.config) for row in rows]))
    # This bound is exact for rigid transforms of the measured patch. We do
    # not claim an exact equivalence to finite-precision LBS under arbitrary
    # skeleton transforms, nor permit its shape to change through finger edits.
    upper = clearance_upper_bound(vertices[ids]-point, normal, contact['target'], target_normal.numpy(), center.numpy()[0], sphere.dimensions[0],
                                  p.config['point_tolerance_m']+1e-6, p.config['normal_tolerance_degrees']+1e-4)+tolerance_m
    worst_slot = int(np.argmin(upper)); worst = int(ids[worst_slot]); required = p.config['object_clearance_m']-1e-6
    bound = dict(model='Rigid transforms of the measured fixed hand patch', vertex=worst,
                 best_signed_clearance_upper_bound_m=float(upper[worst_slot]), required_clearance_with_numeric_tolerance_m=required,
                 rigid_patch_obstruction=bool(upper[worst_slot] < required), obstructed_vertices=int((upper < required).sum()),
                 patch_vertices=len(ids), numeric_allowance_m=tolerance_m, exact_LBS_equivalence_certified=False,
                 weights=[dict(joint=p.names[int(j)], weight=float(w)) for j, w in zip(p.skin['lbs_indices'][worst], p.skin['lbs_weights'][worst]) if w > 0],
                 scope='Allows arbitrary rigid patch translations within the original point tolerance, normal tilts within the original cone and all twists. Fingers/shape fixed. Does not prove infeasibility with finger articulation or for the full original LBS optimization.')
    output.mkdir(parents=True, exist_ok=False)
    save(output/'verification.json', dict(at=now(), protocol_sha256=sha256(report/'protocol.json'), summary_sha256=sha256(report/'summary.json'),
         auditor_sha256=sha256(Path(__file__)), bound_source_sha256=sha256(ROOT/'scripts/rigid_grasp_bound.py'), rows=rows,
         maximum_patch_distance_spread_m=distance_spread, numerical_tie_tolerance_m=tolerance_m,
         full_skin_violation_spread_m=violation_spread, all_twists_numerically_tied=violation_spread <= tolerance_m,
         raw_best_seed_is_not_meaningfully_better=violation_spread <= tolerance_m, rigid_patch_bound=bound, quality_approved=False))
    print(dict(trials=len(rows), maximum_distance_spread_m=distance_spread, rigid_patch_bound=bound))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('report', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.report, args.seed_report, args.output)
