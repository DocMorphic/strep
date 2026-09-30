"""Sufficient fixed-axis separation of triangles with per-vertex motion balls.

Axes are taken from center-pose geometry; their direction stays fixed across the
interval. Failure to find an axis is unresolved, never a collision assertion.
"""
from itertools import islice
import numpy as np
from rtree import index
from swept_surface_boxes import boxes


def pair_bounds(left, left_radii, right, right_radii, tolerance_m=1e-8):
    a, b = np.asarray(left, float), np.asarray(right, float)
    ra, rb = np.asarray(left_radii, float), np.asarray(right_radii, float)
    if (a.ndim != 3 or a.shape[1:] != (3, 3) or not len(a) or b.shape != a.shape
            or ra.shape != a.shape[:2] or rb.shape != ra.shape):
        raise ValueError('Matching nonempty batches of triangles and vertex radii required')
    if not all(np.isfinite(v).all() for v in [a, b, ra, rb]) or np.any(ra < 0) or np.any(rb < 0):
        raise ValueError('Finite triangles and nonnegative radii required')
    if not np.isfinite(tolerance_m) or tolerance_m < 0:
        raise ValueError('Finite nonnegative separation tolerance required')
    # Translation conditioning and an explicit floating-point projection reserve.
    magnitude = np.maximum(1., np.maximum(np.abs(a).max(axis=(1, 2)), np.abs(b).max(axis=(1, 2))))
    magnitude = np.maximum(magnitude, np.maximum(ra.max(axis=1), rb.max(axis=1)))
    reserve = 128*np.finfo(float).eps*magnitude
    origin = a[:, :1].copy(); a, b = a-origin, b-origin
    ea, eb = np.roll(a, -1, axis=1)-a, np.roll(b, -1, axis=1)-b
    na, nb = np.cross(ea[:, 0], -ea[:, 2]), np.cross(eb[:, 0], -eb[:, 2])
    axes = np.concatenate([np.broadcast_to(np.eye(3), (len(a), 3, 3)), na[:, None], nb[:, None],
        np.cross(ea[:, :, None], eb[:, None, :]).reshape(-1, 9, 3),
        np.cross(na[:, None], ea), np.cross(nb[:, None], eb)], axis=1)
    norms = np.linalg.norm(axes, axis=2)
    if not np.isfinite(axes).all() or not np.isfinite(norms).all(): raise ValueError('Projection axis overflow')
    active = norms > np.finfo(float).tiny
    axes = axes/np.where(active, norms, 1.)[:, :, None]
    # Use the computed axis norm, rather than assuming normalization is exact.
    axis_norm = np.linalg.norm(axes, axis=2)
    pa, pb = np.einsum('nvi,nki->nkv', a, axes), np.einsum('nvi,nki->nkv', b, axes)
    ar, br = ra[:, None]*axis_norm[:, :, None], rb[:, None]*axis_norm[:, :, None]
    forward = (pb-br).min(axis=2)-(pa+ar).max(axis=2)
    reverse = (pa-ar).min(axis=2)-(pb+br).max(axis=2)
    margin = np.maximum(forward, reverse) - (tolerance_m+reserve)[:, None]*axis_norm
    margin[~active] = -np.inf
    best = margin.argmax(axis=1); rows = np.arange(len(a)); value = margin[rows, best]
    if not np.isfinite(value).all(): raise ValueError('Nonfinite separation projection')
    sign = np.where(forward[rows, best] >= reverse[rows, best], 1., -1.)
    return dict(separated=value > 0, margin_m=value/axis_norm[rows, best],
                axes=axes[rows, best]*sign[:, None], projection_reserve_m=reserve)


def audit(left, left_faces, right, right_faces, *, candidate_limit=20000, batch_size=256, tolerance_m=1e-8):
    if type(candidate_limit) is not int or not 1 <= candidate_limit <= 1000000:
        raise ValueError('One to one million candidate pairs required')
    if type(batch_size) is not int or not 1 <= batch_size <= 4096:
        raise ValueError('Batch size must be one to 4096')
    if not np.isfinite(tolerance_m) or tolerance_m < 0: raise ValueError('Invalid separation tolerance')
    for key in ['start_s', 'end_s', 'center_s']:
        if not np.isfinite(left[key]) or left[key] != right[key]: raise ValueError('Matching interval clocks required')
    if not left['start_s'] < left['center_s'] < left['end_s']: raise ValueError('Interior center required')
    alo, ahi = boxes(left, left_faces); blo, bhi = boxes(right, right_faces)
    left_faces, right_faces = np.asarray(left_faces), np.asarray(right_faces)
    a, b = np.asarray(left['center_vertices'])[left_faces], np.asarray(right['center_vertices'])[right_faces]
    ra, rb = np.asarray(left['radius_m'])[left_faces], np.asarray(right['radius_m'])[right_faces]
    properties = index.Property(); properties.dimension = 3
    tree = index.Index(((i, (*lo, *hi), None) for i, (lo, hi) in enumerate(zip(blo, bhi))), properties=properties)
    checked = 0; minimum = None; unresolved = []; total = 0
    try:
        queries = [(*(lo-tolerance_m), *(hi+tolerance_m)) for lo, hi in zip(alo, ahi)]
        total = sum(tree.count(query) for query in queries)
        if total <= candidate_limit:
            pairs = ((i, int(j)) for i, query in enumerate(queries) for j in tree.intersection(query))
            while True:
                chunk = list(islice(pairs, batch_size))
                if not chunk: break
                ids = np.asarray(chunk); result = pair_bounds(a[ids[:, 0]], ra[ids[:, 0]], b[ids[:, 1]], rb[ids[:, 1]], tolerance_m)
                checked += len(ids); value = float(result['margin_m'].min())
                minimum = value if minimum is None else min(minimum, value)
                unresolved.extend(dict(left_triangle=int(i), right_triangle=int(j), best_margin_m=float(m))
                    for (i, j), m, ok in zip(ids, result['margin_m'], result['separated']) if not ok)
                if unresolved: break
    finally:
        tree.close()
    separated = total == checked and not unresolved
    return dict(start_s=left['start_s'], end_s=left['end_s'], candidate_pairs=int(total), checked_pairs=checked,
        untested_pairs=int(total-checked), candidate_limit=candidate_limit, minimum_tested_margin_m=minimum,
        unresolved_examples=unresolved[:16], outcome='surface_separation_bound' if separated else 'unresolved',
        reason='all_swept_pairs_separated' if separated else ('candidate_budget' if total > candidate_limit else 'no_separating_axis'),
        collision_free_certified=False, quality_approved=False,
        scope='Sufficient fixed-axis projection separation under supplied vertex-radius bounds and numerical reserves. Unchecked or unseparated pairs remain unresolved. No containment, self-collision, exact-arithmetic or quality certification.')
