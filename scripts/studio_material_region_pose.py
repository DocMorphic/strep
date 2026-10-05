"""Read-only single-time inspection of an existing authored material region.

Character animation coordinates only: no placement, object, partner, collision,
contact acceptance, correction, engine, or anatomical approval is inferred.
"""
import copy
import numpy as np
import studio_material_region as regions
from material_patch_bundle import fields, sha_binding
from native_support_clock import NativeSupportSampler
from rig_material_patch import MaterialSurface, require
from strep import read, save, sha256, now

SCHEMA = 'strep-studio-material-region-pose-v1'
METHODS = tuple(dict.fromkeys(regions.METHODS + ('studio_material_region_pose.py',)))


def syntax(payload):
    fields(payload, ('schema', 'id', 'preview_sha256', 'animation_index', 'time_s'), 'region pose inspection')
    require(payload['schema'] == SCHEMA, 'Region pose schema required')
    regions.folder_for(payload['id']); sha_binding(payload['preview_sha256'], 'preview binding')
    require(type(payload['animation_index']) is int and payload['animation_index'] >= 0,
            'Explicit nonnegative animation index required')
    require(type(payload['time_s']) in (int, float) and np.isfinite(payload['time_s']) and payload['time_s'] >= 0,
            'Explicit finite character-local time required')


def posed_region(material, patch, animation_index, time_s):
    reader = NativeSupportSampler(material.rig.document, material.rig.binary, animation_index, max_duration_s=None)
    require(time_s <= reader.duration, 'Character-local time exceeds animation duration; no clamping or looping')
    posed = material.posed(patch, reader.sample(time_s))
    ids = [material.face_index[tuple(ref)] for ref in patch['face_references']]
    faces = material.faces[ids]; vertices = np.unique(faces)
    triangles = np.asarray(posed['triangles_m'], dtype=float)
    cross = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    areas = np.linalg.norm(cross, axis=1)
    centers = triangles[:, 0]+((triangles[:, 1]-triangles[:, 0])+(triangles[:, 2]-triangles[:, 0]))/3
    require(np.isfinite(areas).all() and np.isfinite(centers).all(), 'Finite complete posed triangles required')
    normals = [(c/a).tolist() if a > patch['selector']['minimum_twice_area_m2'] else None for c, a in zip(cross, areas)]
    material.check_inputs()
    return dict(coordinate_space='character_animation_metres', animation_index=animation_index,
                animation_name=reader.name, duration_s=reader.duration, time_s=time_s,
                vertices=copy.deepcopy(patch['vertices']), positions_m=posed['positions_m'],
                face_references=copy.deepcopy(patch['face_references']),
                triangle_vertex_indices=np.searchsorted(vertices, faces).tolist(),
                triangle_centroids_m=centers.tolist(), triangle_unit_winding_normals=normals,
                triangle_twice_areas_m2=areas.tolist(), patch_winding=posed['winding'],
                complete_triangle_population=True, original_winding_preserved=True,
                animation_sampled=True, scene_placement_applied=False, contact_conditions_measured=False,
                anatomical_review_pending=True, contact_intent_approved=False, quality_approved=False, release_approved=False)


def inspect_pose(payload, resolver, name):
    """Caller holds the production lock. Retain a fresh separate inspection receipt."""
    syntax(payload)
    folder, baseline, request, patch = regions.checked_preview(payload['id'], payload['preview_sha256'], resolver)
    require(isinstance(name, str) and regions.NAME.fullmatch(name), 'Safe pose inspection ID required')
    root = (regions.ROOT/'reports/material-region-pose-previews').resolve(); output = (root/name).resolve()
    require(output.parent == root and output.is_relative_to((regions.ROOT/'reports').resolve()), 'Local inspection folder required')
    require(not output.exists(), 'Fresh pose inspection required')
    methods = {n: sha256(regions.ROOT/'scripts'/n) for n in METHODS}
    output.mkdir(parents=True)
    try:
        save(output/'pipeline.json', dict(status='processing')); save(output/'request.json', payload)
        inputs = baseline['input_sha256']
        material = MaterialSurface(folder/'input/character.glb', folder/'input/rig-profile.json',
                                   character_sha256=inputs['character.glb'], profile_sha256=inputs['rig-profile.json'])
        pose = posed_region(material, patch, payload['animation_index'], payload['time_s']); save(output/'pose.json', pose)
        regions.checked_preview(payload['id'], payload['preview_sha256'], resolver)
        require(read(output/'request.json') == payload and all(sha256(regions.ROOT/'scripts'/n) == h for n, h in methods.items()),
                'Inspection request or methods changed')
        result = dict(schema=SCHEMA, status='complete', id=name, at=now(), preview_id=payload['id'],
                      preview_sha256=payload['preview_sha256'], patch_sha256=baseline['patch_sha256'],
                      input_sha256=copy.deepcopy(inputs), implementation_sha256=methods,
                      request_sha256=sha256(output/'request.json'), pose_sha256=sha256(output/'pose.json'),
                      animation_edited=False, engine_executed=False, human_reviewed=False,
                      quality_approved=False, training_admitted=False, release_approved=False)
        save(output/'result.json', result); save(output/'pipeline.json', dict(status='complete'))
        return dict(result, result_sha256=sha256(output/'result.json'), request=copy.deepcopy(payload), pose=pose)
    except Exception as exc:
        save(output/'pipeline.json', dict(status='failed', error=str(exc), quality_approved=False, release_approved=False)); raise
