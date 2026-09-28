"""Differentiable rigid-patch upper bound for an inward radial sphere contact."""
import numpy as np
import torch


def radial_clearance_upper(offsets, normal, distance, radius, point_tolerance, normal_tolerance_degrees):
    if offsets.ndim != 2 or offsets.shape[1] != 3 or normal.shape != (3,):
        raise ValueError('Nx3 offsets and a unit normal required')
    if not np.isfinite([distance, radius, point_tolerance, normal_tolerance_degrees]).all() or distance <= 0 or radius <= 0 or point_tolerance < 0 or not 0 <= normal_tolerance_degrees <= 180:
        raise ValueError('Invalid radial contact geometry')
    epsilon = np.deg2rad(normal_tolerance_degrees)
    axial = offsets@normal
    lateral = torch.linalg.vector_norm(offsets-axial[:, None]*normal, dim=-1)
    length = torch.linalg.vector_norm(offsets, dim=-1)
    # If the offset can align directly with the outward radial direction,
    # use its length. Otherwise the optimal normal lies on the cone boundary.
    radial = torch.where(axial <= -length*np.cos(epsilon), length,
                         -axial*np.cos(epsilon)+lateral*np.sin(epsilon))
    return torch.sqrt(torch.clamp(distance**2+length**2+2*distance*radial, min=0.))+point_tolerance-radius
