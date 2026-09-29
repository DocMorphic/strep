"""Recover bounded spline controls without resetting the original edit budget."""
import numpy as np
from scipy.spatial.transform import Rotation


def recover_controls(source_local, seed_local, editable, limits, body_count, physical_fingers, basis):
    source_local, seed_local = np.asarray(source_local), np.asarray(seed_local)
    limits = np.asarray(limits, dtype=float)
    basis = np.asarray(basis, dtype=float)
    if source_local.shape != seed_local.shape or source_local.ndim != 4 or source_local.shape[-2:] != (3, 3):
        raise ValueError('Matching frame/joint rotation matrices required')
    if len(set(editable)) != len(editable) or not editable or min(editable) < 0 or max(editable) >= source_local.shape[1]:
        raise ValueError('Distinct editable joint identities required')
    if limits.shape != (len(editable),) or not np.isfinite(limits).all() or (limits <= 0).any():
        raise ValueError('Positive finite per-joint bounds required')
    if basis.ndim != 2 or basis.shape[0] != len(source_local) or not np.isfinite(basis).all():
        raise ValueError('Matching finite spline basis required')
    if not np.isfinite(source_local).all() or not np.isfinite(seed_local).all():
        raise ValueError('Finite seed rotations required')
    relative = source_local[:, editable].transpose(0, 1, 3, 2) @ seed_local[:, editable]
    vectors = Rotation.from_matrix(relative.reshape(-1, 3, 3)).as_rotvec().reshape(len(source_local), len(editable), 3)
    magnitude2 = np.sum(vectors**2, axis=-1, keepdims=True)
    gap = limits[None, :, None]**2 - magnitude2
    if (gap <= 0).any():
        raise ValueError('Seed must be strictly inside original rotation budgets')
    parameters = vectors / np.sqrt(gap)
    if physical_fingers:
        parameters[:, body_count:] *= limits[None, body_count:, None]
    controls = np.linalg.lstsq(basis, parameters.reshape(len(source_local), -1), rcond=None)[0]
    controls = controls.reshape(basis.shape[1], len(editable), 3)
    recovered = np.einsum('fk,kjd->fjd', basis, controls)
    if physical_fingers:
        recovered[:, body_count:] /= limits[None, body_count:, None]
    bounded = limits[None, :, None] * recovered / np.sqrt(1 + np.sum(recovered**2, axis=-1, keepdims=True))
    error = float(np.linalg.norm(bounded-vectors, axis=-1).max())
    if error > 1e-5:
        raise ValueError('Seed cannot be represented by the original correction spline')
    return controls, dict(maximum_recovered_rotation_vector_error_rad=error,
                         original_edit_budgets_preserved=True,
                         scope='Initialization only; edits remain relative to the unchanged original clip.')
