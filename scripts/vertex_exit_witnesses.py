"""Moving source/partner witnesses for currently penetrating mesh vertices."""
import numpy as np
import trimesh
from convex_partner_surface import candidates


def extract(source, target, faces, tolerance_m=1e-8):
    source, target, faces = np.asarray(source, float), np.asarray(target, float), np.asarray(faces)
    if (source.ndim != 2 or source.shape[1:] != (3,) or target.ndim != 2 or target.shape[1:] != (3,)
            or not len(target) or not np.isfinite(source).all() or not np.isfinite(target).all()
            or faces.ndim != 2 or faces.shape[1:] != (3,) or not len(faces)
            or not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0 or faces.max() >= len(target)
            or not np.isfinite(tolerance_m) or tolerance_m <= 0):
        raise ValueError('Finite points, valid closed target faces and positive tolerance required')
    mesh = trimesh.Trimesh(target, faces, process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent: raise ValueError('Closed wound target required')
    selected, broadphase = candidates(source, target); rows = []
    for start in range(0, len(selected), 32):
        ids = selected[start:start+32]
        signed = trimesh.proximity.signed_distance(mesh, source[ids])
        if not np.isfinite(signed).all(): raise ValueError('Finite signed distances required')
        ids = ids[signed > tolerance_m]
        if not len(ids): continue
        nearest, distance, triangle_ids = trimesh.proximity.closest_point(mesh, source[ids])
        triangles = target[faces[triangle_ids]]
        bary = trimesh.triangles.points_to_barycentric(triangles, nearest)
        if (not np.isfinite(bary).all() or np.any(bary < -1e-6) or np.any(bary > 1+1e-6)
                or not np.allclose(bary.sum(axis=1), 1., atol=1e-8, rtol=0)
                or not np.isfinite(distance).all() or np.any(distance <= tolerance_m)):
            raise ValueError('Valid nearest-surface exit witnesses required')
        bary = np.maximum(bary, 0); bary /= bary.sum(axis=1)[:, None]
        nearest = np.einsum('ni,nij->nj', bary, triangles)
        offset = nearest-source[ids]; lengths = np.linalg.norm(offset, axis=1)
        if np.any(lengths <= tolerance_m): raise ValueError('Nonzero exit directions required')
        normals = offset/lengths[:, None]
        for vertex, face, weights, normal, depth in zip(ids, triangle_ids, bary, normals, lengths):
            rows.append(dict(vertex=int(vertex), target_triangle=int(face), target_vertices=faces[face].tolist(),
                barycentric=weights.tolist(), exit_normal=normal.tolist(), initial_distance_m=float(depth)))
    return dict(vertices_checked=len(source), broadphase=broadphase, witnesses=rows,
        full_mesh_validation_required=True, quality_approved=False)


def gaps(points, triangles, barycentric, normals):
    p, t, b, n = map(lambda x: np.asarray(x, float), (points, triangles, barycentric, normals))
    count = len(p)
    if (p.shape != (count, 3) or t.shape != (count, 3, 3) or b.shape != (count, 3) or n.shape != (count, 3)
            or not all(np.isfinite(v).all() for v in (p, t, b, n)) or np.any(b < 0)
            or not np.allclose(b.sum(axis=1), 1., atol=1e-10, rtol=0)
            or not np.allclose(np.linalg.norm(n, axis=1), 1., atol=1e-10, rtol=0)):
        raise ValueError('Matching finite points, convex barycentrics and unit exit directions required')
    return np.einsum('ni,ni->n', p-np.einsum('ni,nij->nj', b, t), n)


class VertexExitObjective:
    def __init__(self, skins, placements, directions, frame=1, clearance_m=1e-8):
        if len(skins) != 2 or len(placements) != 2 or len(directions) != 2 or type(frame) is not int or frame < 0:
            raise ValueError('Two actors, two directed witness groups and a frame required')
        if not np.isfinite(clearance_m) or clearance_m < 0: raise ValueError('Nonnegative clearance required')
        self.skins, self.placements, self.frame, self.clearance = skins, placements, frame, clearance_m
        self.groups = []
        for rows in directions:
            self.groups.append(dict(ids=np.array([r['vertex'] for r in rows], int),
                triangles=np.array([r['target_vertices'] for r in rows], int).reshape(-1, 3),
                bary=np.array([r['barycentric'] for r in rows], float).reshape(-1, 3),
                normals=np.array([r['exit_normal'] for r in rows], float).reshape(-1, 3)))

    def depths(self, worlds):
        result = []
        for a, group in enumerate(self.groups):
            if not len(group['ids']): continue
            b = 1-a; ids = group['ids']; triangles = group['triangles']
            source = self.skins[a].evaluate(worlds[a], np.full(len(ids), self.frame), ids)
            source = source@self.placements[a]['rotation'].T+self.placements[a]['translation']
            target = self.skins[b].evaluate(worlds[b], np.full(triangles.size, self.frame), triangles.ravel())
            target = (target@self.placements[b]['rotation'].T+self.placements[b]['translation']).reshape(-1, 3, 3)
            result.append(self.clearance-gaps(source, target, group['bary'], group['normals']))
        return np.concatenate(result) if result else np.empty(0)
