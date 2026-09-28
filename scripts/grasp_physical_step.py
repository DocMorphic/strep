"""Local epigraph LP with protected rows and conservative rotation-ball remainder."""
import numpy as np
from scipy.optimize import linprog


def epigraph_step(surface, surface_jac, protected, protected_jac, margins, radius, lower, upper):
    surface, surface_jac, protected, protected_jac, margins, radius, lower, upper = [
        np.asarray(v, float) for v in (surface, surface_jac, protected, protected_jac, margins, radius, lower, upper)]
    n = len(radius)
    if surface.ndim != 1 or not len(surface) or surface_jac.shape != (len(surface), n):
        raise ValueError('Nonempty surface rows with matching Jacobian required')
    if protected.ndim != 1 or protected_jac.shape != (len(protected), n) or margins.shape != protected.shape:
        raise ValueError('Protected row shape mismatch')
    if lower.shape != radius.shape or upper.shape != radius.shape or np.any(radius <= 0) or np.any(lower > upper):
        raise ValueError('Invalid trust or coordinate bounds')
    if not all(np.isfinite(v).all() for v in (surface, surface_jac, protected, protected_jac, margins, radius, lower, upper)):
        raise ValueError('Finite LP inputs required')
    a = np.r_[np.c_[-surface_jac*radius, -np.ones(len(surface))],
              np.c_[-protected_jac*radius, np.zeros(len(protected))]]
    b = np.r_[surface, protected-margins]
    bounds = list(zip(np.maximum(-1., lower/radius), np.minimum(1., upper/radius))) + [(None, None)]
    objective = np.r_[np.zeros(n), 1.]
    options = dict(primal_feasibility_tolerance=1e-9, dual_feasibility_tolerance=1e-9)
    primary = linprog(objective, A_ub=a, b_ub=b, bounds=bounds, method='highs', options=options)
    record = dict(success=bool(primary.success), message=str(primary.message), status=int(primary.status))
    if not primary.success:
        return None, record
    # Lexicographic tie break: minimize total normalized displacement while
    # retaining the primary optimum to 1e-8 normalized units (0.1 nanometres).
    tie_a = np.r_[np.c_[a, np.zeros((len(a), n))],
                  np.c_[np.eye(n), np.zeros(n), -np.eye(n)],
                  np.c_[-np.eye(n), np.zeros(n), -np.eye(n)],
                  np.r_[np.zeros(n), 1., np.zeros(n)][None]]
    tie_b = np.r_[b, np.zeros(2*n), primary.fun+1e-8]
    secondary = linprog(np.r_[np.zeros(n+1), np.ones(n)], A_ub=tie_a, b_ub=tie_b,
                        bounds=bounds+[(0., None)]*n, method='highs', options=options)
    chosen = secondary.x[:n+1] if secondary.success else primary.x
    delta = radius*chosen[:n]
    record.update(predicted_worst_violation_normalized=float(chosen[n]),
                  primary_optimum=float(primary.fun), tie_break_success=bool(secondary.success),
                  predicted_protected_minimum=float((protected+protected_jac@delta-margins).min()))
    return delta, record


def norm_remainder(radius, limits):
    """Upper bound for ||delta_theta||^2 / limit^2 inside a trust box."""
    return np.sum(np.asarray(radius[:-1]).reshape(-1, 3)**2, axis=1) / np.asarray(limits)**2
