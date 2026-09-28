"""Project a declared rigid region candidate onto the original bounded arm chain."""
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
from grasp_contact_binding import apply_region_binding
from grasp_orientation import hand_frame, angular_error
from probe_sphere_region_support import contact_triangle


def run(region_report, seed_report, output):
    torch.set_num_threads(2)
    region_report, seed_report, output = [Path(v).resolve() for v in (region_report, seed_report, output)]
    rp, rr = read(region_report/'protocol.json'), read(region_report/'result.json')
    sr, sp = read(seed_report/'result.json'), read(seed_report/'protocol.json')
    if rr['best'] is None: raise ValueError('No passing rigid region candidate to project')
    bindings = {region_report/'probe_sphere_region_support.py': rp['implementation_sha256'],
                seed_report/'result.json': rp['seed_result_sha256'], seed_report/'protocol.json': rp['seed_protocol_sha256'],
                seed_report/'pose.npz': sr['pose_sha256'], ASSET: rp['mesh_sha256']}
    bindings.update({ROOT/n: digest for n, digest in rp['inputs'].items()})
    fit = ROOT/rp['study']/'fit'
    bindings[fit/'summary.json'] = sp['fit_summary_sha256']
    for path, digest in bindings.items():
        if sha256(path) != digest: raise ValueError(f'Input changed: {path.name}')
    summary = read(fit/'summary.json')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), rp['frame'])
    best = rr['best']; hand = rp['patch']['hand']; seed = np.array(sr['parameters'])
    binding = apply_region_binding(p, hand, best['anchor'], rp['patch'])
    before, motion = p.independent(seed)
    if not before['rotation_norm_bounds_passed']: raise ValueError('Original edit limits violated')
    contact = next(c for c in p.contacts if c['region'] == hand)
    faces = next(f for name, f, n in p.normals if name == binding['normal_id'])
    wrist = p.names.index(hand); knuckles = [p.names.index(hand+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]
    vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
    point, normal, tangent = hand_frame(vertices, motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
    rotation = np.array(best['rotation_from_source'])
    np.testing.assert_allclose(rotation.T@rotation, np.eye(3), atol=1e-10)
    np.testing.assert_allclose(np.linalg.det(rotation), 1., atol=1e-10)
    target_point = np.array(rr['desired_anchor_point']); target_normal = rotation@normal; target_tangent = rotation@tangent
    sphere, _, center, _ = p.objects[0]
    if sphere.shape != 'sphere': raise ValueError('Sphere required')
    patch_ids = np.array(rp['patch']['vertices'])
    rigid = (vertices[patch_ids]-point)@rotation.T+target_point
    rigid_triangle = contact_triangle(rigid, patch_ids, np.array(contact['target']), np.linalg.norm(rigid-center.numpy()[0], axis=1)-sphere.dimensions[0], rp['limits'])
    if rigid_triangle is None: raise ValueError('Selected contact triangle no longer passes')
    prefix = hand.removesuffix('Hand'); joints = [prefix+n for n in ['Shoulder', 'Arm', 'ForeArm', 'Hand']]
    slots = np.array([p.lookup[p.names.index(n)] for n in joints]); limits = p.limits[slots]
    columns = np.array([3*i+k for i in slots for k in range(3)]); frozen = np.setdiff1d(np.arange(p.dim), columns)
    initial = inverse_rotation_bound(seed[columns].reshape(-1, 3), limits).ravel()
    settings = dict(maximum_evaluations=160, seconds=80, maximum_rss_bytes=2*1024**3, minimum_available_bytes=int(1.25*1024**3),
                    point_scale_m=.001, direction_scale=.01, regularization=1e-5, reach_point_m=.0001, reach_direction_degrees=.1)
    output.mkdir(parents=True, exist_ok=False); (output/'implementation').mkdir()
    methods = ['project_sphere_region.py', 'grasp_contact_binding.py', 'probe_sphere_region_support.py', 'grasp_orientation.py',
               'grasp_pose_witness.py', 'grasp_pose_witness_bounded.py', 'support_contact_v8.py', 'support_contact_v5.py',
               'floor_contact.py', 'scene_solver_context.py', 'object_geometry.py', 'inspect_motion.py']
    implementation = {n: sha256(ROOT/'scripts'/n) for n in methods}
    for n in methods: shutil.copyfile(ROOT/'scripts'/n, output/'implementation'/n)
    protocol = dict(at=now(), region_report=region_report.relative_to(ROOT).as_posix(), region_protocol_sha256=sha256(region_report/'protocol.json'),
                    region_result_sha256=sha256(region_report/'result.json'), seed_report=seed_report.relative_to(ROOT).as_posix(),
                    inputs={path.relative_to(ROOT).as_posix(): digest for path, digest in bindings.items()}, implementation=implementation,
                    settings=settings, edited_joints=joints, contact_binding=binding, target_point=target_point.tolist(),
                    target_normal=target_normal.tolist(), target_tangent=target_tangent.tolist(),
                    scope='New region condition, original bounded arm chain only. Finger, other arm, torso, legs and root parameters frozen. Full skin/object/floor checked after fitting. No temporal, anatomy, self-collision or animation approval.', quality_approved=False)
    save(output/'protocol.json', protocol)
    started = time.monotonic(); cache = None; last = initial.copy(); evaluations = 0; peak = 0
    def parameters(raw):
        theta = bounded_rotation(raw.reshape(-1, 3)/p.t(limits)[:, None], p.t(limits)[:, None]).reshape(-1)
        return p.t(seed).index_copy(0, torch.as_tensor(columns), theta)
    def geometry(raw):
        _, positions, _, v = p.fk(parameters(raw)); tri = v[faces]
        n = torch.linalg.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0); n = n/torch.linalg.vector_norm(n)
        d = positions[knuckles].mean(0)-positions[wrist]; t = d-n*(n@d); t = t/torch.linalg.vector_norm(t)
        return torch.cat([(v[contact['vertex']]-p.t(target_point))/settings['point_scale_m'],
                          (n-p.t(target_normal))/settings['direction_scale'], (t-p.t(target_tangent))/settings['direction_scale']])
    def pair(raw):
        nonlocal cache, last, evaluations, peak
        if cache is not None and np.array_equal(raw, cache[0]): return cache[1:]
        variable = p.t(raw).requires_grad_(); values = geometry(variable)
        jac = np.array([torch.autograd.grad(v, variable, retain_graph=True)[0].detach().numpy() for v in values])
        residual = np.r_[values.detach().numpy(), settings['regularization']*(raw-initial)]
        jac = np.r_[jac, settings['regularization']*np.eye(len(raw))]
        last = raw.copy(); evaluations += 1; peak = max(peak, psutil.Process().memory_info().rss)
        if time.monotonic()-started > settings['seconds'] or peak > settings['maximum_rss_bytes'] or psutil.virtual_memory().available < settings['minimum_available_bytes']:
            raise TimeoutError('Projection resource guard')
        cache = raw.copy(), residual, jac
        return residual, jac
    _, jac = pair(initial); direction = np.random.default_rng(721).normal(size=len(initial)); direction /= np.linalg.norm(direction); h = 1e-6
    with torch.no_grad(): fd = ((geometry(p.t(initial+h*direction))-geometry(p.t(initial-h*direction)))/(2*h)).numpy()
    np.testing.assert_allclose(jac[:9]@direction, fd, atol=2e-5, rtol=2e-4)
    derivative_error = float(np.max(np.abs(jac[:9]@direction-fd)))
    status = 'complete'
    try:
        solve = least_squares(lambda raw: pair(raw)[0], initial, jac=lambda raw: pair(raw)[1], max_nfev=settings['maximum_evaluations'], ftol=1e-10, xtol=1e-10, gtol=1e-10)
        last = solve.x; solver = dict(success=bool(solve.success), message=str(solve.message), evaluations=int(solve.nfev))
    except TimeoutError as exc:
        status = 'interrupted_resource_guard'; solver = dict(success=False, message=str(exc))
    physical = parameters(p.t(last)).detach().numpy(); audit, motion = p.independent(physical)
    np.testing.assert_array_equal(physical[frozen], seed[frozen])
    vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
    point, normal, tangent = hand_frame(vertices, motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
    reach = dict(point_error_m=float(np.linalg.norm(point-target_point)), normal_error_degrees=angular_error(normal, target_normal), tangent_error_degrees=angular_error(tangent, target_tangent))
    reached = reach['point_error_m'] <= settings['reach_point_m'] and max(reach['normal_error_degrees'], reach['tangent_error_degrees']) <= settings['reach_direction_degrees']
    region_gaps = np.linalg.norm(vertices[patch_ids]-center.numpy()[0], axis=1)-sphere.dimensions[0]
    triangle = contact_triangle(vertices[patch_ids], patch_ids, np.array(contact['target']), region_gaps, rp['limits'])
    with torch.no_grad(): _, _, _, torch_vertices = p.fk(p.t(physical))
    skin_error = float(np.max(np.abs(torch_vertices.numpy()-vertices)))
    if skin_error > 2e-6: raise ValueError('Independent full-skin mismatch')
    np.savez(output/'pose.npz', **motion)
    for path, digest in bindings.items():
        if sha256(path) != digest: raise ValueError('Input changed during projection')
    for name, digest in implementation.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Implementation changed during projection')
    result = dict(at=now(), status=status, solver=solver, parameters=physical.tolist(), raw_parameters=last.tolist(), before=before, candidate=audit,
                  reach=reach, target_reached=bool(reached), contact_triangle=triangle, frozen_parameters_exact=True,
                  region_pose_passed=bool(reached and triangle is not None and audit['pose_witness_passed']),
                  independent_skin_max_error_m=skin_error, derivative_error=derivative_error, seconds=time.monotonic()-started,
                  evaluations=evaluations, sampled_peak_rss_bytes=peak, pose_sha256=sha256(output/'pose.npz'), protocol_sha256=sha256(output/'protocol.json'), quality_approved=False)
    save(output/'result.json', result)
    print(dict(status=status, reach=reach, candidate=audit, contact_triangle=triangle, region_pose_passed=result['region_pose_passed']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('region_report', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=2): run(args.region_report, args.seed_report, args.output)
