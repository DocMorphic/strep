"""Mixed hard native vector norms and complete soft surface halfspaces.

Scalar surface rows use one nonnegative cone instead of artificial vector
cones. Every original native row is hard; no native/contact cap is rebased.
This is a local proposal solver, not an asset acceptance or geometry verifier.
"""
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module


def direction(system, native_jac, gaps, surface_jac, value, lower, upper, trust,
              *, clearance=.0005, scale=.005, maximum_rows=400000, maximum_nonzeros=60000000):
    value, lower, upper, gaps = [np.asarray(a, float) for a in (value, lower, upper, gaps)]
    native_jac, surface_jac = sparse.csr_matrix(native_jac), sparse.csr_matrix(surface_jac)
    if (value.ndim != 1 or not len(value) or lower.shape != value.shape or upper.shape != value.shape
            or gaps.ndim != 1 or native_jac.shape != (system.vectors.size, len(value))
            or surface_jac.shape != (len(gaps), len(value))
            or any(not np.isfinite(a).all() for a in (value, lower, upper, gaps, native_jac.data, surface_jac.data))
            or np.any(lower >= upper) or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or type(clearance) not in (int, float) or not np.isfinite(clearance) or not 0 <= clearance <= .005
            or type(scale) not in (int, float) or not np.isfinite(scale) or scale <= 0
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 400000 or len(gaps) > maximum_rows
            or type(maximum_nonzeros) is not int or not 1 <= maximum_nonzeros <= 60000000):
        raise ValueError('Finite complete mixed model and explicit resource/trust bounds required')
    native_jac.eliminate_zeros(); surface_jac.eliminate_zeros()
    if native_jac.nnz+surface_jac.nnz > maximum_nonzeros:
        raise ValueError('Complete mixed Jacobian exceeds resource budget; no subset returned')
    n = len(value); solver = solver_module()
    lo, hi = np.maximum(-1., (lower-value)/trust), np.minimum(1., (upper-value)/trust)
    counts = np.diff(native_jac.indptr).reshape(-1, 3).sum(axis=1)
    fixed = counts == 0
    info = dict(protected_norm_rows=len(system.caps), surface_rows=len(gaps),
        scalar_rows_encoded=len(gaps), scalar_rows_omitted=0, trust_control_fraction=float(trust),
        clearance_m=float(clearance), scale_m=float(scale), solver_version=solver.__version__,
        quality_approved=False, release_approved=False,
        scope='Hard original native norms and every soft affine surface halfspace; decoded acceptance required.')
    if np.any(system.residual()[fixed] > 0):
        return None, dict(info, status='FixedProtectedConflict')
    maximum_step = np.maximum(abs(lo), abs(hi))*trust
    radius = np.asarray(abs(native_jac) @ maximum_step).reshape(system.vectors.shape)
    upper_norm = np.linalg.norm(abs(system.vectors)+radius, axis=1)
    reserve = 64*(n+4)*np.finfo(float).eps*np.maximum.reduce([upper_norm, abs(system.caps), np.ones(len(system.caps))])
    box_passing = (~fixed) & np.isfinite(upper_norm) & (upper_norm+reserve <= system.caps)
    active = np.flatnonzero(~fixed & ~box_passing)
    mats = [sparse.hstack([sparse.eye(n), sparse.csc_matrix((n, 1))]),
        sparse.hstack([-sparse.eye(n), sparse.csc_matrix((n, 1))]),
        sparse.csc_matrix(np.r_[np.zeros(n), -1.][None])]
    rhs = [hi, -lo, np.zeros(1)]; cones = [solver.NonnegativeConeT(2*n+1)]
    if len(active):
        selected = (3*active[:, None]+np.arange(3)).ravel()
        derivative = native_jac[selected].multiply((-trust/np.repeat(system.scales[active], 3))[:, None]).tocoo()
        matrix = sparse.csc_matrix((derivative.data, (4*(derivative.row//3)+1+derivative.row%3,
            derivative.col)), shape=(4*len(active), n+1))
        mats.append(matrix)
        rhs.append((np.c_[system.caps[active], system.vectors[active]]/system.scales[active, None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in active)
    if len(gaps):
        # A u + s = b => s = (gap + J delta - clearance)/scale + t >= 0.
        mats.append(sparse.hstack([-trust/scale*surface_jac, -np.ones((len(gaps), 1))], format='csc'))
        rhs.append((gaps-clearance)/scale); cones.append(solver.NonnegativeConeT(len(gaps)))
    matrix, bound = sparse.vstack(mats, format='csc'), np.concatenate(rhs)
    settings = solver.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-9
    if hasattr(settings, 'max_threads'):
        settings.max_threads = 1
    first = solver.DefaultSolver(sparse.csc_matrix((n+1, n+1)), np.r_[np.zeros(n), 1.],
        matrix, bound, cones, settings).solve()
    info.update(status=str(first.status), iterations=first.iterations, active_native_cones=len(active),
        omitted_fixed_passing_native_rows=int(fixed.sum()), omitted_affine_box_passing_native_rows=int(box_passing.sum()))
    if str(first.status) not in ('Solved', 'AlmostSolved'):
        return None, info
    point = np.asarray(first.x)
    if not np.isfinite(point).all():
        return None, dict(info, invalid_solution=True)
    optimum = max(0., float(point[-1]))
    second_matrix = sparse.vstack([matrix, sparse.csc_matrix(np.r_[np.zeros(n), 1.][None])], format='csc')
    second = solver.DefaultSolver(sparse.diags(np.r_[np.ones(n), 0.], format='csc'), np.zeros(n+1),
        second_matrix, np.r_[bound, optimum+1e-9], cones+[solver.NonnegativeConeT(1)], settings).solve()
    info.update(affine_optimum=optimum, minimum_norm_phase_status=str(second.status))
    if str(second.status) in ('Solved', 'AlmostSolved') and np.isfinite(second.x).all():
        point = np.asarray(second.x)
    delta = point[:n]*trust
    if np.any(delta < lo*trust-1e-9) or np.any(delta > hi*trust+1e-9):
        return None, dict(info, invalid_solution=True)
    delta = np.clip(value+delta, lower, upper)-value
    info.update(maximum_control_step=float(abs(delta).max()),
        predicted_native_excess=float(system.residual(native_jac, delta).max()),
        predicted_surface_excess=float(max(0., ((clearance-gaps-surface_jac @ delta)/scale).max())) if len(gaps) else 0.)
    return delta, info
