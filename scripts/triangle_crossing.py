"""Discrete surface crossing diagnostic; supplements vertex containment tests.

Plane/interval construction follows the geometry described by Moller (1997),
doi:10.1080/10867651.1997.10487472. Independent NumPy implementation; no upstream
code copied. Boundary, coplanar and degenerate cases remain separate outcomes.
"""
from collections import Counter
import numpy as np
from rtree import index


def _interval(triangle, distances, direction, tolerance):
    points = [triangle[i] for i in range(3) if abs(distances[i]) <= tolerance]
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        if distances[i] * distances[j] < 0:
            t = distances[i] / (distances[i] - distances[j])
            points.append(triangle[i] + t * (triangle[j] - triangle[i]))
    if not points:
        return None
    values = np.asarray(points) @ direction
    return float(values.min()), float(values.max())


def classify(left, right, tolerance_m=1e-8):
    """Classify a triangle pair. Overlap length is not penetration depth."""
    a, b = np.asarray(left, float), np.asarray(right, float)
    if a.shape != (3, 3) or b.shape != (3, 3) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Finite triangles of shape (3,3) required')
    if not np.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError('Positive finite distance tolerance required')
    eps = float(tolerance_m)
    origin = a[0].copy()
    a, b = a - origin, b - origin
    na, nb = np.cross(a[1]-a[0], a[2]-a[0]), np.cross(b[1]-b[0], b[2]-b[0])
    la, lb = np.linalg.norm(na), np.linalg.norm(nb)
    if min(la, lb) <= eps * eps:
        return dict(kind='degenerate', overlap_length_m=None)
    na, nb = na / la, nb / lb
    da, db = (a-b[0]) @ nb, (b-a[0]) @ na
    if any(d.min() > eps or d.max() < -eps for d in [da, db]):
        return dict(kind='disjoint', overlap_length_m=0.)
    direction = np.cross(na, nb)
    length = np.linalg.norm(direction)
    if length <= 1e-10:
        # Parallel planes within the distance tolerance: use 2D separating axes.
        axes = [i for i in range(3) if i != int(np.abs(na).argmax())]
        aa, bb = a[:, axes], b[:, axes]
        minimum = np.inf
        for triangle in [aa, bb]:
            for i, j in [(0, 1), (1, 2), (2, 0)]:
                edge = triangle[j]-triangle[i]
                axis = np.array([-edge[1], edge[0]])
                norm = np.linalg.norm(axis)
                if norm <= eps:
                    continue
                pa, pb = aa @ (axis/norm), bb @ (axis/norm)
                overlap = min(pa.max(), pb.max()) - max(pa.min(), pb.min())
                if overlap < -eps:
                    return dict(kind='disjoint', overlap_length_m=0.)
                minimum = min(minimum, overlap)
        return dict(kind='coplanar_or_near_parallel_overlap' if minimum > eps else 'boundary_or_near_contact',
                    overlap_length_m=None)
    direction /= length
    ia, ib = _interval(a, da, direction, eps), _interval(b, db, direction, eps)
    if ia is None or ib is None:
        return dict(kind='boundary_or_near_contact', overlap_length_m=None)
    overlap = min(ia[1], ib[1]) - max(ia[0], ib[0])
    if overlap < -eps:
        return dict(kind='disjoint', overlap_length_m=0.)
    straddles = all(d.min() < -eps and d.max() > eps for d in [da, db])
    return dict(kind='proper_crossing' if straddles and overlap > eps else 'boundary_or_near_contact',
                overlap_length_m=float(max(overlap, 0.)))


def _mesh(vertices, faces):
    v, f = np.asarray(vertices, float), np.asarray(faces)
    if v.ndim != 2 or v.shape[1] != 3 or not len(v) or not np.isfinite(v).all():
        raise ValueError('Finite nonempty vertex array required')
    if f.ndim != 2 or f.shape[1] != 3 or not len(f) or not np.issubdtype(f.dtype, np.integer):
        raise ValueError('Nonempty integer triangle indices required')
    if f.min() < 0 or f.max() >= len(v):
        raise ValueError('Triangle index out of range')
    return v[f]


def audit(left_vertices, left_faces, right_vertices, right_faces, tolerance_m=1e-8, progress=None):
    """Stream all overlapping triangle boxes; no candidate truncation or NxM array."""
    if not np.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError('Positive finite distance tolerance required')
    left, right = _mesh(left_vertices, left_faces), _mesh(right_vertices, right_faces)
    lo, hi = right.min(axis=1), right.max(axis=1)
    properties = index.Property()
    properties.dimension = 3
    tree = index.Index(((i, (*low, *high), None) for i, (low, high) in enumerate(zip(lo, hi))), properties=properties)
    counts, records, pairs = Counter(), [], 0
    try:
        for i, triangle in enumerate(left):
            bounds = (*(triangle.min(axis=0)-tolerance_m), *(triangle.max(axis=0)+tolerance_m))
            for j in sorted(tree.intersection(bounds)):
                value = classify(triangle, right[j], tolerance_m)
                counts[value['kind']] += 1
                pairs += 1
                if value['kind'] != 'disjoint':
                    records.append(dict(left_triangle=i, right_triangle=int(j), **value))
            if progress and (i+1) % 2000 == 0:
                progress(dict(left_faces_processed=i+1, left_faces_total=len(left), candidate_pairs=pairs))
    finally:
        tree.close()
    degenerate = [np.flatnonzero(np.linalg.norm(np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0]), axis=1) <= tolerance_m**2).tolist()
                  for t in [left, right]]
    return dict(left_faces=len(left), right_faces=len(right), candidate_pairs=pairs,
                counts=dict(counts), records=records, degenerate_faces=degenerate, tolerance_m=tolerance_m,
                quality_approved=False, collision_free_certified=False,
                scope='Discrete triangle-surface diagnostic. Proper crossings are transverse interior intersections; '
                'boundary/near/coplanar outcomes remain separate. No depth, enclosed-volume, self-collision, '
                'continuous-time, exact-arithmetic or animation-quality certification. Retain vertex containment checks.')
