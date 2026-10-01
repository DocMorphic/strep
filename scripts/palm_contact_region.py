"""Explicit surface-distance contact region and conservative support candidates."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import ConvexHull


def rebind_surface_point(item, vertex):
    """Discard cached geometry for the old vertex when authoring a new point."""
    if (not isinstance(item, dict) or not isinstance(item.get('joint'), str)
            or type(vertex) is not int or vertex < 0 or item.get('space', 'actor') != 'actor'):
        raise ValueError('Actor surface joint and nonnegative integer vertex required')
    result = {k: item[k] for k in ('joint', 'space', 'actor') if k in item}
    result.update(surface_vertex=vertex, label='support candidate in declared palm region', status='anatomical_review_pending')
    return result


def region(points, faces, seed, radius_m, facing_degrees=60.):
    points, faces = np.asarray(points, float), np.asarray(faces)
    if (points.ndim != 2 or points.shape[1:] != (3,) or not len(points) or not np.isfinite(points).all()
            or faces.ndim != 2 or faces.shape[1:] != (3,) or not len(faces)
            or not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0 or faces.max() >= len(points)
            or type(seed) is not int or seed not in faces or not np.isfinite(radius_m) or radius_m <= 0
            or not np.isfinite(facing_degrees) or not 0 <= facing_degrees < 90):
        raise ValueError('Finite indexed surface, seed, positive radius and front-facing cone required')
    triangles = points[faces]; area_normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    if np.any(np.linalg.norm(area_normals, axis=1) <= 1e-16): raise ValueError('Nondegenerate region triangles required')
    normals = np.zeros_like(points)
    for i in range(3): np.add.at(normals, faces[:, i], area_normals)
    lengths = np.linalg.norm(normals, axis=1)
    if lengths[seed] <= 1e-12: raise ValueError('Unambiguous seed surface normal required')
    normals /= np.maximum(lengths[:, None], 1e-15)
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    costs = np.linalg.norm(points[edges[:, 0]]-points[edges[:, 1]], axis=1)
    if np.any(costs <= 0): raise ValueError('Positive surface edge lengths required')
    graph = coo_matrix((np.tile(costs, 2), (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])), shape=(len(points), len(points))).tocsr()
    distance = dijkstra(graph, directed=False, indices=seed, limit=radius_m)
    ids = np.flatnonzero((distance <= radius_m) & (lengths > 1e-12) & (normals@normals[seed] >= np.cos(np.deg2rad(facing_degrees))-1e-12))
    return ids, distance, normals


def candidates(points, faces, seed, radius_m, facing_degrees=60., normal_tolerance_degrees=20.):
    points, faces = np.asarray(points, float), np.asarray(faces)
    if not np.isfinite(normal_tolerance_degrees) or not 0 <= normal_tolerance_degrees < 90:
        raise ValueError('Explicit normal tolerance below ninety degrees required')
    ids, distance, normals = region(points, faces, seed, radius_m, facing_degrees)
    hand_ids = np.unique(faces); hull = ConvexHull(points[hand_ids]); allowed = set(ids.tolist()); best = {}
    for simplex, equation in zip(hull.simplices, hull.equations):
        direction = equation[:3]/np.linalg.norm(equation[:3])
        for vertex in hand_ids[simplex]:
            vertex = int(vertex)
            if vertex not in allowed: continue
            angle = float(np.rad2deg(np.arccos(np.clip(normals[vertex]@direction, -1., 1.))))
            if angle > normal_tolerance_degrees: continue
            excess = float(((points[hand_ids]-points[vertex])@direction).max())
            if excess > 1e-8: continue
            row = dict(vertex=vertex, surface_distance_m=float(distance[vertex]), support_normal=direction.tolist(),
                surface_normal=normals[vertex].tolist(), normal_error_degrees=angle, maximum_support_excess_m=excess)
            if vertex not in best or angle < best[vertex]['normal_error_degrees']: best[vertex] = row
    return dict(seed_vertex=seed, radius_m=float(radius_m), facing_degrees=float(facing_degrees),
        normal_tolerance_degrees=float(normal_tolerance_degrees), region_vertices=ids.tolist(),
        candidates=sorted(best.values(), key=lambda row: (row['surface_distance_m'], row['normal_error_degrees'], row['vertex'])),
        new_authored_condition=True, anatomical_review_pending=True, full_mesh_validation_required=True,
        rig_feasibility_verified=False, quality_approved=False)
