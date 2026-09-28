"""One coupled temporal block with frozen serialized-pose safeguards."""
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from rig_transition import localize


def temporal_pair(points, jacobian, order, fps):
    if order not in (1, 2) or points.ndim != 3 or jacobian.shape[:3] != points.shape:
        raise ValueError('Matching frame/foot/XYZ points and Jacobian required')
    return np.diff(points, n=order, axis=0)*fps**order, np.diff(jacobian, n=order, axis=0)*fps**order


def norm_envelope_pair(vectors, derivative, caps, scale_floor):
    scale = np.maximum(np.asarray(caps)**2, scale_floor**2)
    values = (np.asarray(caps)**2-np.sum(vectors**2, axis=-1))/scale
    rows = -2*np.einsum('...i,...ip->...p', vectors, derivative)/scale[..., None]
    return values.ravel(), rows.reshape(-1, derivative.shape[-1])


def adjacent_pair(values, frames, free, root_step, joint_step):
    lookup = {int(frame): i for i, frame in enumerate(frames)}
    width = len(frames)*len(free); rows, residual = [], []
    edges = sorted({end for frame in frames for end in (frame, frame+1) if 1 <= end < len(values)})
    for end in edges:
        for start, radius in [(0, root_step)]+[(i, joint_step) for i in range(3, values.shape[1], 3)]:
            delta = values[end, start:start+3]-values[end-1, start:start+3]
            row = np.zeros(width)
            gradient = np.zeros(values.shape[1]); gradient[start:start+3] = -2*delta/radius**2
            for frame, sign in [(end, 1), (end-1, -1)]:
                if frame in lookup:
                    offset = lookup[frame]*len(free)
                    row[offset:offset+len(free)] += sign*gradient[free]
            residual.append(1-float(delta@delta)/radius**2); rows.append(row)
    return np.asarray(residual), np.asarray(rows)


class BlockProblem:
    def __init__(self, fitter, initial, evaluator, frames, free, envelope, acceleration_caps, target):
        self.fitter, self.initial, self.evaluator = fitter, initial.copy(), evaluator
        self.frames, self.free = np.asarray(frames, int), np.asarray(free, int)
        if len(set(self.frames)) != len(self.frames) or np.any(np.diff(self.frames) != 1):
            raise ValueError('One ordered contiguous frame block required')
        if self.frames[0] < 0 or self.frames[-1] >= len(initial): raise ValueError('Block outside clip')
        self.width = len(frames)*len(free); self.fps = fitter.spec['fps']
        self.patches = [p['vertices'] for p in fitter.spec['patches'].values()]
        self.world = np.array([fitter.pose(f, x)[0] for f, x in enumerate(initial)])
        self.centers = np.array([[fitter.rig.vertices(evaluator.pose(w))[ids].mean(axis=0) for ids in self.patches] for w in self.world])
        self.envelope, self.acceleration_caps, self.target = envelope, np.asarray(acceleration_caps), target
        self.acceleration_indices = np.array(sorted({c-1 for f in frames for c in (f-1, f, f+1) if 1 <= c < len(initial)-1}))
        self.speed_indices = np.array(sorted({end-1 for f in frames for end in (f, f+1) if 1 <= end < len(initial)}))
        self.cached_x = None

    def values(self, x):
        values = self.initial.copy(); values[np.ix_(self.frames, self.free)] = np.asarray(x).reshape(len(self.frames), len(self.free))
        return values

    def evaluate(self, x, quantized=True):
        if quantized and self.cached_x is not None and np.array_equal(x, self.cached_x): return self.cached
        fitter = self.fitter; values = self.values(x)
        points = self.centers.copy(); jac = np.zeros((*points.shape, self.width))
        constraints, constraint_jac = [], []
        for index, frame in enumerate(self.frames):
            positions, derivative = fitter.surface_jacobian(int(frame), values[frame])
            if quantized: positions = fitter.rig.vertices(self.evaluator.pose(fitter.pose(int(frame), values[frame])[0]))
            sl = slice(index*len(self.free), (index+1)*len(self.free))
            points[frame] = [positions[ids].mean(axis=0) for ids in self.patches]
            jac[frame, :, :, sl] = np.array([derivative[ids].mean(axis=0)[:, self.free] for ids in self.patches])
            floor = (positions[:, 1]+.005)/.005
            fj = np.zeros((len(positions), self.width)); fj[:, sl] = derivative[:, 1, self.free]/.005
            constraints.extend(floor); constraint_jac.extend(fj)
            for side, ids in enumerate(self.patches):
                if self.envelope['active_frames'][frame][side]:
                    vertex = ids[int(np.argmin(positions[ids, 1]))]
                    constraints.append((self.envelope['hover_caps_m'][frame][side]-positions[vertex, 1])/.01)
                    row = np.zeros(self.width); row[sl] = -derivative[vertex, 1, self.free]/.01; constraint_jac.append(row)
        acceleration, aj = temporal_pair(points, jac, 2, self.fps)
        indices = self.acceleration_indices
        a, ad = norm_envelope_pair(acceleration[indices], aj[indices], self.acceleration_caps[indices], 1.)
        constraints.extend(a); constraint_jac.extend(ad)
        velocity, vj = temporal_pair(points, jac, 1, self.fps)
        indices = self.speed_indices; mask = np.asarray(self.envelope['support_steps'], bool)[indices]
        v, vd = norm_envelope_pair(velocity[indices][:, :, [0, 2]][mask], vj[indices][:, :, [0, 2]][mask],
            np.asarray(self.envelope['support_speed_caps_m_s'])[indices][mask], .01)
        constraints.extend(v); constraint_jac.extend(vd)
        b, bd = adjacent_pair(values, self.frames, self.free, fitter.spec['limits']['root_step_m'], np.radians(fitter.spec['limits']['joint_step_degrees']))
        constraints.extend(b); constraint_jac.extend(bd)
        indices = np.asarray(self.target['centers'])-1; side = self.target['side_index']; cap = self.target['limit_m_s2']
        vectors, derivative = acceleration[indices, side], aj[indices, side]
        norm = np.linalg.norm(vectors, axis=1); excess = np.maximum(norm-cap, 0)
        directions = vectors/np.maximum(norm[:, None], 1e-30)
        objective = float(excess@excess)
        gradient = 2*np.einsum('s,si,sip->p', excess, directions, derivative)
        result = (objective, gradient, np.asarray(constraints), np.asarray(constraint_jac), points, values)
        if quantized: self.cached_x, self.cached = np.asarray(x).copy(), result
        return result

    def geometric_guard(self, values):
        world = self.world.copy()
        for f in self.frames: world[f] = self.fitter.pose(int(f), values[f])[0]
        edges = sorted({end for f in self.frames for end in (f, f+1) if 1 <= end < len(values)})
        for end in edges:
            half = self.evaluator.half_pose(world[end-1], world[end], int(end-1))
            if self.fitter.rig.vertices(half)[:, 1].min() < -.005: return False
            local = localize(np.array([self.evaluator.pose(world[end-1]), self.evaluator.pose(world[end])]), self.fitter.rig.parents)
            delta = local[0, :, :3, :3].transpose(0, 2, 1)@local[1, :, :3, :3]
            if Rotation.from_matrix(delta).magnitude().max() > self.envelope['rotation_cap_radians']+1e-10: return False
        return True


