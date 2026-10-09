"""Optional complete affine norm-ball starts; never nonlinear pose acceptance.

This isolated proposal helper does not replace the published LP/default fitter.
Every returned point is checked against the original scalar/vector population.
"""
import time
import numpy as np
from scipy import sparse

VERSION = '0.11.1'
CHECK = 1e-8
TIE = 1e-6


def solver_module():
    try:
        import clarabel
    except ImportError as exc:
        raise RuntimeError('Install requirements-scene-proposals.txt for optional conic starts') from exc
    if clarabel.__version__ != VERSION:
        raise ValueError('Conic starts require Clarabel '+VERSION)
    return clarabel


def direction(values, jac, caps, lower, upper, seconds, vectors, *, priority='worst-first'):
    """Return an independently checked affine start inside one shared budget.

    Scalar rows, vector rows (including duplicates), and all control bounds
    remain hard. Worst-first minimizes the original scalar epigraph then the
    squared-violation slope within the existing 1e-6 epigraph tie allowance.
    A returned start still requires full nonlinear and saved-pose replay.
    """
    started = time.monotonic()
    values, jac, caps, lower, upper = [np.asarray(v, dtype=float) for v in (values, jac, caps, lower, upper)]
    n = len(lower) if lower.ndim == 1 else 0
    if (not n or values.ndim != 1 or not len(values) or jac.shape != (len(values), n)
            or caps.shape != values.shape or upper.shape != lower.shape
            or not all(np.isfinite(v).all() for v in (values, jac, caps, lower, upper))
            or np.any(lower > upper) or priority not in ('merit', 'worst-first')
            or type(seconds) not in (int, float) or not np.isfinite(seconds) or not 0 < seconds <= 20):
        raise ValueError('Complete finite scalar rows, ordered control bounds and bounded proposal budget required')
    offsets, derivatives, radii, scales = [np.asarray(vectors[k], dtype=float) for k in ('offsets', 'jacobian', 'limits', 'scales')]
    rows, distance = [np.asarray(vectors[k]) for k in ('rows', 'distance')]
    count = len(radii) if radii.ndim == 1 else 0
    if (not count or offsets.shape != (count, 3) or derivatives.shape != (count, 3, n)
            or scales.shape != (count,) or rows.shape != (count,) or rows.dtype.kind not in 'iu'
            or distance.shape != (count,) or distance.dtype != bool
            or np.any(rows < 0) or np.any(rows >= len(values))
            or not all(np.isfinite(v).all() for v in (offsets, derivatives, radii, scales))
            or np.any(radii <= 0) or np.any(scales <= 0)):
        raise ValueError('Complete finite norm vectors, derivatives, limits, scales and row identities required')
    length = np.linalg.norm(offsets, axis=1)
    vector_values = np.where(distance, (radii-length)/scales, 1-length**2/radii**2)
    envelope = np.full(len(values), np.inf)
    np.minimum.at(envelope, rows, vector_values)
    covered = np.isfinite(envelope)
    if not np.allclose(envelope[covered], values[covered], rtol=1e-10, atol=1e-10):
        raise ValueError('Norm vectors differ from the complete measured scalar population')
    effective = np.where(distance, radii-scales*caps[rows], radii*np.sqrt(np.maximum(1-caps[rows], 0)))
    gradient = 2*jac.T@np.minimum(values, 0)
    if not np.isfinite(effective).all() or not np.isfinite(gradient).all():
        raise ValueError('Finite derived norm radii and merit gradient required')
    worst = float(max(0., -values.min()))
    report = dict(algorithm='Complete affine norm cones', priority=priority, scalar_rows=len(values),
        norm_cones=count, controls=n, time_limit_seconds=float(seconds), initial_worst=worst,
        epigraph_tie_tolerance=TIE, retained=False, quality_approved=False, release_approved=False,
        scope='Checked affine proposal only; no nonlinear, saved-representation, path or animation approval.')
    def finish(status, success=False, **extra):
        return dict(report, status=status, success=success, seconds=time.monotonic()-started, **extra)
    if np.any(effective <= 0):
        return None, finish('empty_vector_radius')
    if np.max(abs(gradient)) == 0:
        return None, finish('no_checked_geometry_descent')
    backend = solver_module()
    width = n+1 if priority == 'worst-first' else n
    linear = sparse.vstack([-sparse.csc_matrix(jac), sparse.eye(n), -sparse.eye(n)], format='csc')
    right = np.r_[values-caps, upper, -lower]
    if priority == 'worst-first':
        linear = sparse.vstack([sparse.hstack([linear, sparse.csc_matrix((len(right), 1))]),
            sparse.csc_matrix(np.r_[gradient, 0.][None]),
            sparse.hstack([-sparse.csc_matrix(jac), -np.ones((len(values), 1))]),
            sparse.csc_matrix(np.r_[np.zeros(n), -1.][None]),
            sparse.csc_matrix(np.r_[np.zeros(n), 1.][None])], format='csc')
        right = np.r_[right, -CHECK, values, 0., worst]
    # b-Ax = [1, (offset + derivative @ delta) / radius] for every ball.
    derivative = sparse.coo_matrix((-derivatives/effective[:, None, None]).reshape(3*count, n))
    norm_matrix = sparse.csc_matrix((derivative.data,
        (4*(derivative.row//3)+1+derivative.row%3, derivative.col)), shape=(4*count, width))
    matrix = sparse.vstack([linear, norm_matrix], format='csc')
    bound = np.r_[right, np.c_[np.ones(count), offsets/effective[:, None]].ravel()]
    cones = [backend.NonnegativeConeT(len(right))]+[backend.SecondOrderConeT(4) for _ in range(count)]
    zero = sparse.csc_matrix((width, width))
    def solve(q, a, b, types):
        remaining = seconds-(time.monotonic()-started)
        if remaining <= 0:
            return None
        settings = backend.DefaultSettings(); settings.verbose = False
        settings.max_iter = 100; settings.time_limit = remaining
        settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-10
        if hasattr(settings, 'max_threads'):
            settings.max_threads = 1
        return backend.DefaultSolver(zero, q, a, b, types, settings).solve()
    def check(point, ceiling=None):
        point = np.asarray(point, dtype=float)
        if point.shape != (width,) or not np.isfinite(point).all():
            return None, dict(check_status='invalid_solution')
        raw = point[:n]
        if np.any(raw < lower-CHECK) or np.any(raw > upper+CHECK):
            return None, dict(check_status='step_bounds_failed')
        delta = np.clip(raw, lower, upper)
        slack = values+jac@delta-caps
        balls = 1-np.linalg.norm(offsets+np.einsum('rkd,d->rk', derivatives, delta), axis=1)**2/effective**2
        descent = float(gradient@delta); predicted = float(max(0., -(values+jac@delta).min()))
        info = dict(minimum_linear_slack=float(slack.min()), minimum_vector_slack=float(balls.min()),
            directional_merit=descent, predicted_worst=predicted, clipped_to_step_bounds=bool(np.any(raw != delta)))
        if not np.isfinite(slack).all() or not np.isfinite(balls).all() or not np.isfinite(descent):
            return None, dict(info, check_status='nonfinite_replay')
        if slack.min() < -CHECK or balls.min() < -CHECK or descent >= -CHECK:
            return None, dict(info, check_status='complete_affine_replay_failed')
        if priority == 'worst-first':
            epigraph = float(point[-1]); info['epigraph'] = epigraph
            if (not -CHECK <= epigraph <= worst+CHECK or predicted > epigraph+CHECK
                    or predicted >= worst-CHECK or (ceiling is not None and epigraph > ceiling+CHECK)):
                return None, dict(info, check_status='priority_epigraph_failed')
        return delta, dict(info, check_status='complete_affine_replay_passed')
    q = np.r_[np.zeros(n), 1.] if priority == 'worst-first' else gradient/np.max(abs(gradient))
    primary = solve(q, matrix, bound, cones)
    if primary is None:
        return None, finish('geometry_start_time_guard')
    report.update(solver_version=backend.__version__, primary_status=str(primary.status), primary_iterations=primary.iterations)
    if str(primary.status) not in ('Solved', 'AlmostSolved'):
        return None, finish('primary_start_unavailable')
    delta, checked = check(primary.x)
    if delta is None:
        return None, finish('primary_replay_failed', **checked)
    report['primary_delta'] = delta.tolist()
    selected = 'primary'
    if priority == 'worst-first':
        ceiling = float(primary.x[-1])+TIE
        tie_matrix = sparse.vstack([matrix, sparse.csc_matrix(np.r_[np.zeros(n), 1.][None])], format='csc')
        secondary = solve(np.r_[gradient/np.max(abs(gradient)), 0.], tie_matrix, np.r_[bound, ceiling],
            cones+[backend.NonnegativeConeT(1)])
        report['secondary_status'] = 'budget_exhausted' if secondary is None else str(secondary.status)
        if secondary is not None and str(secondary.status) in ('Solved', 'AlmostSolved'):
            alternate, alternate_check = check(secondary.x, ceiling)
            report['secondary_replay'] = alternate_check
            if alternate is not None:
                delta, checked = alternate, alternate_check; selected = 'secondary'
    return delta, finish('usable', success=True, selected_phase=selected, delta=delta.tolist(), **checked)
