"""Predeclared left-hand orientation seeds under the original grasp edit limits."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from scipy.optimize import least_squares
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_pose_witness_bounded import inverse_rotation_bound
from support_contact_v8 import bounded_rotation
from restore_grasp_pose import protected_pass, clearance_violation
from grasp_orientation import hand_frame, twist_target, angular_error


def run(study, seed_report, output):
    torch.set_num_threads(2)
    study, seed_report, output = [Path(s).resolve() for s in (study, seed_report, output)]
    fit = study/'fit'; summary = read(fit/'summary.json')
    seed_result, seed_protocol = read(seed_report/'result.json'), read(seed_report/'protocol.json')
    if summary['solver_version'] != 13 or sha256(fit/'summary.json') != seed_protocol['fit_summary_sha256']:
        raise ValueError('Matched V13 study required')
    if sha256(ASSET) != summary['mesh_sha256'] or sha256(seed_report/'pose.npz') != seed_result['pose_sha256']:
        raise ValueError('Mesh or seed changed')
    for name, digest in seed_protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Input changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), seed_protocol['frame'])
    seed = np.array(seed_result['parameters']); before, seed_motion = p.independent(seed)
    if not protected_pass(before, p.config): raise ValueError('Protected seed required')
    hand = 'LeftHand'; contact = next(c for c in p.contacts if c['region'] == hand)
    normal_id, faces, normal_target = next(n for n in p.normals if n[0] == 'left-grip')
    wrist = p.names.index(hand); knuckles = [p.names.index(hand+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]
    skin = p.surface.vertices(seed_motion['global_rot_mats'][0], seed_motion['posed_joints'][0])
    _, seed_normal, seed_tangent = hand_frame(skin, seed_motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
    joints = ['LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand']
    slots = np.array([p.lookup[p.names.index(n)] for n in joints]); limits = p.limits[slots]
    columns = np.array([3*i+k for i in slots for k in range(3)])
    frozen = np.array([i for i in range(p.dim) if i not in columns])
    initial = inverse_rotation_bound(seed[columns].reshape(-1, 3), limits).ravel()
    output.mkdir(parents=True, exist_ok=False); (output/'implementation').mkdir()
    methods = ['study_grasp_twists.py', 'grasp_orientation.py', 'grasp_pose_witness.py', 'grasp_pose_witness_bounded.py',
               'restore_grasp_pose.py', 'support_contact_v8.py', 'support_contact_v5.py', 'floor_contact.py', 'scene_solver_context.py', 'object_geometry.py']
    settings = dict(angles_degrees=[-20., -10., 0., 10., 20.], maximum_evaluations=160, seconds_per_trial=80,
                    maximum_rss_bytes=2*1024**3, minimum_available_bytes=int(1.25*1024**3),
                    reach_point_tolerance_m=.0001, reach_direction_tolerance_degrees=.1,
                    residual_point_scale_m=.001, residual_direction_scale=.01, regularization=1e-5)
    protocol = dict(at=now(), study=study.relative_to(ROOT).as_posix(), frame=p.frame, settings=settings,
                    inputs=seed_protocol['inputs'], fit_summary_sha256=sha256(fit/'summary.json'),
                    seed_result_sha256=sha256(seed_report/'result.json'), seed_protocol_sha256=sha256(seed_report/'protocol.json'),
                    implementation={n: sha256(ROOT/'scripts'/n) for n in methods}, edited_joints=joints,
                    reference_normal=seed_normal.tolist(), reference_tangent=seed_tangent.tolist(),
                    authored_point=contact['target'], authored_normal=normal_target.tolist(), quality_approved=False,
                    selection='Retain every seed. Among reached, original-protected-gate-passing seeds, identify the lowest exact object-clearance violation; no automatic quality promotion.',
                    scope='Align measured palm normal to authored normal, then apply fixed signed twist around that normal. Fit skinned palm point/normal and knuckle tangent. Only original left arm chain rotates; original norm limits apply. Fingers, right arm, torso, legs and root remain fixed. Clearance is measured after projection, not optimized during seed construction. No temporal, anatomical, balance or self-collision claim.')
    save(output/'protocol.json', protocol)
    for n in methods: shutil.copyfile(ROOT/'scripts'/n, output/'implementation'/n)
    rows = []
    for angle in settings['angles_degrees']:
        folder = output/f'twist-{int(angle):+03d}'; folder.mkdir()
        tangent_target = twist_target(seed_normal, seed_tangent, normal_target.numpy(), angle)
        trial_protocol = dict(protocol, angle_degrees=angle, tangent_target=tangent_target.tolist(), parent_protocol_sha256=sha256(output/'protocol.json'))
        save(folder/'protocol.json', trial_protocol)
        started = time.monotonic(); cache = None; evaluations = 0; peak = 0; last = initial.copy(); status = 'complete'
        def parameters(raw):
            theta = bounded_rotation(raw.reshape(-1, 3)/p.t(limits)[:, None], p.t(limits)[:, None]).reshape(-1)
            return p.t(seed).index_copy(0, torch.as_tensor(columns), theta)
        def geometry(raw):
            _, positions, _, vertices = p.fk(parameters(raw))
            tri = vertices[faces]; normal = torch.linalg.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0)
            normal = normal/torch.linalg.vector_norm(normal)
            direction = positions[knuckles].mean(0)-positions[wrist]
            tangent = direction-normal*(normal@direction); tangent = tangent/torch.linalg.vector_norm(tangent)
            return torch.cat([(vertices[contact['vertex']]-p.t(contact['target']))/.001,
                              (normal-normal_target)/.01, (tangent-p.t(tangent_target))/.01])
        def pair(raw):
            nonlocal cache, evaluations, peak, last
            if cache is not None and np.array_equal(raw, cache[0]): return cache[1:]
            variable = p.t(raw).requires_grad_(); values = geometry(variable)
            jac = np.array([torch.autograd.grad(v, variable, retain_graph=True)[0].detach().numpy() for v in values])
            residual = np.r_[values.detach().numpy(), settings['regularization']*(raw-initial)]
            jac = np.r_[jac, settings['regularization']*np.eye(len(raw))]
            evaluations += 1; last = raw.copy(); peak = max(peak, psutil.Process().memory_info().rss)
            if time.monotonic()-started > settings['seconds_per_trial'] or peak > settings['maximum_rss_bytes'] or psutil.virtual_memory().available < settings['minimum_available_bytes']:
                raise TimeoutError('Twist projection resource guard')
            cache = raw.copy(), residual, jac
            return residual, jac
        values, jac = pair(initial)
        direction = np.random.default_rng(719).normal(size=len(initial)); direction /= np.linalg.norm(direction); h = 1e-6
        with torch.no_grad(): fd = ((geometry(p.t(initial+h*direction))-geometry(p.t(initial-h*direction)))/(2*h)).numpy()
        derivative_error = float(np.max(np.abs(jac[:9]@direction-fd)))
        np.testing.assert_allclose(jac[:9]@direction, fd, atol=2e-5, rtol=2e-4)
        try:
            solve = least_squares(lambda raw: pair(raw)[0], initial, jac=lambda raw: pair(raw)[1], max_nfev=settings['maximum_evaluations'], ftol=1e-10, xtol=1e-10, gtol=1e-10)
            last = solve.x; solver = dict(success=bool(solve.success), message=str(solve.message), evaluations=int(solve.nfev))
        except TimeoutError as e:
            status = 'interrupted_resource_guard'; solver = dict(success=False, message=str(e))
        physical = parameters(p.t(last)).detach().numpy(); audit, motion = p.independent(physical)
        np.testing.assert_array_equal(physical[frozen], seed[frozen])
        vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
        point, normal, tangent = hand_frame(vertices, motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
        reach = dict(point_error_m=float(np.linalg.norm(point-contact['target'])), normal_error_degrees=angular_error(normal, normal_target.numpy()), tangent_error_degrees=angular_error(tangent, tangent_target))
        reached = reach['point_error_m'] <= settings['reach_point_tolerance_m'] and max(reach['normal_error_degrees'], reach['tangent_error_degrees']) <= settings['reach_direction_tolerance_degrees']
        with torch.no_grad(): _, _, _, torch_skin = p.fk(p.t(physical))
        skin_error = float(np.max(np.abs(torch_skin.numpy()-vertices)))
        if skin_error > 2e-6: raise ValueError('Independent skin mismatch')
        np.savez(folder/'pose.npz', **motion)
        result = dict(at=now(), status=status, solver=solver, angle_degrees=angle, parameters=physical.tolist(), candidate=audit,
                      reach=reach, target_reached=bool(reached), protected_pass=protected_pass(audit, p.config), frozen_parameters_exact=True,
                      evaluations=evaluations, seconds=time.monotonic()-started, sampled_peak_rss_bytes=peak, derivative_error=derivative_error,
                      independent_skin_max_error_m=skin_error, pose_sha256=sha256(folder/'pose.npz'), protocol_sha256=sha256(folder/'protocol.json'), quality_approved=False)
        save(folder/'result.json', result)
        row = dict(folder=folder.relative_to(ROOT).as_posix(), angle_degrees=angle, target_reached=bool(reached), protected_pass=result['protected_pass'],
                   clearance_violation_m=clearance_violation(audit, p.config), result_sha256=sha256(folder/'result.json'), candidate=audit)
        rows.append(row); save(output/'progress.json', dict(rows=rows, status='running')); print(row, flush=True)
    eligible = [row for row in rows if row['target_reached'] and row['protected_pass']]
    best = min(eligible, key=lambda row: row['clearance_violation_m'])['folder'] if eligible else None
    for n, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/n) != digest: raise ValueError('Implementation changed')
    for n, digest in protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Input changed')
    save(output/'summary.json', dict(at=now(), status='complete', rows=rows, best_reachable_seed=best, seed=before, quality_approved=False))
    save(output/'pipeline.json', dict(status='complete', quality_approved=False)); print(dict(best_reachable_seed=best), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=2): run(args.study, args.seed_report, args.output)
