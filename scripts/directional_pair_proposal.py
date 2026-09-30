"""Explore a relative surface displacement without changing any hard bounds."""
import numpy as np
from scipy import sparse
from coupled_pair_proposal import check_step


def surface_directions(normal):
    normal = np.asarray(normal, float)
    if normal.shape != (3,) or not np.isfinite(normal).all() or np.linalg.norm(normal) < 1e-12:
        raise ValueError('Finite nonzero surface normal required')
    normal = normal/np.linalg.norm(normal)
    axis = np.eye(3)[np.argmin(np.abs(normal))]
    tangent = np.cross(normal, axis); tangent /= np.linalg.norm(tangent)
    bitangent = np.cross(normal, tangent)
    return [(label+suffix, sign*value) for label, value in
            [('normal', normal), ('tangent', tangent), ('bitangent', bitangent)]
            for suffix, sign in [('plus', 1), ('minus', -1)]]


def solve(gaps, gap_jacobian, depth_caps, vectors, jacobians, radii, objective,
          trust, scale=.025, regularizer=5e-8, norm_tolerances=None):
    arrays = [np.asarray(v, float) for v in
              [gaps, gap_jacobian, depth_caps, vectors, jacobians, radii, objective]]
    gaps, gj, caps, vectors, jacobians, radii, objective = arrays
    if gj.ndim != 2 or not len(gaps): raise ValueError('Nonempty surface rows required')
    n = gj.shape[1]
    if (n == 0 or n%3 or gaps.shape != (len(gj),) or caps.shape != gaps.shape
            or objective.shape != (n,) or vectors.shape != (len(radii), 3)
            or jacobians.shape != (len(radii), 3, n) or radii.ndim != 1):
        raise ValueError('Matching surface, objective and norm rows required')
    if (not all(np.isfinite(v).all() for v in arrays+[np.array([trust, scale, regularizer])])
            or min(trust, scale, regularizer) <= 0 or np.any(caps < 0) or np.any(radii < 0)):
        raise ValueError('Finite data, positive scales and nonnegative caps required')
    tolerances = np.full(len(radii), 1e-8) if norm_tolerances is None else np.asarray(norm_tolerances, float)
    if tolerances.shape != radii.shape or not np.isfinite(tolerances).all() or np.any(tolerances < 0):
        raise ValueError('Matching finite norm tolerances required')
    from conic_root_descent import solver_module
    clarabel = solver_module()
    matrices = [sparse.csc_matrix(-gj*trust/scale)]
    rhs = [(gaps+caps)/scale]; cones = [clarabel.NonnegativeConeT(len(gaps))]
    def ball(vector, jacobian, radius):
        if radius == 0:
            matrices.append(sparse.csc_matrix(-jacobian)); rhs.append(vector)
            cones.append(clarabel.ZeroConeT(3))
        else:
            matrices.append(sparse.csc_matrix(np.vstack([np.zeros(n), -jacobian])/radius))
            rhs.append(np.r_[radius, vector]/radius); cones.append(clarabel.SecondOrderConeT(4))
    for value, jac, cap in zip(vectors, jacobians, radii): ball(value, jac*trust, cap)
    eye = np.eye(n)
    for start in range(0, n, 3): ball(np.zeros(3), eye[start:start+3], 1.)
    settings = clarabel.DefaultSettings(); settings.verbose = False
    settings.max_iter = 100; settings.time_limit = 30.
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-9
    if hasattr(settings, 'max_threads'): settings.max_threads = 1
    result = clarabel.DefaultSolver(sparse.eye(n, format='csc')*(2*regularizer),
        -objective*trust/scale, sparse.vstack(matrices, format='csc'),
        np.concatenate(rhs), cones, settings).solve()
    step = np.asarray(result.x, float)*trust
    if step.shape != (n,) or not np.isfinite(step).all(): raise ValueError('Finite matching solution required')
    checks = check_step(step, gaps, gj, caps, vectors, jacobians, radii, trust)
    norms = np.linalg.norm(vectors+np.einsum('nid,d->ni', jacobians, step), axis=1)
    failures = int((norms-radii > tolerances).sum())
    passed = (str(result.status) in ['Solved', 'AlmostSolved'] and failures == 0
              and checks['per_frame_cap_excess_m'] <= 1e-8 and checks['trust_excess_radians'] <= 1e-8)
    report = dict(status=str(result.status), iterations=result.iterations, seconds=result.solve_time,
        surface_rows=len(gaps), norm_rows=len(radii), failed_norms=failures,
        directional_gain_m=float(objective@step), initial_peak_m=float(np.maximum(-gaps, 0).max()),
        proposal_hard_checks=bool(passed), **checks, quality_approved=False)
    return step if passed else None, report
