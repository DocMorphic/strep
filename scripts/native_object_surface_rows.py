"""Primitive support-plane guides; complete decoded geometry remains authority.

Whole-triangle witnesses include intersections missed by vertex queries. Object
center enclosure has a separate escape guide. Ambiguous escape axes are recorded
and never substituted for an authored, uniquely defined grip normal.
"""
import numpy as np
import trimesh
from triangle_primitive_depth import query


def support_extent(geometry, normal, rotation):
    local = np.asarray(normal) @ rotation
    if geometry.shape == 'sphere': return geometry.dimensions[0]
    if geometry.shape == 'box': return float(abs(local) @ (np.asarray(geometry.dimensions) / 2))
    radius, height = geometry.dimensions
    return float(radius * np.linalg.norm(local[[0, 2]]) + height / 2 * abs(local[1]))


def barycentric(triangle, point):
    weights = trimesh.triangles.points_to_barycentric(triangle[None], point[None])[0]
    if not np.isfinite(weights).all() or weights.min() < -1e-7 or weights.max() > 1 + 1e-7:
        raise ValueError('Contained primitive barycentric witness required')
    weights = np.maximum(weights, 0); weights /= weights.sum()
    if np.linalg.norm(weights @ triangle - point) > 1e-10:
        raise ValueError('Primitive barycentric surface reconstruction differs')
    return weights


def append_rows(scene, time, vertices, meshes, faces, policy, clearance, entry, add):
    """Append every actor/object witness through the shared nontruncating budget."""
    reports = []; tolerance = policy['limits']['surface_tolerance_m']
    for actor, points in vertices.items():
        mesh = meshes[actor]
        if not mesh.is_volume:
            raise ValueError('Complete primitive center containment unavailable on actor surface')
        triangles = points[faces[actor]]
        for name, obj in scene.objects.items():
            geometry = obj['geometry']; positions, rotations = scene.object_poses(name, np.array([time]))
            position, rotation = positions[0], rotations[0]
            depths = query(triangles, geometry, position, rotation,
                resolution_m=policy['limits']['depth_resolution_m'])
            if len(depths['degenerate_faces']): raise ValueError('Degenerate primitive actor surface')
            count = 0; ambiguous = 0; separated = 0
            for face in np.flatnonzero(depths['candidate_faces'] & (depths['upper_m'] > 0)):
                triangle = triangles[face]; point = depths['witnesses_world_m'][face]
                _, gradients, defined = geometry.distance_gradient(point[None], position, rotation)
                normal = gradients[0]; choice = 'analytic-gradient' if defined[0] else 'analytic-subgradient'
                if np.linalg.norm(normal) <= 1e-12:
                    normal = -np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
                    if geometry.shape == 'cylinder':
                        local = normal @ rotation; local[1] = 0
                        if np.linalg.norm(local) <= 1e-12: local = np.array([1., 0, 0])
                        normal = local @ rotation.T
                    choice = 'deterministic-face-escape'
                normal = normal / np.linalg.norm(normal)
                constant = float(normal @ position + support_extent(geometry, normal, rotation))
                # Broadphase includes separated triangles. Emit only witnesses
                # within the declared proposal clearance, after the full query.
                if float(point @ normal - constant) >= clearance:
                    separated += 1
                    continue
                weights = barycentric(triangle, point)
                add('primitive-triangle', time, normal, entry(actor, faces[actor][face], weights),
                    constant=constant,
                    object=name, actor_triangle=int(face), normal_defined=bool(defined[0]), escape_axis=choice,
                    depth_lower_m=float(depths['lower_m'][face]), depth_upper_m=float(depths['upper_m'][face]))
                count += 1; ambiguous += int(not defined[0])
            signed = float(trimesh.proximity.signed_distance(mesh, position[None])[0])
            if not np.isfinite(signed): raise ValueError('Finite primitive center containment required')
            enclosure = False
            if signed >= -tolerance:
                closest, distance, nearest = trimesh.proximity.closest_point(mesh, position[None])
                point, face = closest[0], int(nearest[0]); triangle = triangles[face]
                if distance[0] > tolerance:
                    normal = (position-point) / distance[0]
                else:
                    normal = -np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
                    normal /= np.linalg.norm(normal)
                add('primitive-center-enclosure', time, normal, entry(actor, faces[actor][face], barycentric(triangle, point)),
                    constant=float(normal @ position + support_extent(geometry, normal, rotation)),
                    object=name, actor_triangle=face, signed_center_distance_m=signed,
                    escape_axis='nearest-boundary-inward', normal_defined=False)
                enclosure = True
            reports.append(dict(actor=actor, object=name, total_faces=len(triangles),
                candidate_faces=int(depths['candidate_faces'].sum()), triangle_rows=count,
                separated_witnesses=separated,
                ambiguous_triangle_axes=ambiguous, center_enclosure_row=enclosure,
                signed_center_distance_m=signed, containment_available=True))
    return reports
