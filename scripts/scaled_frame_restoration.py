"""Positive rescaling of the complete capped-restoration objective.

The motion objective AND slack penalty are divided by the same constant.
Constraint values, Jacobians, bounds and physical acceptance rules are unchanged.
"""
import numpy as np
from scipy.optimize import minimize
from frame_capped_restoration import RelaxedRows


def scaled_energy(objective, penalty, scale):
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('Positive finite objective scale required')
    def energy(y):
        value, gradient = objective(y[:-1])
        return (value + .5 * (y[-1] * penalty)**2) / scale, np.r_[gradient, y[-1] * penalty**2] / scale
    return energy


def solve(objective, inequalities, x, lower, upper, budgets, scale=1000.):
    x, lower, upper = [np.asarray(v, dtype=float) for v in (x, lower, upper)]
    if x.ndim != 1 or not x.size or lower.shape != x.shape or upper.shape != x.shape:
        raise ValueError('Matching nonempty control/bound vectors required')
    if not np.isfinite(np.r_[x, lower, upper]).all() or np.any(lower > x) or np.any(x > upper):
        raise ValueError('Finite controls inside hard bounds required')
    if not np.isfinite(scale) or not 1 <= scale <= 1000:
        raise ValueError('Objective scale must be between one and 1000')
    constraint = RelaxedRows(inequalities, budgets, len(x))
    seed = np.r_[x, 1. if np.any(constraint.budgets) else 0.]
    if np.min(constraint(seed)[0], initial=0.) < -1e-8:
        raise ValueError('Seed violates frame budgets or unrelaxed hard constraints')
    penalty = float(np.max(constraint.budgets, initial=0.) * 1000.)
    result = minimize(scaled_energy(objective, penalty, scale), seed, jac=True, method='SLSQP',
        bounds=list(zip(lower, upper)) + [(0., 1.)],
        constraints=[dict(type='ineq', fun=lambda y: constraint(y)[0], jac=lambda y: constraint(y)[1])],
        options=dict(maxiter=60, ftol=1e-9 / scale))
    result.objective_scale = float(scale)
    result.solver_ftol = 1e-9 / scale
    result.restoration_fraction = float(result.x[-1])
    result.restoration_slack_m = float(result.x[-1] * np.max(constraint.budgets, initial=0.))
    result.relaxed_constraint_min = float(np.min(constraint(result.x)[0], initial=0.))
    result.x = result.x[:-1]
    return result
