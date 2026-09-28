"""Sphere-clearance upper bounds for a rigid measured contact patch."""
import numpy as np
from grasp_orientation import unit


def clearance_upper_bound(offsets, normal, target, target_normal, center, radius,
                          point_tolerance, normal_tolerance_degrees):
    offsets = np.asarray(offsets, float)
    if offsets.ndim != 2 or offsets.shape[1] != 3 or not np.isfinite(offsets).all():
        raise ValueError('Finite Nx3 patch offsets required')
    if not np.isfinite([radius, point_tolerance, normal_tolerance_degrees]).all() or radius <= 0 or point_tolerance < 0 or not 0 <= normal_tolerance_degrees <= 180:
        raise ValueError('Invalid sphere or contact tolerances')
    m, n = unit(normal), unit(target_normal)
    radial = np.asarray(target, float)-np.asarray(center, float)
    if radial.shape != (3,) or not np.isfinite(radial).all(): raise ValueError('Finite 3D target and center required')
    distance = np.linalg.norm(radial); length = np.linalg.norm(offsets, axis=1)
    if distance < 1e-15: return length+point_tolerance-radius
    alpha = np.arccos(np.clip(radial@n/distance, -1., 1.))
    gamma = np.arccos(np.clip(offsets@m/np.maximum(length, 1e-300), -1., 1.))
    epsilon = np.deg2rad(normal_tolerance_degrees)
    # Allowed normals lie within epsilon of n. A rigid vertex vector makes
    # fixed angle gamma with its normal; free twist minimizes its radial angle.
    nearest = np.maximum(0., np.maximum(alpha-epsilon-gamma, gamma-alpha-epsilon))
    maximum_distance = np.sqrt(np.maximum(0., distance**2+length**2+2*distance*length*np.cos(nearest)))
    return maximum_distance+point_tolerance-radius
