"""Place frozen searched hand shapes inside the original point/normal tolerances."""
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
from grasp_orientation import align_direction, hand_frame, unit, angular_error
from support_contact_v8 import rodrigues


def bounded_vector(raw, limit):
    return limit*raw/torch.sqrt(1+raw@raw)


def placement(raw, offsets, align, basis, target, point_limit, angle_limit):
    displacement = bounded_vector(raw[:3], point_limit)
    tilt = bounded_vector(raw[3:], angle_limit)
    rotate = rodrigues((basis@tilt)[None])[0]@align
    return offsets@rotate.T+target+displacement, target+displacement, rotate


def run(shapes, output):
    torch.set_num_threads(2); shapes, output = Path(shapes).resolve(), Path(output).resolve()
    protocol, summary = read(shapes/'protocol.json'), read(shapes/'summary.json')
    fit = ROOT/protocol['study']/'fit'; fit_summary = read(fit/'summary.json')
    if sha256(fit/'summary.json') != protocol['fit_summary_sha256'] or sha256(ASSET) != fit_summary['mesh_sha256']: raise ValueError('Study or asset changed')
    for n, digest in protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Input changed')
    p = PoseProblem(fit/'assets'/fit_summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    contact = next(c for c in p.contacts if c['region'] == 'LeftHand'); _, faces, target_n = next(n for n in p.normals if n[0] == 'left-grip')
    geometry, _, center, _ = p.objects[0]; radial = np.array(contact['target'])-center.numpy()[0]
    if geometry.shape != 'sphere' or abs(unit(radial)@target_n.numpy()+1) > 1e-10: raise ValueError('Inward radial sphere required')
    wrist = p.names.index('LeftHand'); knuckles = [p.names.index('LeftHand'+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']]
    ids = np.array(protocol['patch_vertices']); t1 = unit(np.cross(target_n.numpy(), np.eye(3)[np.argmin(np.abs(target_n.numpy()))])); basis = np.c_[t1, np.cross(target_n.numpy(), t1)]
    point_limit = p.config['point_tolerance_m']-1e-6; angle_limit = np.deg2rad(p.config['normal_tolerance_degrees']-.001)
    settings = dict(starts=['centered', 'measured_clamped_to_90_percent'], point_limit_m=point_limit, angle_limit_radians=angle_limit,
                    maximum_iterations=200, maximum_evaluations=260, seconds_per_trial=30, smooth_min_temperature_m=.00002)
    output.mkdir(parents=True, exist_ok=False)
    save(output/'protocol.json', dict(at=now(), shapes_summary_sha256=sha256(shapes/'summary.json'), shapes_protocol_sha256=sha256(shapes/'protocol.json'), settings=settings,
         implementation_sha256=sha256(Path(__file__)), scope='Actual sphere clearance of each fixed measured rigid hand patch, jointly across all patch vertices. Bounded point displacement and normal tilt, with axial twist removed by radial sphere symmetry. Does not yet establish skeleton reachability, other-body clearance, anatomy or a full pose.', quality_approved=False))
    rows = []
    for shape in summary['rows']:
        folder = ROOT/shape['folder']; record = read(folder/'result.json')
        if sha256(folder/'result.json') != shape['result_sha256'] or sha256(folder/'pose.npz') != record['pose_sha256']: raise ValueError('Shape changed')
        _, motion = p.independent(np.array(record['parameters'])); vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
        point, normal, tangent = hand_frame(vertices, motion['posed_joints'][0], faces, contact['vertex'], wrist, knuckles)
        align = align_direction(normal, target_n.numpy()); offsets = vertices[ids]-point
        displacement = point-np.array(contact['target']); displacement *= min(1., .9*point_limit/max(np.linalg.norm(displacement), 1e-15))
        angle = basis.T@Rotation.from_matrix(align.T).as_rotvec(); angle *= min(1., .9*angle_limit/max(np.linalg.norm(angle), 1e-15))
        def inverse(value, limit):
            scaled = value/limit
            return scaled/np.sqrt(1-scaled@scaled)
        initial_values = [np.zeros(5), np.r_[inverse(displacement, point_limit), inverse(angle, angle_limit)]]
        for label, initial in zip(settings['starts'], initial_values):
            start = time.monotonic(); best = None; history = []
            def pair(raw):
                nonlocal best
                variable = p.t(raw).requires_grad_(); positions, _, _ = placement(variable, p.t(offsets), p.t(align), p.t(basis), p.t(contact['target']), point_limit, angle_limit)
                distances = torch.linalg.vector_norm(positions-center, dim=-1)-geometry.dimensions[0]
                tau = settings['smooth_min_temperature_m']; smooth = -tau*torch.logsumexp(-distances/tau, dim=0)
                loss = -smooth/.01+1e-10*torch.sum(variable**2); gradient = torch.autograd.grad(loss, variable)[0].detach().numpy()
                minimum = float(distances.detach().min()); history.append(dict(minimum_clearance_m=minimum, smooth_clearance_m=float(smooth.detach())))
                if best is None or minimum > best[0]: best = minimum, raw.copy()
                if time.monotonic()-start > settings['seconds_per_trial']: raise TimeoutError('Rigid placement time guard')
                return float(loss.detach()), gradient
            value, gradient = pair(initial); direction = np.random.default_rng(121).normal(size=5); direction /= np.linalg.norm(direction); h = 1e-6
            plus = pair(initial+h*direction)[0]; minus = pair(initial-h*direction)[0]
            np.testing.assert_allclose(gradient@direction, (plus-minus)/(2*h), atol=2e-6, rtol=2e-4)
            status = 'complete'
            try:
                solved = minimize(pair, initial, jac=True, method='L-BFGS-B', options=dict(maxiter=settings['maximum_iterations'], maxfun=settings['maximum_evaluations'], ftol=1e-12, gtol=1e-9))
                solver = dict(success=bool(solved.success), message=str(solved.message), evaluations=int(solved.nfev))
            except TimeoutError as e:
                status = 'interrupted_resource_guard'; solver = dict(success=False, message=str(e))
            raw = best[1]; delta = point_limit*raw[:3]/np.sqrt(1+raw[:3]@raw[:3]); tilt = angle_limit*raw[3:]/np.sqrt(1+raw[3:]@raw[3:])
            matrix = Rotation.from_rotvec(basis@tilt).as_matrix()@align; q = np.array(contact['target'])+delta
            transformed = offsets@matrix.T+q; exact = np.linalg.norm(transformed-center.numpy()[0], axis=1)-geometry.dimensions[0]
            with torch.no_grad(): actual, _, _ = placement(p.t(raw), p.t(offsets), p.t(align), p.t(basis), p.t(contact['target']), point_limit, angle_limit)
            np.testing.assert_allclose(actual.numpy(), transformed, atol=1e-12, rtol=0)
            normal_error = angular_error(matrix@normal, target_n.numpy())
            if np.linalg.norm(delta) > point_limit+1e-12 or normal_error > np.rad2deg(angle_limit)+1e-8: raise ValueError('Placement outside original contact limits')
            row = dict(shape=shape['folder'], start=label, status=status, solver=solver, seconds=time.monotonic()-start,
                       raw=raw.tolist(), desired_point=q.tolist(), desired_normal=(matrix@normal).tolist(), desired_tangent=(matrix@tangent).tolist(),
                       rotation_from_shape=matrix.tolist(), minimum_clearance_m=float(exact.min()), rigid_patch_clearance_passed=bool(exact.min() >= p.config['object_clearance_m']-1e-6),
                       contact_error_m=float(np.linalg.norm(delta)), normal_error_degrees=normal_error, worst_vertex=int(ids[exact.argmin()]), history=history, quality_approved=False)
            rows.append(row); print({k: row[k] for k in ['shape', 'start', 'minimum_clearance_m', 'rigid_patch_clearance_passed']}, flush=True)
    save(output/'result.json', dict(at=now(), rows=rows, best_index=int(np.argmax([r['minimum_clearance_m'] for r in rows])), quality_approved=False, skeleton_pose_generated=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('shapes', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.shapes, args.output)
