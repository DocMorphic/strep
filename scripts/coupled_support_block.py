"""Sparse coupled root/leg proposals measured in delivered motion space."""
import numpy as np
from scipy import sparse
from scipy.spatial.transform import Rotation
from angular_release_block import skew, chord_cap
from conic_root_descent import solver_module
from rig_clearance_fit import right_jacobian
from rig_transition import localize


class Constraints:
    def __init__(self, width):
        self.width = width
        self.linear = []
        self.norms = []

    def lower(self, value, jacobian, kind):
        self.linear.append((np.atleast_1d(value), sparse.csc_matrix(jacobian), kind))

    def norm(self, vector, jacobian, cap, kind):
        self.norms.append((np.asarray(vector), sparse.csc_matrix(jacobian), float(cap), kind))

    def margins(self):
        result = {}
        for value, _, kind in self.linear:
            result[kind] = min(result.get(kind, float('inf')), float(np.min(value)))
        for vector, _, cap, kind in self.norms:
            result[kind] = min(result.get(kind, float('inf')), cap-float(np.linalg.norm(vector)))
        return result


def embed(matrix, offset, width):
    matrix = sparse.coo_matrix(matrix)
    return sparse.csc_matrix((matrix.data, (matrix.row, matrix.col+offset)), shape=(matrix.shape[0], width))


