"""Compare imported bind/weight data without assuming preserved vertex order."""
import numpy as np
from scipy.spatial import cKDTree


def compare_surface(source_positions, source_weights, joint_names, inverse_binds, observed):
    positions, weights = np.asarray(source_positions, float), np.asarray(source_weights, float)
    found = np.asarray(observed['positions'], float)
    bind_matrices = np.asarray([b['pose'] for b in observed['binds']], float)
    if positions.ndim != 2 or positions.shape[1] != 3 or weights.shape != (len(positions), len(joint_names)):
        raise ValueError('Source geometry/weights dimensions differ')
    if found.ndim != 2 or found.shape[1] != 3 or not len(found) or bind_matrices.shape != (len(observed['binds']), 4, 3):
        raise ValueError('Imported geometry/binds dimensions differ')
    if len(set(joint_names)) != len(joint_names): raise ValueError('Unique joint names required')
    bind_names = [b['bone'] for b in observed['binds']]
    if len(bind_names) != len(joint_names) or set(bind_names) != set(joint_names): raise ValueError('Imported bind mapping differs')
    order = [joint_names.index(n) for n in bind_names]
    inverse_binds = np.asarray(inverse_binds, float)
    if inverse_binds.shape != (len(joint_names), 4, 4): raise ValueError('Source inverse bind dimensions differ')
    bind_error = max(float(np.abs(bind_matrices[:, :3].transpose(0,2,1)-inverse_binds[order, :3, :3]).max()),
                     float(np.abs(bind_matrices[:, 3]-inverse_binds[order, :3, 3]).max()))
    imported_weights = np.asarray(observed['weights'], float)
    imported_bones = np.asarray(observed['bones'])
    if imported_weights.ndim != 1 or imported_bones.shape != imported_weights.shape or len(imported_weights)%len(found):
        raise ValueError('Imported influences dimensions differ')
    influences = len(imported_weights)//len(found)
    if influences not in (4,8) or not np.issubdtype(imported_bones.dtype, np.integer): raise ValueError('Invalid imported influence layout')
    imported_bones = imported_bones.reshape(len(found), influences)
    imported_weights = imported_weights.reshape(len(found), influences)
    if imported_bones.min() < 0 or imported_bones.max() >= len(bind_names) or np.any(imported_weights < 0): raise ValueError('Invalid imported weights/bind indices')
    if any(not np.isfinite(v).all() for v in (positions, weights, found, bind_matrices, inverse_binds, imported_weights)):
        raise ValueError('Non-finite skin evidence')
    effective = np.zeros((len(found), len(joint_names)))
    for column in range(influences):
        np.add.at(effective, (np.arange(len(found)), np.asarray(order)[imported_bones[:, column]]), imported_weights[:, column])
    tree = cKDTree(positions); distances = tree.query(found)[0]
    candidates = tree.query_ball_point(found, 1e-6)
    errors, used, unmatched = [], set(), 0
    # Coincident source positions can have different weights: evaluate every
    # candidate, retaining the closest influence vector, rather than first hit.
    for row, options in enumerate(candidates):
        if not options: unmatched += 1; continue
        values = np.max(np.abs(weights[options]-effective[row]), axis=1)
        best = float(values.min()); errors.append(best)
        used.update(options[i] for i in np.flatnonzero(values <= 1/65535+1e-7))
    maximum_weight_error = max(errors) if errors else None
    coverage = len(used) == len(positions)
    return dict(imported_vertices=len(found), source_vertices=len(positions), influences= influences,
        maximum_rest_position_error_m=float(distances.max()), maximum_bind_matrix_error=bind_error,
        maximum_effective_weight_error=maximum_weight_error, unmatched_vertices=unmatched, source_vertex_coverage=coverage,
        maximum_weight_sum_error=float(np.abs(imported_weights.sum(axis=1)-1).max()),
        passed=bool(not unmatched and distances.max() <= 1e-6 and bind_error <= 1e-5 and maximum_weight_error is not None and maximum_weight_error <= 1/65535+1e-7 and coverage))
