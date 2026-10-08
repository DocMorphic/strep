"""Necessary reach condition for unchanged linear-blend skin and joint budgets.

A lower bound above a requested tolerance proves a conflict. A zero lower bound
does not prove feasibility. No anatomy, joint coupling or speed is modeled.
"""
import numpy as np


def error_lower_bound(positions, rotations, local_points, weights, targets, budget_m):
    if type(budget_m) not in (int, float) or not np.isfinite(budget_m) or budget_m < 0:
        raise ValueError('Nonnegative finite native joint-position budget required')
    arrays = [np.asarray(value) for value in (positions, rotations, local_points, weights, targets)]
    if any(value.dtype.kind not in 'fi' or not np.isfinite(value).all() for value in arrays):
        raise ValueError('Finite numeric skin/reference/target arrays required')
    p, r, local, w, target = [value.astype(np.float64, copy=False) for value in arrays]
    if (p.ndim != 3 or p.shape[0] < 1 or p.shape[1] < 1 or p.shape[2] != 3
            or r.shape != p.shape[:2]+(3, 3) or local.shape != (p.shape[1], 3)
            or w.shape != (p.shape[1],) or target.shape != (p.shape[0], 3)):
        raise ValueError('Matching frame, influence and XYZ populations required')
    if (w < 0).any() or w.sum() <= 0:
        raise ValueError('Original nonnegative skin weights with positive sum required')
    # Any new proper rotation has operator norm one. Use the actual raw matrix
    # norm, including its float rounding, rather than assuming it equals one.
    raw_norm = np.linalg.svd(r, compute_uv=False)[..., 0]
    radius = np.linalg.norm(local, axis=1)
    movement = budget_m*w.sum()+np.sum(w*radius*(1+raw_norm), axis=1)
    source = np.sum((np.einsum('fnij,nj->fni', r, local)+p)*w[None, :, None], axis=1)
    # Conservative arithmetic slack; a proof needs a positive bound even after
    # this slack. It is not an engine export or numerical error certificate.
    lower = np.maximum(0., np.linalg.norm(source-target, axis=1)-movement-1e-6)
    if not np.isfinite(lower).all() or not np.isfinite(movement).all():
        raise ValueError('Skin reach arithmetic must stay finite')
    return dict(error_lower_bound_m=lower, point_movement_upper_bound_m=movement,
                original_point_m=source, arithmetic_slack_m=1e-6)