class CoupledBlock:
    """Frame-local skin rows stay sparse; temporal rows span neighboring poses.

    Fitter coordinates remain relative to the original raw motion so the original
    joint/root budgets cannot silently reset after an earlier correction.
    """
    def __init__(self, fitter, oracle, initial, source_world, source_points,
                 frames, envelope, target_caps):
        self.fitter, self.oracle = fitter, oracle
        self.initial = np.asarray(initial).copy()
        self.source_world, self.source_points = source_world, source_points
        self.frames = np.asarray(frames, int)
        if len(self.frames) < 2 or np.any(np.diff(self.frames) != 1) or self.frames[0] < 2 or self.frames[-1] >= len(initial)-2:
            raise ValueError('Contiguous internal block must preserve the first/last two frames')
        self.columns = len(initial[0]); self.width = len(frames)*self.columns
        self.lookup = {int(f): i for i, f in enumerate(frames)}
        self.patches = [p['vertices'] for p in fitter.spec['patches'].values()]
        self.hover_vertices = np.array([[ids[int(np.argmin(points[ids, 1]))]
            for ids in self.patches] for points in source_points])
        self.envelope, self.target_caps = envelope, np.asarray(target_caps)
        self.root = fitter.spec['root_node']
        self.count = len(initial)
        self.affected_edges = sorted({f for k in frames for f in (k-1, k) if 0 <= f < self.count-1})
        self.affected_acc = sorted({f for k in frames for f in (k-2, k-1, k) if 0 <= f < self.count-2})
        self.world = np.array([fitter.pose(f, v)[0] for f, v in enumerate(initial)])
        self.serialized = np.array([oracle.pose(w) for w in self.world])
        self.points = np.array([fitter.rig.vertices(w) for w in self.serialized])
        self.centers = np.array([[p[ids].mean(axis=0) for ids in self.patches] for p in self.points])
        self.rotations = localize(self.serialized, fitter.rig.parents)[:, fitter.nodes, :3, :3]
        self.zero3 = sparse.csc_matrix((3, self.width))
        self.zero9 = sparse.csc_matrix((9, self.width))

    def values(self, x):
        result = self.initial.copy()
        result[self.frames] = np.asarray(x).reshape(len(self.frames), self.columns)
        return result

    def pair(self, x, quantized=True):
        values = self.values(x); c = Constraints(self.width)
        centers, roots, rotations = self.centers.copy(), self.serialized[:, self.root, :3, 3].copy(), self.rotations.copy()
        cj, rj, qj = {}, {}, {}
        limits = self.fitter.spec['limits']; eps = self.envelope['position_epsilon_m']
        for f in self.frames:
            offset = self.lookup[int(f)]*self.columns
            points, derivative = self.fitter.surface_jacobian(int(f), values[f])
            world, local = self.fitter.pose(int(f), values[f])
            if quantized:
                world = self.oracle.pose(world); points = self.fitter.rig.vertices(world)
                local = localize(world[None], self.fitter.rig.parents)[0]
            centers[f] = [points[ids].mean(axis=0) for ids in self.patches]
            roots[f] = world[self.root, :3, 3]
            rotations[f] = local[self.fitter.nodes, :3, :3]
            # Preserve each vertex's achieved floor depth, rather than merely a
            # clip-wide maximum that could hide new penetration elsewhere.
            lower = np.minimum(self.source_points[f, :, 1], 0.)-eps
            c.lower(points[:, 1]-lower, embed(derivative[:, 1], offset, self.width), 'floor')
            for side, ids in enumerate(self.patches):
                cj[f, side] = embed(derivative[ids].mean(axis=0), offset, self.width)
                if self.envelope['active'][f, side]:
                    # A fixed source vertex witnesses the retained minimum.
                    # This avoids differentiating a changing argmin on flat soles.
                    vertex = self.hover_vertices[f, side]
                    cap = self.source_points[f, ids, 1].min()+eps
                    c.lower(cap-points[vertex, 1], -embed(derivative[vertex, 1][None], offset, self.width), 'hover')
                if self.envelope['used'][f, side]:
                    vector = centers[f, side, [0, 2]]-self.envelope['anchors'][f, side]
                    c.norm(vector, cj[f, side][[0, 2]], self.envelope['anchor_caps'][f, side]+eps, 'anchor')
            root_derivative = np.zeros((3, self.columns)); root_derivative[:, :3] = np.eye(3)
            rj[f] = embed(root_derivative, offset, self.width)
            c.norm(values[f, [0, 2]], rj[f][[0, 2]], limits['root_horizontal_m']+eps, 'root_horizontal')
            c.lower(limits['root_vertical_m']+eps-values[f, 1], -rj[f][1], 'root_vertical')
            c.lower(limits['root_vertical_m']+eps+values[f, 1], rj[f][1], 'root_vertical')
            for j, node in enumerate(self.fitter.nodes):
                vector = values[f, 3+3*j:6+3*j]
                smooth = self.fitter.local[f, node, :3, :3]@Rotation.from_rotvec(vector).as_matrix()
                jac = np.zeros((9, self.columns))
                for axis in range(3):
                    jac[:, 3+3*j+axis] = (smooth@skew(right_jacobian(vector)[:, axis])).ravel()/np.sqrt(2)
                qj[f, j] = embed(jac, offset, self.width)
                identity = np.zeros((3, self.columns)); identity[:, 3+3*j:6+3*j] = np.eye(3)
                c.norm(vector, embed(identity, offset, self.width), self.fitter.angles[j], 'joint_budget')
        objective, gradient = 0., np.zeros(self.width)
        for edge in self.affected_edges:
            for column in range(0, self.columns, 3):
                matrix = sparse.csc_matrix((3, self.width))
                identity = np.zeros((3, self.columns)); identity[:, column:column+3] = np.eye(3)
                for f, sign in ((edge+1, 1), (edge, -1)):
                    if f in self.lookup: matrix += sign*embed(identity, self.lookup[f]*self.columns, self.width)
                cap = self.envelope['edit_step_caps'][edge, column//3]
                c.norm(values[edge+1, column:column+3]-values[edge, column:column+3], matrix, cap, 'edit_step')
            for j in range(len(self.fitter.nodes)):
                vector = (rotations[edge+1, j]-rotations[edge, j]).ravel()/np.sqrt(2)
                matrix = qj.get((edge+1, j), self.zero9)-qj.get((edge, j), self.zero9)
                c.norm(vector, matrix, self.envelope['rotation_chord_caps'][edge, j], 'rotation_step')
            for side in range(len(self.patches)):
                vector = (centers[edge+1, side]-centers[edge, side])[[0, 2]]*30
                matrix = (cj.get((edge+1, side), self.zero3)-cj.get((edge, side), self.zero3))[[0, 2]]*30
                if self.envelope['guarded'][edge, side]:
                    c.norm(vector, matrix, self.envelope['speed_caps'][edge, side]+self.envelope['speed_epsilon_m_s'], 'support_speed')
                if self.envelope['support_steps'][edge, side]:
                    length = np.linalg.norm(vector); excess = max(0., length-self.target_caps[side])
                    objective += excess**2
                    gradient += np.asarray(matrix.T@vector).ravel()*(2*excess/max(length, 1e-30))
        for index in self.affected_acc:
            for side in range(len(self.patches)):
                vector = (centers[index+2, side]-2*centers[index+1, side]+centers[index, side])*900
                matrix = (cj.get((index+2, side), self.zero3)-2*cj.get((index+1, side), self.zero3)+cj.get((index, side), self.zero3))*900
                c.norm(vector, matrix, self.envelope['foot_acc_caps'][index, side]+self.envelope['acc_epsilon_m_s2'], 'foot_acceleration')
            vector = (roots[index+2]-2*roots[index+1]+roots[index])*900
            matrix = (rj.get(index+2, self.zero3)-2*rj.get(index+1, self.zero3)+rj.get(index, self.zero3))*900
            c.norm(vector, matrix, self.envelope['root_acc_caps'][index]+self.envelope['acc_epsilon_m_s2'], 'root_acceleration')
        return float(objective), gradient, c, values

    def midpoint_guard(self, values):
        world = self.world.copy()
        for f in self.frames: world[f] = self.fitter.pose(int(f), values[f])[0]
        worst = 0.
        for edge in self.affected_edges:
            points = self.fitter.rig.vertices(self.oracle.half_pose(world[edge], world[edge+1], int(edge)))
            excess = np.maximum(-points[:, 1], 0)-self.envelope['half_depths'][edge]
            worst = max(worst, float(excess.max()))
        return worst <= self.envelope['position_epsilon_m'], worst


def direction(problem, x, trust):
    objective, gradient, constraints, _ = problem.pair(x)
    clarabel = solver_module(); matrices, rhs, cones = [], [], []
    for value, jac, _ in constraints.linear:
        matrices.append(-jac*trust); rhs.append(value); cones.append(clarabel.NonnegativeConeT(len(value)))
    for vector, jac, cap, _ in constraints.norms:
        scale = max(cap, 1e-4)
        matrices.append(sparse.vstack([sparse.csc_matrix((1, problem.width)), -jac*trust], format='csc')/scale)
        rhs.append(np.r_[cap, vector]/scale); cones.append(clarabel.SecondOrderConeT(len(vector)+1))
    matrices.extend([sparse.eye(problem.width, format='csc'), -sparse.eye(problem.width, format='csc')])
    rhs.extend([np.ones(problem.width), np.ones(problem.width)])
    cones.extend([clarabel.NonnegativeConeT(problem.width)]*2)
    settings = clarabel.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-9
    if hasattr(settings, 'max_threads'): settings.max_threads = 1
    if not np.isfinite(gradient).all() or np.max(np.abs(gradient)) == 0:
        return None, dict(status='ZeroGradient')
    result = clarabel.DefaultSolver(sparse.eye(problem.width, format='csc')*1e-4,
        gradient/max(np.abs(gradient)), sparse.vstack(matrices, format='csc'), np.concatenate(rhs), cones, settings).solve()
    delta = np.asarray(result.x)*trust
    record = dict(status=str(result.status), iterations=result.iterations, solve_time_s=result.solve_time,
        variables=problem.width, linear_rows=sum(len(v) for v, _, _ in constraints.linear), norm_cones=len(constraints.norms),
        objective=objective, predicted_change=float(gradient@delta), trust=trust)
    if str(result.status) not in ('Solved', 'AlmostSolved') or not np.isfinite(delta).all() or np.abs(delta).max() > trust+1e-9:
        return None, record
    return delta, record


def solve(problem, steps=3, trusts=(.005, .001, .0002), fractions=(1., .5, .25, .125)):
    fractions = tuple(fractions)
    if not 1 <= len(fractions) <= 11 or fractions[0] != 1. or any(
            not np.isfinite(f) or not 0 < f <= 1 for f in fractions) or any(
            a <= b for a, b in zip(fractions, fractions[1:])):
        raise ValueError('Use one to eleven strictly decreasing positive fractions starting at1')
    x = problem.initial[problem.frames].ravel().copy(); history = []
    initial = problem.pair(x)
    if min(initial[2].margins().values()) < -1e-8:
        raise ValueError('Source reconstruction violates frozen block constraints: '+str(initial[2].margins()))
    for iteration in range(steps):
        old = problem.pair(x)[0]; attempts = []; accepted = False
        for trust in trusts:
            delta, record = direction(problem, x, trust); record['trials'] = []
            if delta is not None and record['predicted_change'] < 0:
                record['delta'] = delta.tolist()
                for fraction in fractions:
                    trial = problem.pair(x+fraction*delta)
                    margins = trial[2].margins()
                    feasible = all(np.isfinite(v) and v >= -1e-9 for v in margins.values())
                    geometry, excess = problem.midpoint_guard(trial[3]) if feasible else (False, None)
                    good = bool(feasible and geometry and trial[0] < old-max(1e-9, old*.001))
                    record['trials'].append(dict(fraction=fraction, objective=trial[0], margins=margins,
                        midpoint_pass=geometry, midpoint_excess_m=excess, accepted=good))
                    if good:
                        x += fraction*delta; accepted = True; break
            attempts.append(record)
            if accepted: break
        history.append(dict(iteration=iteration, accepted=accepted, attempts=attempts))
        if not accepted: break
    return problem.values(x), dict(initial_objective=initial[0], final_objective=problem.pair(x)[0],
        frames=problem.frames.tolist(), history=history, steps_limit=steps, trusts=list(trusts), fractions=list(fractions), quality_approved=False)
