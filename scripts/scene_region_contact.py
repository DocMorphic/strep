"""Authored distributed hand contacts against rigid scene primitives.

The point effector remains a guide/diagnostic. Region acceptance requires a
separated triangle of skin samples, declared clearance and patch orientation.
This is sampled geometry, not a force, anatomy or continuous collision proof.
"""
import hashlib
import itertools
import json
import numpy as np
from floor_contact import Surface
from object_geometry import scene_geometry

SCHEMA = 'strep-scene-region-contact-v1'
LIMITS = {'clearance_m', 'contact_gap_m', 'spacing_m', 'area_m2',
          'centroid_error_m', 'local_radius_m', 'normal_degrees'}


def mesh_fingerprint(skin):
    """Canonical array-content identity, independent of NPZ packaging."""
    digest = hashlib.sha256()
    for name in ['bind_vertices', 'faces', 'lbs_indices', 'lbs_weights',
                 'bind_rig_transform', 'rig_joint_names']:
        array = np.asarray(skin[name])
        if name == 'rig_joint_names':
            payload = json.dumps(array.tolist(), ensure_ascii=True).encode()
        else:
            dtype = '<i8' if name in ['faces', 'lbs_indices'] else '<f8'
            payload = np.ascontiguousarray(array, dtype=dtype).tobytes()
        digest.update(name.encode() + json.dumps(array.shape).encode() + payload)
    return digest.hexdigest()


def validate_binding(binding, effector, skin):
    fields = {'schema', 'mesh_sha256', 'hand', 'face_ids', 'limits'}
    if not isinstance(binding, dict) or set(binding) != fields or binding['schema'] != SCHEMA:
        raise ValueError('Explicit versioned region binding required')
    if binding['mesh_sha256'] != mesh_fingerprint(skin):
        raise ValueError('Region binding mesh identity mismatch')
    hand = binding['hand']
    if hand not in ['LeftHand', 'RightHand'] or effector.get('joint') != hand:
        raise ValueError('Region must match the declared hand')
    ids = binding['face_ids']
    if (not isinstance(ids, list) or not ids or any(type(i) != int for i in ids)
            or len(set(ids)) != len(ids) or min(ids) < 0 or max(ids) >= len(skin['faces'])):
        raise ValueError('Region face IDs must be unique mesh triangles')
    faces = np.asarray(skin['faces'])[ids]
    vertices = np.unique(faces)
    if not 3 <= len(vertices) <= 256:
        raise ValueError('Region must contain 3 to 256 vertices')
    if type(effector.get('surface_vertex')) != int or effector['surface_vertex'] not in vertices:
        raise ValueError('Declared guide anchor must lie in the region')
    names = list(map(str, skin['rig_joint_names']))
    allowed = np.array([name.startswith(hand) for name in names])
    influences = np.asarray(skin['lbs_indices'])[vertices]
    weights = np.asarray(skin['lbs_weights'])[vertices]
    if not np.all(allowed[influences] | (weights == 0)):
        raise ValueError('Region has skin influences outside the declared hand')
    triangles = np.asarray(skin['bind_vertices'])[faces]
    normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    if np.any(np.linalg.norm(normals, axis=1) <= 1e-12):
        raise ValueError('Region contains degenerate bind triangles')
    limits = binding['limits']
    if not isinstance(limits, dict) or set(limits) != LIMITS:
        raise ValueError('Declare every region acceptance limit explicitly')
    for key, value in limits.items():
        if type(value) not in [int, float] or not np.isfinite(value) or value <= 0:
            raise ValueError('Region limits must be positive finite numbers')
    if limits['contact_gap_m'] < limits['clearance_m'] or limits['normal_degrees'] >= 90:
        raise ValueError('Invalid region gap or normal interval')
    return vertices, faces


