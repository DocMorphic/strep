"""Generate bounded correction-step proposals with the first pose fixed.

These are root translations and local rotation-vector *corrections*, not total
motion velocities or anatomical limits. Projection does not preserve contacts
or floor clearance. Every proposal needs complete decoded motion validation.
"""
import numpy as np


def project_steps(values, *, root_step_m, rotation_step_degrees,
                  root_reserve_m=0., rotation_reserve_radians=0.):
    values = np.asarray(values, float)
    options = [root_step_m, rotation_step_degrees, root_reserve_m, rotation_reserve_radians]
    if (any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)) for v in options)
            or not np.isfinite(options).all()
            or root_step_m <= 0 or not 0 < rotation_step_degrees <= 180
            or not 0 <= root_reserve_m < root_step_m
            or not 0 <= rotation_reserve_radians < np.deg2rad(rotation_step_degrees)
            or values.ndim != 2 or not 2 <= len(values) <= 8
            or values.shape[1] < 6 or values.shape[1] % 3
            or not np.isfinite(values).all()):
        raise ValueError('Two to eight finite correction poses and positive step limits with smaller nonnegative reserves required')
    result = values.reshape(len(values), -1, 3).copy()
    limits = np.r_[root_step_m-root_reserve_m,
                   np.full(result.shape[1]-1, np.deg2rad(rotation_step_degrees)-rotation_reserve_radians)]
    for index in range(1, len(result)):
        with np.errstate(over='ignore', invalid='ignore'):
            delta = result[index]-result[index-1]
            lengths = np.linalg.norm(delta, axis=1)
        if not np.isfinite(lengths).all():
            raise ValueError('Correction differences exceed finite arithmetic range')
        changed = lengths > limits
        # Do not rewrite unchanged blocks; already feasible inputs retain their
        # exact values rather than accumulating subtract/add rounding.
        result[index, changed] = (result[index-1, changed]
            + delta[changed]*(limits[changed]/lengths[changed])[:, None])
    return result.reshape(values.shape)
