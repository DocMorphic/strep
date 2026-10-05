"""Complete source-bound default-pose directions for inspecting a picked region."""
import copy
import numpy as np
from rig_material_patch import require

SCHEMA = 'strep-material-region-orientation-v1'


def preview(material, patch):
    expected = material.patch(patch['role'], patch['face_references'], **patch['selector'])
    require(expected == patch, 'Exact source-bound patch required for orientation preview')
    ids = [material.face_index[tuple(ref)] for ref in patch['face_references']]
    faces = material.faces[ids]
    vertices = np.unique(faces)
    require(material.skin.vertex_references[vertices].tolist() == patch['vertices'],
            'Complete original patch vertex order required')
    local_faces = np.searchsorted(vertices, faces)
    triangles = material.points[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    areas = np.linalg.norm(cross, axis=1)
    require(np.isfinite(cross).all() and np.all(areas > patch['selector']['minimum_twice_area_m2']),
            'Every selected triangle must have a finite winding direction')
    centers = triangles[:, 0] + ((triangles[:, 1] - triangles[:, 0]) +
                                (triangles[:, 2] - triangles[:, 0])) / 3
    center = centers[0] + ((centers - centers[0]) * (areas / areas.sum())[:, None]).sum(axis=0)
    require(np.isfinite(centers).all() and np.isfinite(center).all(), 'Finite region inspection centers required')
    material.check_inputs()
    return dict(schema=SCHEMA, coordinate_space='character_default_pose_metres',
                face_references=copy.deepcopy(patch['face_references']),
                triangle_vertex_indices=local_faces.tolist(), triangle_centroids_m=centers.tolist(),
                triangle_unit_winding_normals=(cross / areas[:, None]).tolist(),
                triangle_twice_areas_m2=areas.tolist(), area_weighted_centroid_m=center.tolist(),
                patch_winding=copy.deepcopy(patch['winding']),
                complete_triangle_population=True, original_winding_preserved=True,
                animation_sampled=False, anatomical_review_pending=True, contact_intent_approved=False,
                quality_approved=False, release_approved=False)
