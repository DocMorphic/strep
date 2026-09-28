"""Timed arm controls with full rotation-ball budgets and sampled speed limits.

The piecewise-linear control basis is nonnegative with row sums at most one.
Constraining each control vector therefore bounds every integer-frame vector.
Decoded fractional rotations still require independent export verification.
"""
import numpy as np
from paired_hand_trajectory import TrajectoryFitter


def ball_pair(values, radii):
    values, radii = np.asarray(values, dtype=float), np.asarray(radii, dtype=float)
    if values.ndim != 1 or len(values) != 3*len(radii) or np.any(radii <= 0) or not np.isfinite(values).all() or not np.isfinite(radii).all():
        raise ValueError('Finite vectors and positive norm budgets required')
    vectors = values.reshape(-1, 3)
    slack = 1-np.sum(vectors*vectors, axis=1)/(radii*radii)
    jac = np.zeros((len(radii), len(values)))
    for i in range(len(radii)):
        jac[i, 3*i:3*i+3] = -2*vectors[i]/radii[i]**2
    return slack, jac


class BoundedPathFitter(TrajectoryFitter):
    def __init__(self, actors, event=75, fade=30, knots=(50, 62.5, 75, 87.5, 100)):
        super().__init__(actors, event=event, fade=fade, knots=knots)
        self.control_radii = np.concatenate([np.tile(a.limits, len(knots)) for a in actors])
        self.bounds = np.repeat(self.control_radii, 3)
        if np.any(self.matrix < 0) or np.any(self.matrix.sum(axis=1) > 1+1e-12):
            raise ValueError('Control basis must preserve convex rotation budgets')

    def step_pair(self, x):
        speed, speed_jac = super().step_pair(x)
        norm, norm_jac = ball_pair(x, self.control_radii)
        return np.r_[speed, norm], np.vstack([speed_jac, norm_jac])
