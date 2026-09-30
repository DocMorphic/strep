"""Experimental conservative face filtering around Trimesh's nearest-vertex box.

No dependency patching. A per-query mesh proxy leaves the target mesh and ray
intersector unchanged. Not the production geometry backend.
"""
import numpy as np


def filter_faces(ids, lower, upper, centers, radii, merge_tolerance):
    ids = np.asarray(ids, dtype=np.int64)
    if len(ids) < 3: return ids
    lower, upper = np.asarray(lower, float), np.asarray(upper, float)
    midpoint = lower/2+upper/2
    # Trimesh supplied a cube containing the nearest-vertex radius. A triangle
    # that can beat that vertex has centroid distance <= radius + face radius.
    # Retain the squared-distance ambiguity band used by its two-face reducer.
    extent = float(np.max((upper-lower)/2))
    reach = np.sqrt(extent*extent+merge_tolerance)
    scale = max(1., float(np.abs(midpoint).max()), extent, float(radii[ids].max()))
    padding = 128*np.finfo(float).eps*scale
    distances = np.linalg.norm(centers[ids]-midpoint, axis=1)
    keep = distances <= reach+radii[ids]+padding
    if not np.isfinite(distances).all() or not np.isfinite(reach): return ids
    selected = ids[keep]
    # A degenerate or unexpected query must fall back, never invent no surface.
    return selected if len(selected) else ids


class FilteredTree:
    def __init__(self, original, centers, radii, tolerance):
        self.original, self.centers, self.radii, self.tolerance = original, centers, radii, tolerance
        self.raw_candidates = 0; self.retained_candidates = 0; self.queries = 0

    def _filter(self, ids, lower, upper):
        ids = np.asarray(list(ids) if not isinstance(ids, np.ndarray) else ids, dtype=np.int64)
        result = filter_faces(ids, lower, upper, self.centers, self.radii, self.tolerance)
        self.raw_candidates += len(ids); self.retained_candidates += len(result); self.queries += 1
        return result

    def intersection_v(self, lower, upper):
        ids, counts = self.original.intersection_v(lower, upper)
        groups = np.split(ids, np.cumsum(counts.astype(np.int64))[:-1])
        selected = [self._filter(group, lo, hi) for group, lo, hi in zip(groups, lower, upper)]
        return np.concatenate(selected), np.array([len(group) for group in selected], dtype=np.uint64)

    def intersection(self, bounds):
        return self._filter(self.original.intersection(bounds), bounds[:3], bounds[3:])


class ProximityMesh:
    def __init__(self, mesh, *, filter_rays=False):
        from trimesh.constants import tol
        self._mesh = mesh
        triangles = np.asarray(mesh.triangles, float)
        centers = triangles.mean(axis=1)
        radii = np.linalg.norm(triangles-centers[:, None], axis=2).max(axis=1)
        self.triangles_tree = FilteredTree(mesh.triangles_tree, centers, radii, tol.merge)
        if filter_rays: self.ray = FilteredRay(mesh)

    def __getattr__(self, name): return getattr(self._mesh, name)


def line_box_candidates(origin, direction, lower, upper, padding=1e-7):
    """Conservative infinite-line/AABB test; deliberately does not cull by t>=0."""
    origin, direction, lower, upper = map(lambda x: np.asarray(x, float), [origin, direction, lower, upper])
    if origin.shape != (3,) or direction.shape != (3,) or lower.ndim != 2 or lower.shape[1:] != (3,) or upper.shape != lower.shape:
        raise ValueError('One line and matching three-dimensional box arrays required')
    if not all(np.isfinite(x).all() for x in [origin, direction, lower, upper]) or np.any(lower > upper) or not np.isfinite(padding) or padding < 1e-7:
        raise ValueError('Finite line/boxes and conservative padding required')
    scale = max(1., float(np.abs(origin).max()), float(np.abs(lower).max(initial=0)), float(np.abs(upper).max(initial=0)))
    pad = padding+128*np.finfo(float).eps*scale
    enter = np.full(len(lower), -np.inf); leave = np.full(len(lower), np.inf)
    possible = np.ones(len(lower), bool); fallback = np.zeros(len(lower), bool)
    for axis in range(3):
        if direction[axis] == 0:
            possible &= (origin[axis] >= lower[:, axis]-pad) & (origin[axis] <= upper[:, axis]+pad)
        else:
            with np.errstate(over='ignore', invalid='ignore'):
                a = (lower[:, axis]-pad-origin[axis])/direction[axis]
                b = (upper[:, axis]+pad-origin[axis])/direction[axis]
            fallback |= ~np.isfinite(a) | ~np.isfinite(b)
            enter = np.maximum(enter, np.minimum(a, b)); leave = np.minimum(leave, np.maximum(a, b))
    return fallback | (possible & (enter <= leave))


class RayTree:
    def __init__(self, mesh, origins, directions, boxes, statistics):
        self.original = mesh.triangles_tree; self.bounds = self.original.bounds
        self.origins, self.directions = np.asarray(origins), np.asarray(directions)
        self.lower, self.upper = boxes; self.statistics = statistics; self.index = 0

    def intersection(self, bounds):
        if self.index >= len(self.origins): raise ValueError('Ray/tree query ordering changed')
        index = self.index; self.index += 1; ids = np.asarray(list(self.original.intersection(bounds)), dtype=np.int64)
        keep = line_box_candidates(self.origins[index], self.directions[index], self.lower[ids], self.upper[ids])
        self.statistics['raw_candidates'] += len(ids); self.statistics['retained_candidates'] += int(keep.sum())
        self.statistics['rays'] += 1
        return ids[keep]


class RayMesh:
    def __init__(self, mesh, tree): self.original = mesh; self.triangles_tree = tree
    def __getattr__(self, name): return getattr(self.original, name)


class FilteredRay:
    def __init__(self, mesh):
        import trimesh
        if trimesh.__version__ != '5.1.0': raise ValueError('Ray query ordering is validated only for Trimesh 5.1.0')
        self.mesh = mesh; triangles = mesh.triangles
        self.boxes = triangles.min(axis=1), triangles.max(axis=1)
        self.statistics = dict(raw_candidates=0, retained_candidates=0, rays=0)

    def contains_points(self, points):
        from trimesh.ray.ray_util import contains_points
        return contains_points(self, points)

    def intersects_location(self, ray_origins, ray_directions, **kwargs):
        from trimesh.ray.ray_triangle import RayMeshIntersector
        tree = RayTree(self.mesh, ray_origins, ray_directions, self.boxes, self.statistics)
        intersector = RayMeshIntersector(RayMesh(self.mesh, tree))
        result = intersector.intersects_location(ray_origins, ray_directions, **kwargs)
        if tree.index != len(ray_origins): raise ValueError('Incomplete ray/tree query sequence')
        return result
