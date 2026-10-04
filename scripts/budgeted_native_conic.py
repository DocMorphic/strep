"""Explicit bounded CPU budgets for the unchanged native norm-cone formulation.

The historical 30-second model stays immutable. Assembly and model construction
are outside each solver phase budget; an affine direction is not clip approval.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module,solver_identity
from native_support_feasibility import merit


def direction(system,jacobian,value,lower,upper,trust,*,hard_rows=0,
              phase_seconds=120.,maximum_iterations=200):
    if (type(phase_seconds) not in (int,float) or not np.isfinite(phase_seconds)
            or not 1.<=phase_seconds<=300. or type(maximum_iterations) is not int
            or not 1<=maximum_iterations<=500):
        raise ValueError('Explicit solver phase budget of 1..300 seconds and 1..500 iterations required')
    delta,record=_direction(system,jacobian,value,lower,upper,trust,hard_rows=hard_rows,
        phase_seconds=float(phase_seconds),maximum_iterations=maximum_iterations)
    return delta,dict(record,phase_time_limit_seconds=float(phase_seconds),phase_maximum_iterations=maximum_iterations,
        formulation='Unchanged complete native norm-cone minimax and optional minimum-norm phase',
        assembly_and_model_construction_outside_phase_budget=True,physical_or_authored_limits_relaxed=False,
        independently_decoded_candidate_required=True,quality_approved=False,release_approved=False)


def _direction(system, jacobian, value, lower, upper, trust, *, hard_rows=0, phase_seconds, maximum_iterations):
    (value, lower, upper) = [np.asarray(a, float) for a in (value, lower, upper)]
    if value.ndim != 1:
        raise ValueError('One-dimensional vector controls required')
    n = len(value)
    if type(hard_rows) is not int or not 0 <= hard_rows <= len(system.vectors):
        raise ValueError('Valid protected norm row prefix required')
    if sparse.issparse(jacobian):
        jacobian = sparse.csr_matrix(jacobian)
    else:
        jacobian = np.asarray(jacobian, float)
        if jacobian.shape != (*system.vectors.shape, n):
            raise ValueError('Matching dense vector Jacobian required')
        jacobian = sparse.csr_matrix(jacobian.reshape(system.vectors.size, n))
    if not n or lower.shape != value.shape or upper.shape != value.shape or (jacobian.shape != (system.vectors.size, n)) or any((not np.isfinite(a).all() for a in (value, lower, upper, jacobian.data))) or np.any(lower >= upper) or np.any(value < lower) or np.any(value > upper) or (type(trust) not in (int, float)) or (not np.isfinite(trust)) or (trust <= 0):
        raise ValueError('Finite matching vector model, ordered boxes and positive trust required')
    solver = solver_module()
    lo = np.maximum(-1.0, (lower - value) / trust)
    hi = np.minimum(1.0, (upper - value) / trust)
    mats = [sparse.hstack([sparse.eye(n), sparse.csc_matrix((n, 1))]), sparse.hstack([-sparse.eye(n), sparse.csc_matrix((n, 1))]), sparse.csc_matrix(np.r_[np.zeros(n), -1.0][None])]
    rhs = [hi, -lo, np.zeros(1)]
    cones = [solver.NonnegativeConeT(2 * n + 1)]
    jacobian.eliminate_zeros()
    counts = np.diff(jacobian.indptr).reshape(-1, 3).sum(axis=1)
    maximum_step = np.maximum(abs(lo), abs(hi)) * trust
    radius = np.asarray(abs(jacobian) @ maximum_step).reshape(system.vectors.shape)
    upper_norm = np.linalg.norm(abs(system.vectors) + radius, axis=1)
    reserve = 64 * (n + 4) * np.finfo(float).eps * np.maximum.reduce([upper_norm, abs(system.caps), np.ones(len(system.caps))])
    box_passing = (counts > 0) & np.isfinite(upper_norm) & (upper_norm + reserve <= system.caps)
    active = np.flatnonzero((counts > 0) & ~box_passing)
    fixed_mask = counts == 0
    fixed_residual = system.residual()[fixed_mask]
    fixed = fixed_residual[fixed_residual > 0]
    if np.any(system.residual()[:hard_rows][counts[:hard_rows] == 0] > 0):
        return (None, dict(status='FixedProtectedConflict', protected_norm_rows=hard_rows, scope='Fixed failed protected affine row; no decoded feasibility claim.'))
    omitted = int((fixed_residual <= 0).sum())
    if len(active):
        selected_rows = (3 * active[:, None] + np.arange(3)).ravel()
        derivative = jacobian[selected_rows].multiply((-trust / np.repeat(system.scales[active], 3))[:, None]).tocoo()
        mapped_rows = 4 * (derivative.row // 3) + 1 + derivative.row % 3
        matrix = sparse.csc_matrix((np.r_[derivative.data, -(active >= hard_rows).astype(float)], (np.r_[mapped_rows, 4 * np.arange(len(active))], np.r_[derivative.col, np.full(len(active), n)])), shape=(4 * len(active), n + 1))
        bound = np.c_[system.caps[active], system.vectors[active]] / system.scales[active, None]
        mats.append(matrix)
        rhs.append(bound.ravel())
        cones.extend((solver.SecondOrderConeT(4) for _ in active))
    if len(fixed):
        mats.append(sparse.csc_matrix(np.r_[np.zeros(n), -1.0][None]))
        rhs.append(np.array([-float(fixed.max())]))
        cones.append(solver.NonnegativeConeT(1))
    matrix = sparse.vstack(mats, format='csc')
    bound = np.concatenate(rhs)
    settings = solver.DefaultSettings()
    settings.verbose = False
    settings.max_iter = maximum_iterations
    settings.time_limit = phase_seconds
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-09
    if hasattr(settings, 'max_threads'):
        settings.max_threads = 1
    objective = np.r_[np.zeros(n), 1.0]
    first = solver.DefaultSolver(sparse.csc_matrix((n + 1, n + 1)), objective, matrix, bound, cones, settings).solve()
    info = dict(status=str(first.status), iterations=first.iterations, trust_control_fraction=float(trust), solver_version=solver.__version__, norm_rows=len(system.vectors), active_cones=len(active), protected_norm_rows=hard_rows, fixed_failed_rows=len(fixed), omitted_fixed_passing_rows=omitted, omitted_affine_box_passing_rows=int(box_passing.sum()), affine_box_bound='norm(abs(vector) + abs(J) @ maximum_absolute_step) plus arithmetic reserve', scope='Affine vector-norm proposal only; decoded constraints still decide acceptance.')
    if str(first.status) not in ('Solved', 'AlmostSolved'):
        return (None, info)
    point = np.asarray(first.x)
    if not np.isfinite(point).all():
        return (None, dict(info, invalid_solution=True))
    optimum = max(0.0, float(point[-1]))
    second_matrix = sparse.vstack([matrix, sparse.csc_matrix(np.r_[np.zeros(n), 1.0][None])], format='csc')
    second_bound = np.r_[bound, optimum + 1e-09]
    second = solver.DefaultSolver(sparse.diags(np.r_[np.ones(n), 0.0], format='csc'), np.zeros(n + 1), second_matrix, second_bound, cones + [solver.NonnegativeConeT(1)], settings).solve()
    info.update(minimum_norm_phase_status=str(second.status), affine_optimum=optimum)
    if str(second.status) in ('Solved', 'AlmostSolved') and np.isfinite(second.x).all():
        point = np.asarray(second.x)
    delta = point[:n] * trust
    if np.any(delta < lo * trust - 1e-09) or np.any(delta > hi * trust + 1e-09) or (not np.isfinite(delta).all()):
        return (None, dict(info, invalid_solution=True))
    delta = np.clip(value + delta, lower, upper) - value
    info.update(maximum_control_step=float(abs(delta).max()), predicted_norm_merit=list(merit(system.residual(jacobian, delta))))
    return (delta, info)
