"""Coordinate descent with fixed per-frame dynamics envelopes.

Envelopes are computed once from baseline/held motion, never ratcheted after
updates. Root and selected joint tracks are eliminated from the variables.
Final serialized full/half-frame checks remain necessary.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from foot_acceleration import foot_acceleration_pair, foot_acceleration_energy
from rig_periodic_contact import neighbor_constraints
from rig_transition import localize


def acceleration_envelope_pair(track, frame, candidate, jacobian, caps, fps):
    """Normalized squared-norm inequalities for all affected centers/feet."""
    # Reuse established validation and ensure this helper has the same clock.
    foot_acceleration_pair(track, frame, candidate, jacobian, caps, fps, 0.)
    values, rows = [], []
    for center in range(max(1, frame-1), min(len(track)-2, frame+1)+1):
        coefficient = -2. if center == frame else 1.
        acceleration = (track[center-1]-2*track[center]+track[center+1]
                        + coefficient*(candidate-track[frame]))*fps**2
        limit = caps[center-1]
        scale = np.maximum(limit**2, 1.)
        values.extend((limit**2-np.sum(acceleration**2, axis=1))/scale)
        rows.extend(-2*np.einsum('si,sip->sp', acceleration, jacobian)*coefficient*fps**2/scale[:, None])
    return np.asarray(values), np.asarray(rows)


def support_envelope_pair(track, frame, candidate, jacobian, active_steps, speed_caps, fps):
    values, rows = [], []
    for end in (frame, frame+1):
        if not 1 <= end < len(track):
            continue
        coefficient = 1. if end == frame else -1.
        velocity = (track[end]-track[end-1]+coefficient*(candidate-track[frame]))[:, [0, 2]]*fps
        for side in np.flatnonzero(active_steps[end-1]):
            cap = speed_caps[end-1, side]
            scale = max(cap**2, .01**2)
            values.append((cap**2-float(velocity[side]@velocity[side]))/scale)
            rows.append(-2*velocity[side]@jacobian[side, [0, 2]]*coefficient*fps/scale)
    return np.asarray(values), np.asarray(rows).reshape(-1, jacobian.shape[-1])


def relax(fitter, initial, objective_caps, active_frames, protected_nodes, sweeps=3,
          maxiter=80, progress=None, pose_evaluator=None):
    values = np.asarray(initial, float).copy()
    count, dimensions = values.shape
    fps = fitter.spec['fps']
    if count < 3 or dimensions != len(fitter.bounds) or not np.isfinite(values).all():
        raise ValueError('Finite complete parameter track required')
    if np.any(np.abs(values) > fitter.bounds+1e-8):
        raise ValueError('Initial absolute edit limit exceeded')
    protected = {0, 1, 2}
    for node in protected_nodes:
        start = 3+3*fitter.nodes.index(node)
        protected.update(range(start, start+3))
    free = np.array([i for i in range(dimensions) if i not in protected])
    if not len(free):
        raise ValueError('No editable coordinates')
    patches = [p['vertices'] for p in fitter.spec['patches'].values()]
    active_frames = np.asarray(active_frames, bool)
    if active_frames.shape != (count, len(patches)):
        raise ValueError('Support annotations must match frame/foot clock')
    original_world = np.array([fitter.pose(f, x)[0] for f, x in enumerate(values)])
    evaluated_world = original_world if pose_evaluator is None else np.array([pose_evaluator.pose(w) for w in original_world])
    surfaces = [fitter.rig.vertices(w) for w in evaluated_world]
    centers = np.array([[surface[ids].mean(axis=0) for ids in patches] for surface in surfaces])
    objective_caps = np.asarray(objective_caps, float)
    energy_before = foot_acceleration_energy(centers, objective_caps, fps, 1.)
    safety_caps = np.maximum(objective_caps, np.linalg.norm(np.diff(centers, n=2, axis=0)*fps**2, axis=2))
    active_steps = active_frames[:-1] & active_frames[1:]
    speed_caps = np.linalg.norm(np.diff(centers[:, :, [0, 2]], axis=0)*fps, axis=2)
    hover_caps = np.maximum(.01, [[surface[ids, 1].min() for ids in patches] for surface in surfaces])
    root_step = fitter.spec['limits']['root_step_m']
    joint_step = np.radians(fitter.spec['limits']['joint_step_degrees'])
    local = (np.array([fitter.pose(f, x)[1] for f, x in enumerate(values)]) if pose_evaluator is None
             else localize(evaluated_world, fitter.rig.parents))
    delta = local[:-1, :, :3, :3].transpose(0, 1, 3, 2)@local[1:, :, :3, :3]
    rotation_cap = float(Rotation.from_matrix(delta.reshape(-1, 3, 3)).magnitude().max())
    for frame in range(count):
        neighbors = [values[n] for n in (frame-1, frame+1) if 0 <= n < count]
        if neighbor_constraints(values[frame], neighbors, root_step, joint_step)[0].min() < -1e-7:
            raise ValueError('Initial adjacent edit limit exceeded')
        if surfaces[frame][:, 1].min() < -.005:
            raise ValueError('Held clip is outside integer floor constraint')
        if pose_evaluator is not None and frame+1 < count:
            half = pose_evaluator.half_pose(original_world[frame], original_world[frame+1], frame)
            if fitter.rig.vertices(half)[:, 1].min() < -.005:
                raise ValueError('Held clip is outside half-frame floor constraint')
    records, changes = [], []
    for sweep in range(sweeps):
        start_values = values.copy()
        for frame in (range(count) if sweep % 2 == 0 else range(count-1, -1, -1)):
            old = values[frame].copy()
            neighbors = [values[n].copy() for n in (frame-1, frame+1) if 0 <= n < count]
            cached_y, cached_pair = None, None

            def evaluate(y):
                nonlocal cached_y, cached_pair
                if cached_y is not None and np.array_equal(y, cached_y):
                    return cached_pair
                x = old.copy(); x[free] = y
                positions, derivative = fitter.surface_jacobian(frame, x)
                if pose_evaluator is not None:
                    # Values and acceptance use actual quantized poses. The
                    # smooth skin Jacobian is only a proposal approximation;
                    # it is not a derivative of the discontinuous quantizer.
                    positions = fitter.rig.vertices(pose_evaluator.pose(fitter.pose(frame, x)[0]))
                centroid = np.array([positions[ids].mean(axis=0) for ids in patches])
                jacobian = np.array([derivative[ids].mean(axis=0) for ids in patches])
                r, j = foot_acceleration_pair(centers, frame, centroid, jacobian, objective_caps, fps, 1.)
                a, aj = acceleration_envelope_pair(centers, frame, centroid, jacobian, safety_caps, fps)
                s, sj = support_envelope_pair(centers, frame, centroid, jacobian, active_steps, speed_caps, fps)
                bounds, bj = neighbor_constraints(x, neighbors, root_step, joint_step)
                floor, fj = (positions[:, 1]+.005)/.005, derivative[:, 1]/.005
                hover, hj = [], []
                for side, ids in enumerate(patches):
                    if active_frames[frame, side]:
                        vertex = ids[int(np.argmin(positions[ids, 1]))]
                        hover.append((hover_caps[frame, side]-positions[vertex, 1])/.01)
                        hj.append(-derivative[vertex, 1]/.01)
                constraints = np.r_[a, s, bounds, floor, hover]
                constraint_jac = np.vstack([aj, sj, bj, fj, np.asarray(hj).reshape(-1, dimensions)])[:, free]
                # Fixed tiny proximal tie-breaker; acceptance also requires the
                # actual acceleration energy itself not to increase.
                shift = y-old[free]
                objective = float(r@r+1e-6*(shift@shift))
                gradient = 2*j[:, free].T@r+2e-6*shift
                cached_y = y.copy()
                cached_pair = (objective, gradient, constraints, constraint_jac, centroid, float(r@r), x)
                return cached_pair

            original = evaluate(old[free])
            if original[2].min() < -1e-7:
                raise ValueError('Current iterate lost a frozen envelope')
            fit = minimize(lambda y: evaluate(y)[0], old[free], jac=lambda y: evaluate(y)[1],
                method='SLSQP', bounds=list(zip(-fitter.bounds[free], fitter.bounds[free])),
                constraints=dict(type='ineq', fun=lambda y: evaluate(y)[2], jac=lambda y: evaluate(y)[3]),
                options=dict(maxiter=maxiter, ftol=1e-9))
            accepted = False
            for backtrack in range(8):
                y = old[free]+(fit.x-old[free])*(.5**backtrack)
                trial = evaluate(y)
                if not np.isfinite(trial[0]) or trial[2].min() < -1e-8 or trial[5] > original[5]+1e-12:
                    continue
                candidate_world, candidate_local = fitter.pose(frame, trial[6])
                if pose_evaluator is not None:
                    candidate_local = localize(pose_evaluator.pose(candidate_world)[None], fitter.rig.parents)[0]
                    half_ok = True
                    for n in (frame-1, frame+1):
                        if not 0 <= n < count:
                            continue
                        a, b = (original_world[n], candidate_world) if n < frame else (candidate_world, original_world[n])
                        half = pose_evaluator.half_pose(a, b, min(n, frame))
                        if fitter.rig.vertices(half)[:, 1].min() < -.005:
                            half_ok = False
                            break
                    if not half_ok:
                        continue
                steps = [candidate_local[:, :3, :3].transpose(0, 2, 1)@local[n, :, :3, :3]
                         for n in (frame-1, frame+1) if 0 <= n < count]
                peak = Rotation.from_matrix(np.concatenate(steps)).magnitude().max()
                if peak > rotation_cap+1e-10:
                    continue
                values[frame] = trial[6]
                centers[frame] = trial[4]
                local[frame] = candidate_local
                original_world[frame] = candidate_world
                accepted = True
                break
            records.append(dict(sweep=sweep, frame=frame, success=bool(fit.success), status=int(fit.status),
                iterations=int(fit.nit), accepted=accepted, energy_before=original[5],
                energy_after=trial[5] if accepted else original[5]))
        changes.append(float(np.abs(values-start_values).max()))
        if progress:
            progress(sweep+1, changes[-1], foot_acceleration_energy(centers, objective_caps, fps, 1.))
    np.testing.assert_array_equal(values[:, sorted(protected)], initial[:, sorted(protected)])
    return values, records, dict(sweeps=sweeps, maxiter=maxiter, changes=changes,
        energy_before=energy_before, energy_after=foot_acceleration_energy(centers, objective_caps, fps, 1.),
        safety_caps_m_s2=safety_caps.tolist(), support_speed_caps_m_s=speed_caps.tolist(),
        support_steps=active_steps.tolist(), hover_caps_m=hover_caps.tolist(),
        protected_columns=sorted(protected), rotation_cap_radians=rotation_cap,
        serialized_pose_evaluation=pose_evaluator is not None,
        derivative_mode='Smooth unquantized proposal approximation; quantized values and acceptance' if pose_evaluator is not None else 'Exact smooth skin Jacobian',
        stationary_proven=False, quality_approved=False)
