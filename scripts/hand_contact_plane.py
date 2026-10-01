"""Conservative hand-region plane proposals, separate from full-mesh approval."""
import numpy as np


def hand_region(parents, hand, skin_nodes, weights, faces):
    parents = np.asarray(parents)
    nodes = np.asarray(skin_nodes)
    weights = np.asarray(weights, float)
    faces = np.asarray(faces)
    if (parents.ndim != 1 or not np.issubdtype(parents.dtype, np.integer)
            or type(hand) is not int or not 0 <= hand < len(parents)
            or nodes.ndim != 2 or nodes.shape != weights.shape
            or not np.issubdtype(nodes.dtype, np.integer) or not nodes.size
            or nodes.min() < 0 or nodes.max() >= len(parents)
            or not np.isfinite(weights).all() or np.any(weights < 0)
            or not np.allclose(weights.sum(axis=1), 1., atol=1e-6, rtol=0)
            or faces.ndim != 2 or faces.shape[1:] != (3,) or not faces.size
            or not np.issubdtype(faces.dtype, np.integer)
            or faces.min() < 0 or faces.max() >= len(nodes)):
        raise ValueError('Valid hierarchy, normalized complete skin weights and faces required')
    descendants = []
    for node in range(len(parents)):
        current = node; seen = set(); belongs = False
        while current != -1:
            if current in seen or not 0 <= current < len(parents):
                raise ValueError('Acyclic valid parent hierarchy required')
            seen.add(current); belongs |= current == hand; current = int(parents[current])
        if belongs: descendants.append(node)
    mass = np.sum(weights * np.isin(nodes, descendants), axis=1)
    seeds = np.flatnonzero(mass >= .5)
    selected_faces = np.flatnonzero(np.any(np.isin(faces, seeds), axis=1))
    if not len(selected_faces): raise ValueError('Nonempty hand surface required')
    # Include every vertex of each incident triangle, including blended seams.
    vertices = np.unique(faces[selected_faces])
    return vertices, selected_faces


def plane_excess(points, midpoint, axis, actor):
    points = np.asarray(points, float)
    midpoint = np.asarray(midpoint, float); axis = np.asarray(axis, float)
    if (points.ndim != 2 or points.shape[1:] != (3,) or not len(points)
            or midpoint.shape != (3,) or axis.shape != (3,)
            or not np.isfinite(points).all() or not np.isfinite(midpoint).all()
            or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1.) > 1e-8
            or type(actor) is not int or actor not in (0, 1)):
        raise ValueError('Finite geometry, unit plane axis and actor 0 or 1 required')
    return (points-midpoint) @ axis * (1 if actor == 0 else -1)


def measure(points, midpoint, axis, actor):
    excess = plane_excess(points, midpoint, axis, actor)
    return dict(vertices=len(excess), vertices_across_plane=int(np.count_nonzero(excess > 0)),
                maximum_excess_m=float(excess.max()),
                selected_surface_plane_pass=bool(np.all(excess <= 0)),
                full_mesh_validation_required=True, quality_approved=False)
