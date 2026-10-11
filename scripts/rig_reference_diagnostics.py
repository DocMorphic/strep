"""Measure explicit humanoid reference proportions and transfer alignment.

The aligned pose uses identity source global rotations and the supplied neutral
joint coordinates. It is a synthetic diagnostic, not a generated motion or a
contact correction. Distances are compared relative to the mapped pelvis.
"""
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
from retarget_rig import ROLE_PARENTS, resolve_profile, transfer


def diagnose(rig, profile, names, neutral_joints):
    if (not isinstance(names, (list, tuple)) or not 1 <= len(names) <= 512
            or any(type(n) is not str or not n for n in names) or len(set(names)) != len(names)):
        raise ValueError('Distinct bounded source joint names required')
    raw = np.asarray(neutral_joints)
    if (raw.shape != (len(names), 3) or raw.dtype.kind not in 'fiu'
            or any(isinstance(x, (bool, np.bool_)) for x in np.asarray(neutral_joints, dtype=object).flat)
            or not np.isfinite(raw).all()):
        raise ValueError('One finite numeric source reference position per joint required')
    neutral = raw.astype(float)
    mapping, offset = resolve_profile(rig, profile)
    if not set(mapping) <= set(names):
        raise ValueError('Every target role requires a source reference joint')
    if len(rig.document['nodes']) > 512:
        raise ValueError('Reference diagnosis supports at most 512 target nodes')
    skeleton = SimpleNamespace(bone_order_names=list(names), neutral_joints=neutral)
    motion = dict(root_positions=neutral[[names.index('Hips')]],
                  global_rot_mats=np.tile(np.eye(3), (1, len(names), 1, 1)))
    worlds, _, _, scale, calibration = transfer(rig, motion, skeleton, mapping, offset,
                                               profile.get('axis_alignment_xyzw'))
    aligned = worlds[0]; hips = mapping['Hips']; source_hips = neutral[names.index('Hips')]
    joints = {}; edges = {}
    for role, node in mapping.items():
        expected = scale * (neutral[names.index(role)] - source_hips)
        actual = aligned[node, :3, 3] - aligned[hips, :3, 3]
        joints[role] = dict(target_node=node, source_relative_pelvis_m=(expected / scale).tolist(),
            aligned_target_relative_pelvis_m=actual.tolist(), scaled_source_relative_pelvis_m=expected.tolist(),
            position_difference_m=(actual - expected).tolist(), position_error_m=float(np.linalg.norm(actual - expected)),
            reference_rotation_change_degrees=float(np.rad2deg(Rotation.from_matrix(
                aligned[node, :3, :3] @ rig.reference[node, :3, :3].T).magnitude())))
        parent = ROLE_PARENTS[role]
        while parent and parent not in mapping: parent = ROLE_PARENTS[parent]
        if parent is None: continue
        source_vector = neutral[names.index(role)] - neutral[names.index(parent)]
        reference_vector = rig.reference[node, :3, 3] - rig.reference[mapping[parent], :3, 3]
        aligned_vector = aligned[node, :3, 3] - aligned[mapping[parent], :3, 3]
        sl, tl, al = [float(np.linalg.norm(v)) for v in (source_vector, reference_vector, aligned_vector)]
        if min(sl, tl, al) < 1e-6: raise ValueError('Nondegenerate mapped reference edges required')
        def angle(vector):
            return float(np.rad2deg(np.arccos(np.clip(np.dot(vector, source_vector)
                / (np.linalg.norm(vector) * sl), -1., 1.))))
        edges[role] = dict(parent_role=parent, source_length_m=sl, target_reference_length_m=tl,
            aligned_target_length_m=al, target_to_source_length_ratio=tl/sl,
            ratio_relative_to_leg_scale=tl/sl/scale, reference_direction_error_degrees=angle(reference_vector),
            aligned_direction_error_degrees=angle(aligned_vector))
    bounds = {}
    for name, world in [('target_default', rig.reference), ('target_aligned_identity', aligned)]:
        vertices = rig.vertices(world)
        if not np.isfinite(vertices).all(): raise ValueError('Non-finite reference mesh')
        bounds[name] = dict(vertices=len(vertices), minimum_m=vertices.min(axis=0).tolist(),
                           maximum_m=vertices.max(axis=0).tolist())
    return dict(schema='strep-rig-reference-diagnostics-v1', status='complete', leg_scale=scale,
        calibration=calibration, joints=joints, edges=edges, mesh_bounds=bounds,
        source_orientation_policy='Synthetic identity global rotations; supplied neutral joint positions, not source GLB bind transforms',
        target_policy='Existing transfer calibration; original target bone translations and helpers retained',
        position_policy='Relative to each pelvis; root offset does not affect reported joint differences',
        cause_established=False, contact_or_support_verified=False, quality_approved=False, release_approved=False)
