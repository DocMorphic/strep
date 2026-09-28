"""Experimental per-frame restoration budgets; never an animation approval.

The homotopy variable is bounded to [0, 1]. At one, each surface row may
use its frame's existing depth/screen allowance; at zero, clearance is hard.
Root/joint/edit constraints are never relaxed. Fresh geometry and the existing
screen_path_guard are still required after solving fixed correspondences.
"""
import numpy as np
from scipy.optimize import minimize


def frame_caps(depths, screen):
    depths = np.asarray(depths, dtype=float)
    if depths.ndim != 1 or not depths.size or not np.isfinite(depths).all() or np.any(depths < 0):
        raise ValueError('Finite nonnegative frame depths required')
    if not np.isfinite(screen) or screen < 0:
        raise ValueError('Finite nonnegative screen required')
    # Preserve the global peak too, including when every frame already passes.
    return np.maximum(depths, min(float(screen), float(depths.max())))


def row_budgets(depths, counts, margin, screen):
    counts = np.asarray(counts)
    caps = frame_caps(depths, screen)
    if counts.shape != caps.shape or not np.issubdtype(counts.dtype, np.integer) or np.any(counts < 0):
        raise ValueError('One nonnegative integer row count per frame required')
    if not np.isfinite(margin) or margin < 0:
        raise ValueError('Finite nonnegative clearance margin required')
    budgets = np.repeat(caps + margin, counts)
    if np.any(budgets > .12):
        raise ValueError('Restoration budget exceeds declared 120 mm cap')
    return budgets


class RelaxedRows:
    def __init__(self, inequalities, budgets, dimension):
        self.inequalities = inequalities
        self.budgets = np.asarray(budgets, dtype=float).copy()
        if self.budgets.ndim != 1 or not np.isfinite(self.budgets).all() or np.any(self.budgets < 0) or np.any(self.budgets > .12):
            raise ValueError('Finite surface budgets between zero and 120 mm required')
        self.dimension = dimension

    def __call__(self, y):
        values, jac = self.inequalities(y[:-1])
        values, jac = np.asarray(values, float), np.asarray(jac, float)
        n = len(self.budgets)
        if values.ndim != 1 or len(values) < n or jac.shape != (len(values), self.dimension):
            raise ValueError('Inequality shape mismatch')
        if not np.isfinite(values).all() or not np.isfinite(jac).all():
            raise ValueError('Nonfinite inequality evaluation')
        values = values.copy()
        jac = np.c_[jac, np.zeros(len(values))]
        values[:n] = (values[:n] + self.budgets * y[-1]) / .03
        jac[:n, :-1] /= .03
        jac[:n, -1] = self.budgets / .03
        return values, jac


def solve(objective, inequalities, x, lower, upper, budgets):
    x, lower, upper = [np.asarray(v, dtype=float) for v in (x, lower, upper)]
    if x.ndim != 1 or not x.size or lower.shape != x.shape or upper.shape != x.shape:
        raise ValueError('Matching nonempty control/bound vectors required')
    if not np.isfinite(np.r_[x, lower, upper]).all() or np.any(lower > x) or np.any(x > upper):
        raise ValueError('Finite controls inside hard bounds required')
    constraint = RelaxedRows(inequalities, budgets, len(x))
    seed = np.r_[x, 1. if np.any(constraint.budgets) else 0.]
    if np.min(constraint(seed)[0], initial=0.) < -1e-8:
        raise ValueError('Seed violates frame budgets or unrelaxed hard constraints')
    penalty = float(np.max(constraint.budgets, initial=0.) * 1000.)

    def energy(y):
        value, gradient = objective(y[:-1])
        return value + .5 * (y[-1] * penalty)**2, np.r_[gradient, y[-1] * penalty**2]

    result = minimize(energy, seed, jac=True, method='SLSQP',
        bounds=list(zip(lower, upper)) + [(0., 1.)],
        constraints=[dict(type='ineq', fun=lambda y: constraint(y)[0], jac=lambda y: constraint(y)[1])],
        options=dict(maxiter=60, ftol=1e-9))
    result.restoration_fraction = float(result.x[-1])
    result.restoration_slack_m = float(result.x[-1] * np.max(constraint.budgets, initial=0.))
    result.relaxed_constraint_min = float(np.min(constraint(result.x)[0], initial=0.))
    result.x = result.x[:-1]
    return result