def contact_witness(points, ids, target, gaps, limits):
    """Exhaustive bounded-memory search; first valid triangle proves existence."""
    eligible = np.flatnonzero(
        (gaps >= limits['clearance_m']-1e-6) & (gaps <= limits['contact_gap_m'])
        & (np.linalg.norm(points-target, axis=1) <= limits['local_radius_m']))
    choices = itertools.combinations(eligible, 3)
    while True:
        block = list(itertools.islice(choices, 4096))
        if not block:
            return None
        indices = np.asarray(block)
        tri = points[indices]
        spacing = np.minimum.reduce([np.linalg.norm(tri[:, a]-tri[:, b], axis=1)
                                     for a, b in [(0, 1), (1, 2), (2, 0)]])
        area = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)/2
        error = np.linalg.norm(tri.mean(1)-target, axis=1)
        valid = np.flatnonzero((spacing >= limits['spacing_m']) & (area >= limits['area_m2'])
                              & (error <= limits['centroid_error_m']))
        if len(valid):
            i = valid[0]
            return dict(vertices=ids[indices[i]].tolist(), minimum_spacing_m=float(spacing[i]),
                        area_m2=float(area[i]), centroid_error_m=float(error[i]),
                        contact_gaps_m=gaps[indices[i]].tolist())


def measure_frame(vertices, ids, faces, target, desired_normal, geometry, position, rotation, limits):
    points = vertices[ids]
    gaps = geometry.distance_gradient(points, position, rotation)[0]
    tri = vertices[faces]
    normal = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0)
    length = np.linalg.norm(normal)
    # A collapsed/cancelled patch is a measured failure, never an invented normal.
    angle = None if length <= 1e-12 else float(np.rad2deg(np.arccos(np.clip(
        (normal/length) @ desired_normal, -1, 1))))
    witness = contact_witness(points, ids, target, gaps, limits)
    clearance = float(gaps.min())
    passed = (witness is not None and clearance >= limits['clearance_m']-1e-6
              and angle is not None and angle <= limits['normal_degrees'])
    return dict(passed=bool(passed), minimum_region_clearance_m=clearance,
                normal_error_degrees=angle, contact_triangle=witness)


def compile_region(contact, scene, skin):
    """Validate authored meaning before any pipeline consumes the scene."""
    binding = contact['region_contact']
    ids, faces = validate_binding(binding, contact['effector'], skin)
    target = contact['target']
    if target.get('space') != 'object' or target.get('object') not in scene.get('objects', {}):
        raise ValueError('Region contact currently requires a declared rigid primitive target')
    if contact.get('normal_target') or contact.get('tangent_target'):
        raise ValueError('Region v1 uses the inward primitive normal; separate orientation overrides unsupported')
    geometry = scene_geometry(scene['objects'][target['object']])
    normal = -geometry.local_surface_normal(target.get('point_m'))
    a, b = contact['start_frame'], contact['end_frame']
    if type(a) != int or type(b) != int or not 0 <= a <= b < scene['frame_count']:
        raise ValueError('Region interval outside scene')
    return ids, faces, geometry, normal


def evaluate_region(contact, scene, actor, objects, skin):
    ids, faces, geometry, local_normal = compile_region(contact, scene, skin)
    position, rotation = objects[contact['target']['object']]
    local_target = np.asarray(contact['target']['point_m'], dtype=float)
    surface = Surface(skin)
    rows = []
    for frame in range(contact['start_frame'], contact['end_frame']+1):
        vertices = surface.vertices(actor['rotations'][frame], actor['positions'][frame])
        row = measure_frame(vertices, ids, faces, rotation[frame]@local_target+position[frame],
                            rotation[frame]@local_normal, geometry, position[frame], rotation[frame],
                            contact['region_contact']['limits'])
        rows.append(dict(frame=frame, **row))
    return dict(schema=SCHEMA, binding=contact['region_contact'], rows=rows,
                passed_frames=sum(r['passed'] for r in rows), frames=len(rows),
                all_requested_frames_passed=all(r['passed'] for r in rows),
                scope='Native integer-frame distributed region contact. Full body/object clearance remains a separate scene measurement. No continuous collision, force, self-collision or quality approval.')
