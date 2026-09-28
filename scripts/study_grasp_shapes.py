"""Search bounded finger shapes using a necessary rigid-clearance diagnostic."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_pose_witness_bounded import inverse_rotation_bound
from support_contact_v8 import bounded_rotation
from grasp_shape_bound import radial_clearance_upper
from rigid_grasp_bound import clearance_upper_bound


def run(study, seed_report, output):
    torch.set_num_threads(2)
    study, seed_report, output = [Path(s).resolve() for s in (study, seed_report, output)]
    fit = study/'fit'; summary = read(fit/'summary.json')
    seed_record, seed_protocol = read(seed_report/'result.json'), read(seed_report/'protocol.json')
    if summary['solver_version'] != 13 or sha256(fit/'summary.json') != seed_protocol['fit_summary_sha256'] or sha256(ASSET) != summary['mesh_sha256']:
        raise ValueError('Matched V13 study and mesh required')
    if sha256(seed_report/'pose.npz') != seed_record['pose_sha256']: raise ValueError('Seed changed')
    for n, digest in seed_protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Input changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), seed_protocol['frame'])
    seed = np.array(seed_record['parameters']); contact = next(c for c in p.contacts if c['region'] == 'LeftHand')
    _, faces, target_normal = next(n for n in p.normals if n[0] == 'left-grip')
    geometry, object_name, center, _ = p.objects[0]; radial = np.array(contact['target'])-center.numpy()[0]; distance = np.linalg.norm(radial)
    if geometry.shape != 'sphere' or distance <= 0 or abs(radial@target_normal.numpy()/distance+1) > 1e-10:
        raise ValueError('Inward radial sphere contact required')
    wrist = p.names.index('LeftHand'); descendants = []
    for j in range(len(p.parents)):
        while j >= 0 and j != wrist: j = p.parents[j]
        descendants.append(j == wrist)
    ids = np.flatnonzero(np.all(np.array(descendants)[p.skin['lbs_indices']] | (p.skin['lbs_weights'] == 0), axis=1))
    if not set(np.unique(faces)).issubset(set(ids)) or contact['vertex'] not in ids: raise ValueError('Contact frame outside hand patch')
    slots = np.array([i for i, j in enumerate(p.editable) if p.names[j].startswith('LeftHand') and p.names[j] != 'LeftHand'])
    columns = np.array([3*i+k for i in slots for k in range(3)]); frozen = np.array([i for i in range(p.dim) if i not in columns]); limits = p.limits[slots]
    output.mkdir(parents=True, exist_ok=False); (output/'implementation').mkdir()
    methods = ['study_grasp_shapes.py', 'grasp_shape_bound.py', 'rigid_grasp_bound.py', 'grasp_orientation.py', 'grasp_pose_witness.py',
               'grasp_pose_witness_bounded.py', 'support_contact_v8.py', 'support_contact_v5.py', 'floor_contact.py', 'scene_solver_context.py', 'object_geometry.py']
    settings = dict(starts=[dict(name='current', scale=1.), dict(name='half', scale=.5), dict(name='reference', scale=0.)],
                    maximum_iterations=180, maximum_evaluations=240, seconds_per_trial=80, maximum_rss_bytes=2*1024**3,
                    minimum_available_bytes=int(1.25*1024**3), smooth_min_temperature_m=.00005, numeric_allowance_m=2e-6)
    protocol = dict(at=now(), study=study.relative_to(ROOT).as_posix(), frame=p.frame, settings=settings, inputs=seed_protocol['inputs'],
                    fit_summary_sha256=sha256(fit/'summary.json'), seed_result_sha256=sha256(seed_report/'result.json'), seed_protocol_sha256=sha256(seed_report/'protocol.json'),
                    implementation={n: sha256(ROOT/'scripts'/n) for n in methods}, variable_joints=[p.names[p.editable[i]] for i in slots],
                    patch_vertices=ids.tolist(), selection='Retain all three local searches; select best visited exact minimum upper bound per search, then rank completed shapes by that quantity. Bound passing is never pose passing.',
                    scope='Left-finger shape search inside original rotation-norm budgets; all body/root/right-finger parameters fixed. Optimize a conservative smooth minimum of per-vertex rigid-patch clearance upper bounds. Necessary geometric diagnostic only, not actual clearance, anatomy, temporal quality or an exact original-LBS infeasibility proof.', quality_approved=False)
    save(output/'protocol.json', protocol)
    for n in methods: shutil.copyfile(ROOT/'scripts'/n, output/'implementation'/n)
    rows = []
    for setting in settings['starts']:
        folder = output/setting['name']; folder.mkdir(); save(folder/'protocol.json', dict(protocol, start=setting, parent_protocol_sha256=sha256(output/'protocol.json')))
        initial = inverse_rotation_bound(seed[columns].reshape(-1, 3)*setting['scale'], limits).ravel()
        started = time.monotonic(); cache = None; evaluations = 0; peak = 0; history = []; best = None; last = initial.copy(); status = 'complete'
        def physical(raw):
            theta = bounded_rotation(raw.reshape(-1, 3)/p.t(limits)[:, None], p.t(limits)[:, None]).reshape(-1)
            return p.t(seed).index_copy(0, torch.as_tensor(columns), theta)
        def quantities(raw):
            parameters = physical(raw); _, _, _, vertices = p.fk(parameters)
            tri = vertices[faces]; normal = torch.linalg.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0); normal = normal/torch.linalg.vector_norm(normal)
            upper = radial_clearance_upper(vertices[ids]-vertices[contact['vertex']], normal, distance, geometry.dimensions[0],
                                          p.config['point_tolerance_m']+1e-6, p.config['normal_tolerance_degrees']+1e-4)+settings['numeric_allowance_m']
            tau = settings['smooth_min_temperature_m']; smooth = -tau*torch.logsumexp(-upper/tau, dim=0)
            regularization = 1e-6*torch.sum(((parameters[columns]-p.t(seed[columns]))/p.t(np.repeat(limits, 3)))**2)
            return -smooth/.01+regularization, upper, smooth
        def pair(raw):
            nonlocal cache, evaluations, peak, best, last
            if cache is not None and np.array_equal(cache[0], raw): return cache[1:]
            variable = p.t(raw).requires_grad_(); loss, upper, smooth = quantities(variable)
            gradient = torch.autograd.grad(loss, variable)[0].detach().numpy(); value = float(loss.detach()); exact = float(upper.detach().min())
            if not np.isfinite(value) or not np.isfinite(gradient).all(): raise ValueError('Nonfinite shape objective')
            evaluations += 1; last = raw.copy(); peak = max(peak, psutil.Process().memory_info().rss)
            history.append(dict(evaluation=evaluations, exact_minimum_upper_m=exact, smooth_minimum_upper_m=float(smooth.detach()), loss=value))
            if best is None or exact > best[0]: best = exact, raw.copy()
            if time.monotonic()-started > settings['seconds_per_trial'] or peak > settings['maximum_rss_bytes'] or psutil.virtual_memory().available < settings['minimum_available_bytes']:
                raise TimeoutError('Shape search resource guard')
            cache = raw.copy(), value, gradient
            return value, gradient
        value, gradient = pair(initial)
        direction = np.random.default_rng(120).normal(size=len(initial)); direction /= np.linalg.norm(direction); h = 1e-6
        with torch.no_grad(): fd = float((quantities(p.t(initial+h*direction))[0]-quantities(p.t(initial-h*direction))[0])/(2*h))
        np.testing.assert_allclose(gradient@direction, fd, atol=2e-6, rtol=2e-4)
        try:
            solution = minimize(pair, initial, jac=True, method='L-BFGS-B', options=dict(maxiter=settings['maximum_iterations'], maxfun=settings['maximum_evaluations'], ftol=1e-12, gtol=1e-9))
            last = solution.x; solver = dict(success=bool(solution.success), message=str(solution.message), evaluations=int(solution.nfev))
        except TimeoutError as e:
            status = 'interrupted_resource_guard'; solver = dict(success=False, message=str(e))
        parameters = physical(p.t(best[1])).detach().numpy(); audit, motion = p.independent(parameters)
        np.testing.assert_array_equal(parameters[frozen], seed[frozen])
        if not audit['rotation_norm_bounds_passed']: raise ValueError('Shape violates original edit budgets')
        vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0]); tri = vertices[faces]
        normal = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0); normal /= np.linalg.norm(normal)
        independent = clearance_upper_bound(vertices[ids]-vertices[contact['vertex']], normal, contact['target'], target_normal.numpy(), center.numpy()[0],
                                            geometry.dimensions[0], p.config['point_tolerance_m']+1e-6, p.config['normal_tolerance_degrees']+1e-4)+settings['numeric_allowance_m']
        with torch.no_grad(): _, upper, _ = quantities(p.t(best[1])); _, _, _, tv = p.fk(p.t(parameters))
        bound_error = float(np.max(np.abs(upper.numpy()-independent))); skin_error = float(np.max(np.abs(tv.numpy()-vertices)))
        if bound_error > 2e-6 or skin_error > 2e-6: raise ValueError('Independent bound or skin mismatch')
        required = p.config['object_clearance_m']-1e-6; minimum = float(independent.min())
        np.savez(folder/'pose.npz', **motion)
        result = dict(at=now(), status=status, solver=solver, parameters=parameters.tolist(), candidate=audit, minimum_rigid_upper_m=minimum,
                      necessary_rigid_bound_passed=minimum >= required, worst_patch_vertex=int(ids[np.argmin(independent)]), frozen_parameters_exact=True,
                      final_solver_parameters=physical(p.t(last)).detach().numpy().tolist(), history=history, evaluations=evaluations, seconds=time.monotonic()-started,
                      sampled_peak_rss_bytes=peak, derivative_error=abs(float(gradient@direction)-fd), independent_bound_max_error_m=bound_error,
                      independent_skin_max_error_m=skin_error, pose_sha256=sha256(folder/'pose.npz'), protocol_sha256=sha256(folder/'protocol.json'), quality_approved=False)
        save(folder/'result.json', result)
        row = dict(folder=folder.relative_to(ROOT).as_posix(), start=setting['name'], minimum_rigid_upper_m=minimum, necessary_rigid_bound_passed=minimum >= required,
                   pose_witness_passed=audit['pose_witness_passed'], result_sha256=sha256(folder/'result.json'))
        rows.append(row); save(output/'progress.json', dict(rows=rows, status='running')); print(row, flush=True)
    for n, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/n) != digest: raise ValueError('Implementation changed')
    for n, digest in protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Input changed')
    save(output/'summary.json', dict(at=now(), status='complete', rows=rows, best_shape=max(rows, key=lambda row: row['minimum_rigid_upper_m'])['folder'], quality_approved=False))
    save(output/'pipeline.json', dict(status='complete', quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=2): run(args.study, args.seed_report, args.output)
