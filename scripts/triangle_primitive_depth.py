"""Whole-triangle penetration into analytic rigid primitives at one instant.

Depth is the maximum negative analytic signed distance on a triangle. It is
not overlap volume, mesh containment, continuous collision or exact arithmetic.
Box/cylinder depth levels are eroded solids; intersect them with the triangle
and bisect the level. Sphere depth uses the closest triangle point directly.
"""
import numpy as np
from object_geometry import Geometry, finite


def clip(polygon, axis, sign, limit):
    """Clip a convex polygon to sign*x[axis] <= limit, preserving 3D points."""
    result = []
    if not len(polygon): return np.empty((0, 3))
    previous = polygon[-1]; a = sign * previous[axis] - limit
    for current in polygon:
        b = sign * current[axis] - limit
        if (a <= 0) != (b <= 0):
            result.append(previous + (current - previous) * (a / (a - b)))
        if b <= 0: result.append(current)
        previous, a = current, b
    return np.asarray(result).reshape(-1, 3)


def radial_nearest(polygon):
    """Closest projected XZ point to zero, with its original 3D witness."""
    if not len(polygon): return None
    projected = polygon[:, [0, 2]]; best = polygon[0]; distance = np.linalg.norm(projected[0])
    for i in range(len(polygon)):
        a, b = projected[i - 1], projected[i]; direction = b - a
        size = direction @ direction
        t = np.clip(-a @ direction / size, 0., 1.) if size else 0.
        point = polygon[i - 1] + t * (polygon[i] - polygon[i - 1])
        value = np.linalg.norm(point[[0, 2]])
        if value < distance: distance, best = value, point
    # Edge distances handle point/line projections. For an area projection,
    # test the convex fan and reconstruct a point on the original polygon.
    for i in range(1, len(polygon) - 1):
        matrix = np.column_stack((projected[i] - projected[0], projected[i + 1] - projected[0]))
        if abs(np.linalg.det(matrix)) <= 1e-24: continue
        uv = np.linalg.solve(matrix, -projected[0])
        if uv.min() >= 0 and uv.sum() <= 1:
            point = polygon[0] + uv[0] * (polygon[i] - polygon[0]) + uv[1] * (polygon[i + 1] - polygon[0])
            value = np.linalg.norm(point[[0, 2]])
            if value < distance: distance, best = value, point
    return best


def level_witness(triangle, geometry, depth):
    polygon = triangle
    if geometry.shape == 'box':
        half = np.asarray(geometry.dimensions) / 2 - depth
        for axis in range(3):
            for sign in (-1, 1): polygon = clip(polygon, axis, sign, half[axis])
        return polygon.mean(axis=0) if len(polygon) else None
    radius, height = geometry.dimensions
    polygon = clip(clip(polygon, 1, -1, height / 2 - depth), 1, 1, height / 2 - depth)
    point = radial_nearest(polygon)
    return point if point is not None and np.linalg.norm(point[[0, 2]]) <= radius - depth else None


def closest_origin(triangle):
    """Triangle-plane projection when interior, otherwise its closest edge."""
    a, b, c = triangle; e, f = b - a, c - a
    normal = np.cross(e, f); square = normal @ normal
    if square:
        projected = normal * (normal @ a / square)
        matrix = np.column_stack((e, f))
        uv = np.linalg.lstsq(matrix, projected - a, rcond=None)[0]
        if uv.min() >= 0 and uv.sum() <= 1: return projected
    best, distance = a, np.linalg.norm(a)
    for left, right in ((a, b), (b, c), (c, a)):
        direction = right - left; size = direction @ direction
        t = np.clip(-left @ direction / size, 0., 1.) if size else 0.
        point = left + t * direction; value = np.linalg.norm(point)
        if value < distance: best, distance = point, value
    return best


def query(triangles, geometry, position, rotation, *, resolution_m=1e-6):
    """Return per-face depth brackets and witnesses, without dropping faces.

    The brackets include a reported floating-point reserve, not a rigorous
    outward-rounded proof. Faces at/below that degeneracy scale remain marked
    unresolved. Callers must also check actor-volume containment separately.
    """
    if not isinstance(geometry, Geometry): raise ValueError('Analytic Geometry required')
    triangles = np.asarray(triangles, dtype=float)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not len(triangles) or not np.isfinite(triangles).all():
        raise ValueError('Finite nonempty Nx3x3 triangle array required')
    if type(resolution_m) not in (int, float) or not np.isfinite(resolution_m) or not 1e-9 <= resolution_m <= .01:
        raise ValueError('Depth resolution must be between 1e-9 and .01 metres')
    position = finite(position, (3,), 'position'); rotation = finite(rotation, (3, 3), 'rotation')
    geometry.world_half_extents(rotation)  # Validate proper rigid rotation.
    local = (triangles - position) @ rotation
    scale = max(float(abs(triangles).max()), float(abs(position).max()), geometry.bounding_radius(), 1.)
    reserve = 256 * np.finfo(float).eps * scale
    if reserve > resolution_m / 4: raise ValueError('Coordinate magnitude exceeds declared depth resolution')
    degenerate = np.linalg.norm(np.cross(local[:, 1] - local[:, 0], local[:, 2] - local[:, 0]), axis=1) <= reserve**2
    half = geometry.local_size() / 2
    candidates = np.all(local.min(axis=1) <= half + reserve, axis=1) & np.all(local.max(axis=1) >= -half - reserve, axis=1)
    lower = np.zeros(len(local)); upper = np.zeros(len(local)); witnesses = local[:, 0].copy()
    inradius = min(geometry.dimensions) / 2 if geometry.shape == 'box' else (
        geometry.dimensions[0] if geometry.shape == 'sphere' else min(geometry.dimensions[0], geometry.dimensions[1] / 2))
    for i in np.flatnonzero(candidates):
        triangle = local[i]
        if geometry.shape == 'sphere':
            point = closest_origin(triangle); depth = max(0., inradius - np.linalg.norm(point))
            lower[i], upper[i], witnesses[i] = max(0., depth - reserve), min(inradius, depth + reserve), point
            continue
        point = level_witness(triangle, geometry, 0.)
        if point is None:
            # Numerical clipping is not an exact-arithmetic separation proof.
            upper[i] = reserve
            continue
        lo, hi = 0., inradius; witnesses[i] = point
        while hi - lo > resolution_m / 2:
            mid = (lo + hi) / 2; point = level_witness(triangle, geometry, mid)
            if point is None: hi = mid
            else: lo, witnesses[i] = mid, point
        # Independently evaluate the analytic SDF at the constructed witness.
        depth = geometry.penetration_depth(witnesses[i:i+1], np.zeros(3), np.eye(3))[0]
        lower[i] = max(0., min(lo, depth) - reserve)
        upper[i] = min(inradius, hi + reserve)
        if depth + resolution_m < lo: raise ValueError('Eroded-level witness contradicts analytic distance')
    return dict(lower_m=lower, upper_m=upper, witnesses_world_m=witnesses @ rotation.T + position,
                candidate_faces=candidates, degenerate_faces=np.flatnonzero(degenerate),
                resolution_m=float(resolution_m), floating_reserve_m=float(reserve),
                exact_arithmetic_certified=False, continuous_collision_certified=False)
