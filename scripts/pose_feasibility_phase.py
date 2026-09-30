"""Normalized Phase-I adapter; temporary slack never changes pose acceptance.

The first geometry_rows inequalities may share a nonnegative scalar slack.
Remaining inequalities and all variable bounds stay hard. Minimizing that
scalar is a local feasibility search, not an infeasibility certificate.
"""
import numpy as np


class PhaseOne:
    def __init__(self, pair, seed, scale, lower, upper, geometry_rows):
        self.pair = pair
        self.seed = np.asarray(seed, dtype=float).copy()
        self.scale = np.asarray(scale, dtype=float).copy()
        lower, upper = np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)
        if self.seed.ndim != 1 or not len(self.seed):
            raise ValueError('Nonempty parameter vector required')
        if any(a.shape != self.seed.shape or not np.isfinite(a).all()
               for a in [self.seed, self.scale, lower, upper]):
            raise ValueError('Finite matching parameter vectors required')
        if np.any(self.scale <= 0) or np.any(lower >= upper):
            raise ValueError('Positive scales and ordered bounds required')
        if np.any(self.seed < lower) or np.any(self.seed > upper):
            raise ValueError('Seed violates hard variable bounds')
        values, jac = pair(self.seed)
        values, jac = np.asarray(values), np.asarray(jac)
        if values.ndim != 1 or jac.shape != (len(values), len(self.seed)):
            raise ValueError('Invalid constraint/Jacobian shape')
        if not np.isfinite(values).all() or not np.isfinite(jac).all():
            raise ValueError('Nonfinite constraints')
        if type(geometry_rows) is not int or not 0 < geometry_rows < len(values):
            raise ValueError('Separate geometry and hard constraint rows required')
        if np.min(values[geometry_rows:]) < -1e-8:
            raise ValueError('Seed violates hard constraints')
        self.geometry_rows = geometry_rows
        self.rows = len(values)
        self.initial = np.r_[self.seed/self.scale, max(0., -values[:geometry_rows].min())]
        self.bounds = list(zip(lower/self.scale, upper/self.scale)) + [(0., None)]

    def physical(self, z):
        z = np.asarray(z, dtype=float)
        if z.shape != (len(self.seed)+1,) or not np.isfinite(z).all():
            raise ValueError('Finite augmented parameter vector required')
        return z[:-1]*self.scale

    def constraints(self, z):
        values, jac = self.pair(self.physical(z))
        values, jac = np.asarray(values, dtype=float).copy(), np.asarray(jac, dtype=float)
        if values.shape != (self.rows,) or jac.shape != (self.rows, len(self.seed)):
            raise ValueError('Constraint layout changed')
        if not np.isfinite(values).all() or not np.isfinite(jac).all():
            raise ValueError('Nonfinite constraints')
        values[:self.geometry_rows] += z[-1]
        augmented = np.zeros((self.rows, len(self.seed)+1))
        augmented[:, :-1] = jac*self.scale
        augmented[:self.geometry_rows, -1] = 1.
        return values, augmented

    def objective(self, z):
        self.physical(z)
        gradient = np.zeros(len(self.seed)+1)
        gradient[-1] = 1.
        return float(z[-1]), gradient
