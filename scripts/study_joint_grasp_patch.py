"""Joint finger-shape and rigid hand-placement search with original limits."""
import argparse
import time
from pathlib import Path
import numpy as np
import torch
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_orientation import unit, hand_frame, align_direction, angular_error
from study_grasp_placements import placement


def differentiable_alignment(source, target):
    cross = torch.linalg.cross(source, target); zero = cross[0]*0
    k = torch.stack([zero, -cross[2], cross[1], cross[2], zero, -cross[0], -cross[1], cross[0], zero]).reshape(3, 3)
    return torch.eye(3, dtype=source.dtype, device=source.device)+k+k@k/(1+source@target)


def run(shapes, placements, seed_report, output):
    torch.set_num_threads(2); shapes, placements, seed_report, output = [Path(s).resolve() for s in (shapes, placements, seed_report, output)]
    protocol = read(shapes/'protocol.json'); placed = read(placements/'result.json'); fit = ROOT/protocol['study']/'fit'; summary = read(fit/'summary.json')
    if sha256(fit/'summary.json') != protocol['fit_summary_sha256'] or sha256(ASSET) != summary['mesh_sha256'] or sha256(seed_report/'result.json') != protocol['seed_result_sha256']: raise ValueError('Inputs changed')
    for n, digest in protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Source input changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    seed = np.array(read(seed_report/'result.json')['parameters']); contact = next(c for c in p.contacts if c['region'] == 'LeftHand')
    _, faces, target_n = next(n for n in p.normals if n[0] == 'left-grip'); sphere, _, center, _ = p.objects[0]
    if sphere.shape != 'sphere' or abs(unit(np.array(contact['target'])-center.numpy()[0])@target_n.numpy()+1) > 1e-10: raise ValueError('Radial sphere required')
    ids = np.array(protocol['patch_vertices']); slots = [i for i, j in enumerate(p.editable) if p.names[j] in protocol['variable_joints']]
    columns = np.array([3*i+k for i in slots for k in range(3)]); frozen = [i for i in range(p.dim) if i not in columns]; limits = p.limits[slots]
    wrist = p.names.index('LeftHand'); knuckles = [p.names.index('LeftHand'+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]
    t1 = unit(np.cross(target_n.numpy(), np.eye(3)[np.argmin(np.abs(target_n.numpy()))])); basis = np.c_[t1, np.cross(target_n.numpy(), t1)]
    point_limit = p.config['point_tolerance_m']-1e-6; angle_limit = np.deg2rad(p.config['normal_tolerance_degrees']-.001)
    optimized = max([r for r in placed['rows'] if r['shape'].endswith('/current')], key=lambda r: r['minimum_clearance_m'])
    optimized_shape = np.array(read(ROOT/optimized['shape']/'result.json')['parameters'])
    def encode(angles):
        scaled = angles.reshape(-1, 3)/limits[:, None]
        if np.any(np.sum(scaled**2, axis=1) >= 1): raise ValueError('Interior finger seed required')
        return (scaled/np.sqrt(1-np.sum(scaled**2, axis=1))[:, None]).ravel()
    starts = [('original_shape_centered', np.r_[encode(seed[columns]), np.zeros(5)]),
              ('searched_shape_placed', np.r_[encode(optimized_shape[columns]), optimized['raw']]),
              ('reference_shape_centered', np.zeros(len(columns)+5))]
    output.mkdir(parents=True, exist_ok=False)
    settings = dict(starts=[n for n, _ in starts], maximum_iterations=250, maximum_evaluations=400, seconds_per_trial=80,
                    point_limit_m=point_limit, angle_limit_radians=angle_limit, smooth_min_temperature_m=.00005)
    save(output/'protocol.json', dict(at=now(), shapes_protocol_sha256=sha256(shapes/'protocol.json'), placements_result_sha256=sha256(placements/'result.json'),
         seed_result_sha256=sha256(seed_report/'result.json'), inputs=protocol['inputs'], settings=settings,
         implementation_sha256=sha256(Path(__file__)), placement_source_sha256=sha256(ROOT/'scripts/study_grasp_placements.py'),
         scope='Joint left-finger shapes and actual rigid-patch placement, original finger norm/point/normal limits. Final target still needs arm IK and full-body collision validation. Saved shape pose has NOT had the desired rigid placement applied to its skeleton.', quality_approved=False))
    rows = []
    for name, initial in starts:
        folder = output/name; folder.mkdir(); started = time.monotonic(); history = []; best = None
        def quantities(raw):
            v = raw[:-5].reshape(-1, 3); theta = p.t(limits)[:, None]*v/torch.sqrt(1+torch.sum(v*v, dim=1))[:, None]
            parameters = p.t(seed).index_copy(0, torch.as_tensor(columns), theta.reshape(-1))
            _, _, _, vertices = p.fk(parameters); tri = vertices[faces]
            normal = torch.linalg.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0); normal = normal/torch.linalg.vector_norm(normal)
            if float((normal@target_n).detach()) < -.99: raise ValueError('Alignment near antiparallel singularity')
            positions, q, matrix = placement(raw[-5:], vertices[ids]-vertices[contact['vertex']], differentiable_alignment(normal, target_n), p.t(basis), p.t(contact['target']), point_limit, angle_limit)
            distances = torch.linalg.vector_norm(positions-center, dim=-1)-sphere.dimensions[0]
            tau = settings['smooth_min_temperature_m']; smooth = -tau*torch.logsumexp(-distances/tau, dim=0)
            loss = -smooth/.01+1e-8*torch.sum(((theta.reshape(-1)-p.t(seed[columns]))/p.t(np.repeat(limits, 3)))**2)+1e-12*torch.sum(raw[-5:]**2)
            return loss, distances, parameters, q, matrix
        def pair(raw):
            nonlocal best
            variable = p.t(raw).requires_grad_(); loss, distances, _, _, _ = quantities(variable)
            gradient = torch.autograd.grad(loss, variable)[0].detach().numpy(); minimum = float(distances.detach().min())
            if not np.isfinite(gradient).all(): raise ValueError('Nonfinite joint gradient')
            history.append(dict(minimum_clearance_m=minimum, loss=float(loss.detach())))
            if best is None or minimum > best[0]: best = minimum, raw.copy()
            if time.monotonic()-started > settings['seconds_per_trial']: raise TimeoutError('Joint patch time guard')
            return float(loss.detach()), gradient
        value, gradient = pair(initial); direction = np.random.default_rng(122).normal(size=len(initial)); direction /= np.linalg.norm(direction); h = 1e-6
        with torch.no_grad(): fd = float((quantities(p.t(initial+h*direction))[0]-quantities(p.t(initial-h*direction))[0])/(2*h))
        np.testing.assert_allclose(gradient@direction, fd, atol=2e-6, rtol=2e-4)
        status = 'complete'
        try:
            solved = minimize(pair, initial, jac=True, method='L-BFGS-B', options=dict(maxiter=settings['maximum_iterations'], maxfun=settings['maximum_evaluations'], ftol=1e-12, gtol=1e-9))
            solver = dict(success=bool(solved.success), message=str(solved.message), evaluations=int(solved.nfev))
        except TimeoutError as e:
            status = 'interrupted_resource_guard'; solver = dict(success=False, message=str(e))
        with torch.no_grad(): _, distances, physical, desired_point, matrix = quantities(p.t(best[1]))
        parameters = physical.numpy(); np.testing.assert_array_equal(parameters[frozen], seed[frozen]); audit, motion = p.independent(parameters)
        if not audit['rotation_norm_bounds_passed']: raise ValueError('Original finger bounds exceeded')
        vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0]); point, normal, tangent = hand_frame(vertices, motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
        raw = best[1][-5:]; delta = point_limit*raw[:3]/np.sqrt(1+raw[:3]@raw[:3]); tilt = angle_limit*raw[3:]/np.sqrt(1+raw[3:]@raw[3:])
        rotate = Rotation.from_rotvec(basis@tilt).as_matrix()@align_direction(normal, target_n.numpy()); q = np.array(contact['target'])+delta
        exact = np.linalg.norm((vertices[ids]-point)@rotate.T+q-center.numpy()[0], axis=1)-sphere.dimensions[0]
        error = float(np.max(np.abs(exact-distances.numpy())))
        if error > 2e-6: raise ValueError('Independent joint-patch mismatch')
        np.savez(folder/'unprojected-shape.npz', **motion)
        result = dict(at=now(), status=status, solver=solver, parameters=parameters.tolist(), raw=best[1].tolist(), candidate_unprojected=audit,
                      desired_point=q.tolist(), desired_normal=(rotate@normal).tolist(), desired_tangent=(rotate@tangent).tolist(),
                      point_error_m=float(np.linalg.norm(delta)), normal_error_degrees=angular_error(rotate@normal, target_n.numpy()),
                      minimum_clearance_m=float(exact.min()), rigid_patch_clearance_passed=bool(exact.min() >= p.config['object_clearance_m']-1e-6),
                      frozen_parameters_exact=True, independent_patch_max_error_m=error, seconds=time.monotonic()-started, history=history,
                      unprojected_pose_sha256=sha256(folder/'unprojected-shape.npz'), quality_approved=False)
        save(folder/'result.json', result); rows.append(dict(folder=folder.relative_to(ROOT).as_posix(), start=name, minimum_clearance_m=result['minimum_clearance_m'], rigid_patch_clearance_passed=result['rigid_patch_clearance_passed'], result_sha256=sha256(folder/'result.json')))
        print(rows[-1], flush=True)
    save(output/'summary.json', dict(at=now(), rows=rows, best_index=int(np.argmax([r['minimum_clearance_m'] for r in rows])), quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('shapes', type=Path); parser.add_argument('placements', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.shapes, args.placements, args.seed_report, args.output)
