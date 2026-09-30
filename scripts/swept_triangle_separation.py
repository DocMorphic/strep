"""Sufficient fixed-axis separation of triangles with per-vertex motion balls.

Axes are taken from center-pose geometry; their direction stays fixed across the
interval. Failure to find an axis is unresolved, never a collision assertion.
"""
from itertools import islice
import numpy as np
from rtree import index
from swept_surface_boxes import boxes


def pair_bounds(left, left_radii, right, right_radii, tolerance_m=1e-8, *,
                left_velocity=None, right_velocity=None, time_radius_s=None):
    a, b = np.asarray(left, float), np.asarray(right, float)
    ra, rb = np.asarray(left_radii, float), np.asarray(right_radii, float)
    if (a.ndim != 3 or a.shape[1:] != (3, 3) or not len(a) or b.shape != a.shape
            or ra.shape != a.shape[:2] or rb.shape != ra.shape):
        raise ValueError('Matching nonempty batches of triangles and vertex radii required')
    if not all(np.isfinite(v).all() for v in [a, b, ra, rb]) or np.any(ra < 0) or np.any(rb < 0):
        raise ValueError('Finite triangles and nonnegative radii required')
    if not np.isfinite(tolerance_m) or tolerance_m < 0:
        raise ValueError('Finite nonnegative separation tolerance required')
    directional = any(v is not None for v in (left_velocity, right_velocity, time_radius_s))
    if directional:
        va, vb = np.asarray(left_velocity, float), np.asarray(right_velocity, float)
        if (va.shape != a.shape or vb.shape != b.shape or not np.isfinite(va).all() or not np.isfinite(vb).all()
                or time_radius_s is None or not np.isscalar(time_radius_s)
                or not np.isfinite(time_radius_s) or time_radius_s <= 0):
            raise ValueError('Matching finite velocities and positive time radius required')
    # Translation conditioning and an explicit floating-point projection reserve.
    magnitude = np.maximum(1., np.maximum(np.abs(a).max(axis=(1, 2)), np.abs(b).max(axis=(1, 2))))
    magnitude = np.maximum(magnitude, np.maximum(ra.max(axis=1), rb.max(axis=1)))
    if directional:
        magnitude = np.maximum(magnitude, time_radius_s*np.maximum(abs(va).max(axis=(1, 2)), abs(vb).max(axis=(1, 2))))
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
    if directional:
        # Compare each of nine vertex pairs at the SAME time. Subtracting
        # velocities before projecting preserves cancellation of shared travel.
        relative = vb[:, None, :, :]-va[:, :, None, :]
        movement = abs(np.einsum('nabi,nki->nkab', relative, axes))*time_radius_s
        gap = pb[:, :, None, :]-pa[:, :, :, None]
        remainder = ar[:, :, :, None]+br[:, :, None, :]
        forward = (gap-movement-remainder).min(axis=(2, 3))
        reverse = (-gap-movement-remainder).min(axis=(2, 3))
    margin = np.maximum(forward, reverse) - (tolerance_m+reserve)[:, None]*axis_norm
    margin[~active] = -np.inf
    best = margin.argmax(axis=1); rows = np.arange(len(a)); value = margin[rows, best]
    if not np.isfinite(value).all(): raise ValueError('Nonfinite separation projection')
    sign = np.where(forward[rows, best] >= reverse[rows, best], 1., -1.)
    return dict(separated=value > 0, margin_m=value/axis_norm[rows, best],
                axes=axes[rows, best]*sign[:, None], projection_reserve_m=reserve)


def audit(left, left_faces, right, right_faces, *, candidate_limit=20000, batch_size=256, tolerance_m=1e-8,
          motion_model='balls'):
    if type(candidate_limit) is not int or not 1 <= candidate_limit <= 1000000:
        raise ValueError('One to one million candidate pairs required')
    if type(batch_size) is not int or not 1 <= batch_size <= 4096:
        raise ValueError('Batch size must be one to 4096')
    if not np.isfinite(tolerance_m) or tolerance_m < 0: raise ValueError('Invalid separation tolerance')
    for key in ['start_s', 'end_s', 'center_s']:
        if not np.isfinite(left[key]) or left[key] != right[key]: raise ValueError('Matching interval clocks required')
    if not left['start_s'] < left['center_s'] < left['end_s']: raise ValueError('Interior center required')
    if motion_model not in ('balls', 'taylor'): raise ValueError('Unknown motion bound model')
    if motion_model == 'taylor':
        for value in (left, right):
            half = value['time_radius_s']
            if half != max(value['end_s']-value['center_s'], value['center_s']-value['start_s']):
                raise ValueError('Taylor time radius must cover the matching interval')
            v, r = np.asarray(value['center_velocities']), np.asarray(value['remainder_radius_m'])
            if (v.shape != np.asarray(value['center_vertices']).shape or r.shape != (len(v),)
                    or not np.isfinite(v).all() or not np.isfinite(r).all() or np.any(r < 0)):
                raise ValueError('Finite per-vertex Taylor velocities and remainder radii required')
    alo, ahi = boxes(left, left_faces); blo, bhi = boxes(right, right_faces)
    left_faces, right_faces = np.asarray(left_faces), np.asarray(right_faces)
    a, b = np.asarray(left['center_vertices'])[left_faces], np.asarray(right['center_vertices'])[right_faces]
    ra, rb = np.asarray(left['radius_m'])[left_faces], np.asarray(right['radius_m'])[right_faces]
    if motion_model == 'taylor':
        ra, rb = np.asarray(left['remainder_radius_m'])[left_faces], np.asarray(right['remainder_radius_m'])[right_faces]
        va, vb = np.asarray(left['center_velocities'])[left_faces], np.asarray(right['center_velocities'])[right_faces]
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
                ids = np.asarray(chunk); options = {}
                if motion_model == 'taylor':
                    options = dict(left_velocity=va[ids[:, 0]], right_velocity=vb[ids[:, 1]], time_radius_s=left['time_radius_s'])
                result = pair_bounds(a[ids[:, 0]], ra[ids[:, 0]], b[ids[:, 1]], rb[ids[:, 1]], tolerance_m, **options)
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
        scope='Sufficient fixed-axis projection separation under supplied motion bounds and numerical reserves. Unchecked or unseparated pairs remain unresolved. No containment, self-collision, exact-arithmetic or quality certification.')
