"""Necessary angular bound for one rigid rotation of a normal field.

A passing bound is not a feasible rotation, nor a contact/motion certificate.
Skin deformation can change pair distances and is outside this hypothesis.
"""
import numpy as np


def pairwise_bound(source, target, *, maximum_pairs=4096):
    """Return per-frame lower bounds in degrees, with the maximizing pair.

    If every rotated source normal is within theta of its opposing target,
    triangle inequalities imply |d(source_i,source_j)-d(target_i,target_j)|
    <= 2 theta. Negating all target normals preserves these pair distances.
    Arrays are complete caller-selected populations, shape (frames, points, 3).
    This is floating-point diagnostic arithmetic, not interval certification.
    """
    if type(maximum_pairs) is not int or not 1 <= maximum_pairs <= 65536:
        raise ValueError('Explicit finite pair budget required')
    a, b = np.asarray(source, float), np.asarray(target, float)
    if (a.ndim != 3 or a.shape != b.shape or a.shape[2] != 3
            or not len(a) or a.shape[1] < 2 or not np.isfinite(a).all()
            or not np.isfinite(b).all()):
        raise ValueError('Complete matching finite normal populations required')
    count = a.shape[1] * (a.shape[1] - 1) // 2
    if count > maximum_pairs:
        raise ValueError('Complete pair population exceeds budget; no subset returned')
    if (np.max(abs(np.linalg.norm(a, axis=2) - 1)) > 1e-8
            or np.max(abs(np.linalg.norm(b, axis=2) - 1)) > 1e-8):
        raise ValueError('Unit normals required; missing normals are not inferred')
    pairs = np.asarray([(i, j) for i in range(a.shape[1]) for j in range(i + 1, a.shape[1])])

    def distance(normals):
        left, right = normals[:, pairs[:, 0]], normals[:, pairs[:, 1]]
        return np.rad2deg(np.arctan2(np.linalg.norm(np.cross(left, right), axis=2),
                                    np.einsum('fpi,fpi->fp', left, right)))

    differences = abs(distance(a) - distance(b)) / 2
    largest = np.argmax(differences, axis=1)
    return dict(lower_bound_degrees=differences[np.arange(len(a)), largest],
                maximizing_pair=pairs[largest], all_pair_bounds_degrees=differences,
                pair_indices=pairs, necessary_only=True, rotation_found=False,
                skin_deformation_ruled_out=False, quality_approved=False)
