"""Necessary angular bound for fixed surfaces and one common rigid target pose."""
import numpy as np


def angles(vectors):
    """Pairwise direction angles; atan2 remains stable near 0 and 180 degrees."""
    dot = vectors @ vectors.T
    cross = np.cross(vectors[:, None, :], vectors[None, :, :])
    return np.rad2deg(np.arctan2(np.linalg.norm(cross, axis=2), dot))


def bound(source_normals, target_local_normals, maximum_error_degrees):
    """Sources have shape [frames, points, 3]; all targets share one rigid frame.

    If e_i is the opposition error at point i, angle invariance and the
    spherical triangle inequality imply |a_ij - b_ij| <= e_i + e_j.
    Half the largest pairwise spread difference bounds the maximum error.
    This is necessary only; satisfying it does not construct a proper rotation.
    """
    source = np.asarray(source_normals, float)
    target = np.asarray(target_local_normals, float)
    if (source.ndim != 3 or source.shape[2] != 3 or not 1 <= source.shape[0] <= 20000
            or not 1 <= source.shape[1] <= 256 or target.shape != source.shape[1:]
            or not np.isfinite(source).all() or not np.isfinite(target).all()
            or np.any(abs(np.linalg.norm(source, axis=2)-1) > 1e-8)
            or np.any(abs(np.linalg.norm(target, axis=1)-1) > 1e-8)):
        raise ValueError('Complete finite unit-normal frames and one matching local target population required')
    if (type(maximum_error_degrees) not in (int, float) or not np.isfinite(maximum_error_degrees)
            or not 0 <= maximum_error_degrees <= 180):
        raise ValueError('Explicit finite maximum opposition error required')
    target_spread = angles(target)
    lower = []; pairs = []; source_witness = []; target_witness = []
    for frame in source:
        spread = angles(frame)
        difference = abs(spread-target_spread)/2
        # Self-pairs cannot constrain a rotation; exclude them explicitly.
        np.fill_diagonal(difference, 0)
        if len(target) == 1:
            i = j = -1; value = sa = ta = 0.
        else:
            upper = np.triu_indices(len(target), k=1)
            peak = difference[upper].argmax()
            i,j = upper[0][peak],upper[1][peak]
            value = float(difference[i,j]); sa = float(spread[i,j]); ta = float(target_spread[i,j])
        lower.append(value); pairs.append([int(i),int(j)]); source_witness.append(sa); target_witness.append(ta)
    lower = np.asarray(lower); rejected = lower > maximum_error_degrees
    return (dict(frames=len(source),points=len(target),maximum_error_degrees=maximum_error_degrees,
        maximum_necessary_error_degrees=float(lower.max()),minimum_frame_lower_bound_degrees=float(lower.min()),
        rejected_frames=int(rejected.sum()),all_frames_not_rejected=bool(not rejected.any()),
        necessary_condition_only=True,rigid_rotation_feasibility_proven=False,
        source_surface_changes_allowed=False,translation_cannot_change_normal_spread=True,
        continuous_time_certified=False,formal_interval_certificate=False,quality_approved=False,release_approved=False,
        scope='Floating necessary condition at every supplied frame for fixed source directions and fixed target normals sharing one common rigid pose. '
            'Object translations and common rotations preserve target spread. Not rejection of body edits, new correspondences, different conditions or all possible motion.'),
        dict(lower_bound_degrees=lower,witness_pairs=np.asarray(pairs),source_pair_degrees=np.asarray(source_witness),
            target_pair_degrees=np.asarray(target_witness),rejected=rejected))
