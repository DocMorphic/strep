"""Continuous-interval broad phase from skin speed bounds, never a depth test."""
import numpy as np
from rtree import index
from itertools import islice


def boxes(bound, faces):
    points = np.asarray(bound['center_vertices'], float); radius = np.asarray(bound['radius_m'], float)
    faces = np.asarray(faces)
    if (points.ndim != 2 or points.shape[1:] != (3,) or not len(points) or radius.shape != (len(points),)
            or not np.isfinite(points).all() or not np.isfinite(radius).all() or np.any(radius < 0)):
        raise ValueError('Finite matching center vertices and nonnegative radii required')
    if faces.ndim != 2 or faces.shape[1:] != (3,) or not len(faces) or faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(points):
        raise ValueError('Valid nonempty triangle indices required')
    return ((points-radius[:, None])[faces].min(axis=1),
            (points+radius[:, None])[faces].max(axis=1))


def audit(left, left_faces, right, right_faces, tolerance_m=1e-8):
    if not np.isfinite(tolerance_m) or tolerance_m < 0:
        raise ValueError('Finite nonnegative broad-phase padding required')
    for key in ['start_s', 'end_s', 'center_s']:
        if not np.isfinite(left[key]) or left[key] != right[key]:
            raise ValueError('Matching interval clocks required')
    if not left['start_s'] < left['center_s'] < left['end_s']:
        raise ValueError('Interior center time required')
    alo, ahi = boxes(left, left_faces); blo, bhi = boxes(right, right_faces)
    properties = index.Property(); properties.dimension = 3
    tree = index.Index(((i, (*lo, *hi), None) for i, (lo, hi) in enumerate(zip(blo, bhi))), properties=properties)
    count = 0; examples = []
    try:
        for i, (lo, hi) in enumerate(zip(alo, ahi)):
            bounds = (*(lo-tolerance_m), *(hi+tolerance_m))
            count += int(tree.count(bounds))
            if len(examples) < 16:
                examples.extend([i, int(j)] for j in islice(tree.intersection(bounds), 16-len(examples)))
    finally:
        tree.close()
    return dict(start_s=left['start_s'], end_s=left['end_s'], candidate_pairs=count,
        example_pairs=examples, examples_truncated=count > len(examples),
        outcome='surface_separation_bound' if count == 0 else 'unresolved',
        collision_free_certified=False, quality_approved=False,
        scope='All triangle box pairs considered using supplied interval radii. Zero pairs bounds surface separation only; containment, self-intersection, invalid bounds and floating-point predicate error are not certified. Nonzero pairs do not prove collision.')
