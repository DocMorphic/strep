"""Object-local targets and bounded arm projection for a declared grasp interval."""
import numpy as np
import torch
from scipy.optimize import least_squares
from grasp_pose_witness_bounded import inverse_rotation_bound
from support_contact_v8 import bounded_rotation


def smoothstep5(value):
    t = np.clip(np.asarray(value, dtype=float), 0., 1.)
    return t*t*t*(10.+t*(-15.+6.*t))


def object_local_targets(point, normal, tangent, positions, rotations, reference_frame):
    positions, rotations = np.asarray(positions), np.asarray(rotations)
    origin, reference = positions[reference_frame], rotations[reference_frame]
    local_point = reference.T@(np.asarray(point)-origin)
    local_normal, local_tangent = reference.T@normal, reference.T@tangent
    return dict(points=(rotations@local_point[..., None]).squeeze(-1)+positions,
                normals=(rotations@local_normal[..., None]).squeeze(-1), tangents=(rotations@local_tangent[..., None]).squeeze(-1))


def arm_columns(problem):
    joints = [side+name for side in ['Left', 'Right'] for name in ['Shoulder', 'Arm', 'ForeArm', 'Hand']]
    slots = np.array([problem.lookup[problem.names.index(name)] for name in joints])
    return np.array([3*s+k for s in slots for k in range(3)]), problem.limits[slots]


def project(problem, fixed, initial_angles, targets, settings, guard=None, check_derivative=False):
    columns, limits = arm_columns(problem); initial = inverse_rotation_bound(initial_angles.reshape(-1, 3), limits).ravel()
    geometry_specs = []
    for hand, target in targets.items():
        contact = next(c for c in problem.contacts if c['region'] == hand)
        faces = next(f for name, f, _ in problem.normals if name == ('left-grip' if hand == 'LeftHand' else 'right-grip'))
        geometry_specs.append((contact['vertex'], faces, problem.names.index(hand),
                               [problem.names.index(hand+f+'2') for f in ['Index', 'Middle', 'Ring', 'Pinky']], target))
    def physical(raw):
        theta = bounded_rotation(raw.reshape(-1, 3)/problem.t(limits)[:, None], problem.t(limits)[:, None]).reshape(-1)
        return problem.t(fixed).index_copy(0, torch.as_tensor(columns), theta)
    def geometry(raw):
        _, joints, _, vertices = problem.fk(physical(raw)); values = []
        for anchor, faces, wrist, knuckles, target in geometry_specs:
            tri = vertices[faces]; normal = torch.linalg.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0)
            normal = normal/torch.linalg.vector_norm(normal)
            direction = joints[knuckles].mean(0)-joints[wrist]; tangent = direction-normal*(normal@direction)
            tangent = tangent/torch.linalg.vector_norm(tangent)
            values.extend([(vertices[anchor]-problem.t(target['point']))/settings['point_scale_m'],
                           (normal-problem.t(target['normal']))/settings['direction_scale'],
                           (tangent-problem.t(target['tangent']))/settings['direction_scale']])
        return torch.cat(values)
    cache = None; evaluations = 0; last = initial.copy()
    def pair(raw):
        nonlocal cache, evaluations, last
        if cache is not None and np.array_equal(raw, cache[0]): return cache[1:]
        variable = problem.t(raw).requires_grad_(); values = geometry(variable)
        jac = np.array([torch.autograd.grad(v, variable, retain_graph=True)[0].detach().numpy() for v in values])
        residual = np.r_[values.detach().numpy(), settings['regularization']*(raw-initial)]
        jac = np.r_[jac, settings['regularization']*np.eye(len(raw))]; evaluations += 1; last = raw.copy()
        if guard: guard(evaluations)
        cache = raw.copy(), residual, jac
        return residual, jac
    derivative_error = None
    if check_derivative:
        _, jac = pair(initial); d = np.random.default_rng(723).normal(size=len(initial)); d /= np.linalg.norm(d); h = 1e-6
        with torch.no_grad(): fd = ((geometry(problem.t(initial+h*d))-geometry(problem.t(initial-h*d)))/(2*h)).numpy()
        derivative_error = float(np.max(np.abs(jac[:len(fd)]@d-fd)))
        np.testing.assert_allclose(jac[:len(fd)]@d, fd, atol=2e-5, rtol=2e-4)
    status = 'complete'
    try:
        solve = least_squares(lambda x: pair(x)[0], initial, jac=lambda x: pair(x)[1], max_nfev=settings['maximum_evaluations'], ftol=1e-10, xtol=1e-10, gtol=1e-10)
        last = solve.x; solver = dict(success=bool(solve.success), message=str(solve.message), evaluations=int(solve.nfev))
    except TimeoutError as exc:
        status = 'interrupted_resource_guard'; solver = dict(success=False, message=str(exc))
    parameters = physical(problem.t(last)).detach().numpy()
    return parameters, dict(status=status, solver=solver, raw_parameters=last.tolist(), evaluations=evaluations, derivative_error=derivative_error)