def solve(problem, maxiter=80, progress=None):
    x = problem.initial[np.ix_(problem.frames, problem.free)].ravel(); before = problem.evaluate(x)
    if before[2].min() < -1e-7 or not problem.geometric_guard(problem.initial):
        raise ValueError('Block initialization violates frozen safeguards')
    visits = []
    def callback(y):
        r = problem.evaluate(y); visits.append(dict(iteration=len(visits)+1, objective=r[0], minimum_constraint=float(r[2].min())))
        if progress and len(visits)%10 == 0: progress(visits[-1])
    bounds = np.tile(problem.fitter.bounds[problem.free], len(problem.frames))
    fit = minimize(lambda y: problem.evaluate(y)[0], x, jac=lambda y: problem.evaluate(y)[1], method='SLSQP',
        bounds=list(zip(-bounds, bounds)), constraints=dict(type='ineq', fun=lambda y: problem.evaluate(y)[2], jac=lambda y: problem.evaluate(y)[3]),
        callback=callback, options=dict(maxiter=maxiter, ftol=1e-9))
    retained = problem.initial.copy(); accepted = None; trials = []
    for index in range(8):
        alpha = .5**index; trial = problem.evaluate(x+alpha*(fit.x-x))
        finite = np.isfinite(trial[0]) and np.isfinite(trial[2]).all()
        feasible = bool(finite and trial[2].min() >= -1e-8)
        geometry = problem.geometric_guard(trial[5]) if feasible else False
        improved = bool(trial[0] < before[0]-1e-9)
        trials.append(dict(alpha=alpha, objective=trial[0], minimum_constraint=float(trial[2].min()), geometric_guard=geometry, feasible=feasible, improved=improved))
        if feasible and geometry and improved:
            retained = trial[5]; accepted = alpha; break
    return retained, dict(success=bool(fit.success), status=int(fit.status), message=str(fit.message), iterations=int(fit.nit),
        variable_frames=problem.frames.tolist(), free_columns=problem.free.tolist(), proposed_coordinates=fit.x.tolist(),
        objective_before=before[0], objective_after=problem.evaluate(retained[np.ix_(problem.frames, problem.free)].ravel())[0],
        accepted_fraction=accepted, iterations_log=visits, safeguard_trials=trials, quality_approved=False)
