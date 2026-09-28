"""Explicit in-memory contact calibration for isolated development pose studies."""
import numpy as np


def apply_contact_binding(problem, hand, vertex):
    if hand not in ('LeftHand', 'RightHand') or isinstance(vertex, (bool, np.bool_)) or not isinstance(vertex, (int, np.integer)):
        raise ValueError('Mapped hand and integer vertex required')
    if not 0 <= vertex < len(problem.skin['lbs_indices']): raise ValueError('Vertex outside skin')
    contacts = [c for c in problem.contacts if c['region'] == hand]
    normal_id = 'left-grip' if hand == 'LeftHand' else 'right-grip'
    normals = [n for n in problem.normals if n[0] == normal_id]
    if len(contacts) != 1 or len(normals) != 1: raise ValueError('One active hand contact and normal required')
    hand_joint = problem.names.index(hand); descendants = []
    for j in range(len(problem.parents)):
        while j >= 0 and j != hand_joint: j = problem.parents[j]
        descendants.append(j == hand_joint)
    faces = problem.skin['faces'][np.any(problem.skin['faces'] == vertex, axis=1)]
    if not len(faces): raise ValueError('Contact vertex has no adjacent triangles')
    ids = np.unique(faces)
    inside = np.array(descendants)[problem.skin['lbs_indices'][ids]] | (problem.skin['lbs_weights'][ids] == 0)
    if not np.all(inside): raise ValueError('Contact neighborhood extends outside mapped hand subtree')
    old = contacts[0]['vertex']
    # Do not mutate the source recipe, world targets, other contacts or limits.
    problem.contacts = [dict(c, vertex=int(vertex)) if c['region'] == hand else c for c in problem.contacts]
    problem.normals = [(name, faces.copy(), target) if name == normal_id else (name, triangles, target)
                       for name, triangles, target in problem.normals]
    problem.cache = None
    return dict(hand=hand, original_vertex=int(old), vertex=int(vertex), normal_id=normal_id, adjacent_triangles=len(faces),
                world_targets_unchanged=True, edit_limits_unchanged=True, source_recipe_unchanged=True,
                anatomical_approval=False, condition='Explicit alternate authored surface binding; original condition remains separate')


def apply_region_binding(problem, hand, anchor, patch):
    if hand not in ('LeftHand', 'RightHand') or patch.get('hand') != hand or type(anchor) is not int:
        raise ValueError('Matching declared hand region and integer anchor required')
    face_ids = np.asarray(patch['face_ids'])
    if face_ids.ndim != 1 or face_ids.dtype.kind not in 'iu' or not len(face_ids) or np.any(face_ids < 0) or np.any(face_ids >= len(problem.skin['faces'])):
        raise ValueError('Valid region face IDs required')
    faces = problem.skin['faces'][face_ids]; ids = np.unique(faces)
    if anchor not in ids or set(ids) != set(patch['vertices']): raise ValueError('Region vertices or anchor do not match its triangles')
    root = problem.names.index(hand); descendants = []
    for j in range(len(problem.parents)):
        while j >= 0 and j != root: j = problem.parents[j]
        descendants.append(j == root)
    if not np.all(np.array(descendants)[problem.skin['lbs_indices'][ids]] | (problem.skin['lbs_weights'][ids] == 0)):
        raise ValueError('Region includes influences outside hand subtree')
    normal_id = 'left-grip' if hand == 'LeftHand' else 'right-grip'
    contacts = [c for c in problem.contacts if c['region'] == hand]
    if len(contacts) != 1 or sum(n[0] == normal_id for n in problem.normals) != 1: raise ValueError('One active contact and normal required')
    old = contacts[0]['vertex']
    problem.contacts = [dict(c, vertex=anchor) if c['region'] == hand else c for c in problem.contacts]
    problem.normals = [(name, faces.copy(), target) if name == normal_id else (name, triangles, target) for name, triangles, target in problem.normals]
    problem.cache = None
    return dict(hand=hand, original_vertex=int(old), anchor=anchor, face_ids=face_ids.tolist(), vertices=ids.tolist(),
                normal_id=normal_id, normal_definition='Area-weighted declared region triangles', world_targets_unchanged=True,
                edit_limits_unchanged=True, anatomical_approval=False, condition='Explicit region contact; old fixed-point/local-normal condition remains separate')
