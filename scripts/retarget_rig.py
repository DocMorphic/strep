"""Explicit-profile SOMA77 transfer to a validated rigged GLB; no loop/floor fixes."""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now
from rig_asset import RigAsset, index
from gltf_tools import local_matrix, append_accessor, write_glb, sample_animation
from correct_stance import swing, load_motion
from inspect_motion import validate_motion, contact_events

ROLE_PARENTS = {'Hips': None, 'Spine2': 'Hips', 'Chest': 'Spine2', 'Neck1': 'Chest', 'Head': 'Neck1',
                'LeftArm': 'Chest', 'LeftForeArm': 'LeftArm', 'LeftHand': 'LeftForeArm',
                'RightArm': 'Chest', 'RightForeArm': 'RightArm', 'RightHand': 'RightForeArm',
                'LeftLeg': 'Hips', 'LeftShin': 'LeftLeg', 'LeftFoot': 'LeftShin', 'LeftToeBase': 'LeftFoot',
                'RightLeg': 'Hips', 'RightShin': 'RightLeg', 'RightFoot': 'RightShin', 'RightToeBase': 'RightFoot'}
OPTIONAL = {'Spine2', 'Neck1', 'LeftToeBase', 'RightToeBase'}
PRIMARY = {'Hips': 'Chest', 'Spine2': 'Chest', 'Chest': 'Neck1', 'Neck1': 'Head',
           'LeftArm': 'LeftForeArm', 'LeftForeArm': 'LeftHand', 'RightArm': 'RightForeArm', 'RightForeArm': 'RightHand',
           'LeftLeg': 'LeftShin', 'LeftShin': 'LeftFoot', 'LeftFoot': 'LeftToeBase',
           'RightLeg': 'RightShin', 'RightShin': 'RightFoot', 'RightFoot': 'RightToeBase'}


def resolve_profile(rig, profile):
    if profile.get('schema') != 'strep-rig-profile-v1' or profile.get('reference_pose') != 'default_nodes':
        raise ValueError('Explicit v1 profile and default_nodes reference pose required')
    if set(profile) - {'schema', 'character_sha256', 'reference_pose', 'mapping', 'world_offset_m', 'axis_alignment_xyzw', 'notes'}:
        raise ValueError('Unknown rig profile field')
    mapping = profile.get('mapping', {})
    if not isinstance(mapping, dict) or set(mapping) - set(ROLE_PARENTS) or (set(ROLE_PARENTS) - OPTIONAL) - set(mapping):
        raise ValueError('Incomplete or unknown humanoid roles in mapping')
    nodes, resolved = rig.document['nodes'], {}
    for role, target in mapping.items():
        if isinstance(target, str):
            matches = [i for i, node in enumerate(nodes) if node.get('name') == target]
            if len(matches) != 1:
                raise ValueError(f'Bone name missing or ambiguous: {target}')
            target = matches[0]
        index(nodes, target, 'mapped node')
        if target not in rig.joints:
            raise ValueError(f'Mapped role {role} is not a skin joint')
        resolved[role] = target
    if len(set(resolved.values())) != len(resolved):
        raise ValueError('Roles must map to distinct target nodes')
    for role, target in resolved.items():
        parent_role = ROLE_PARENTS[role]
        while parent_role and parent_role not in resolved:
            parent_role = ROLE_PARENTS[parent_role]
        if parent_role:
            parent = rig.parents[target]
            # Intermediate helper bones are allowed, other mapped chains are not.
            while parent != -1 and parent not in resolved.values():
                parent = rig.parents[parent]
            if parent != resolved[parent_role]:
                raise ValueError(f'Mapping has incompatible hierarchy at {role}')
    offset = np.asarray(profile.get('world_offset_m', [0, 0, 0]), dtype=float)
    if offset.shape != (3,) or not np.isfinite(offset).all():
        raise ValueError('world_offset_m must be three finite coordinates')
    overrides = profile.get('axis_alignment_xyzw', {})
    if not isinstance(overrides, dict) or set(overrides) - set(mapping):
        raise ValueError('Axis alignment overrides must use mapped roles')
    for role, value in overrides.items():
        q = np.asarray(value, dtype=float)
        if q.shape != (4,) or not np.isfinite(q).all() or abs(np.linalg.norm(q) - 1) > 1e-5:
            raise ValueError(f'Axis alignment for {role} must be a normalized XYZW quaternion')
    return resolved, offset


def calibration(rig, mapping, skeleton, overrides=None):
    names, neutral = skeleton.bone_order_names, np.asarray(skeleton.neutral_joints)
    bind = rig.reference  # Authored reference, never reconstructed from inverse binds.
    corrections = {}
    for role, node in mapping.items():
        child_role = PRIMARY.get(role)
        if role == 'Chest' and child_role not in mapping:
            child_role = 'Head'
        if child_role not in mapping:
            child_role, parent_role = role, ROLE_PARENTS[role]
            while parent_role not in mapping:
                parent_role = ROLE_PARENTS[parent_role]
        else:
            parent_role = role
        target_direction = bind[mapping[child_role], :3, 3] - bind[mapping[parent_role], :3, 3]
        source_direction = neutral[names.index(child_role)] - neutral[names.index(parent_role)]
        if min(np.linalg.norm(target_direction), np.linalg.norm(source_direction)) < 1e-6:
            raise ValueError(f'Degenerate reference bone for {role}')
        corrections[node] = swing(target_direction, source_direction) @ bind[node, :3, :3]
    source = np.array([neutral[names.index(role)] - neutral[names.index('Hips')] for role in ('LeftLeg', 'RightLeg', 'Chest')])
    target = np.array([bind[mapping[role], :3, 3] - bind[mapping['Hips'], :3, 3] for role in ('LeftLeg', 'RightLeg', 'Chest')])
    if min(np.linalg.matrix_rank(source), np.linalg.matrix_rank(target)) < 2:
        raise ValueError('Degenerate pelvis reference landmarks')
    source /= np.linalg.norm(source, axis=1, keepdims=True)
    target /= np.linalg.norm(target, axis=1, keepdims=True)
    align, residual = Rotation.align_vectors(source, target)
    corrections[mapping['Hips']] = align.as_matrix() @ bind[mapping['Hips'], :3, :3]
    # Anatomical surface axes can disagree with joint-to-child directions,
    # notably when a toe joint lies near the sole rather than on its long axis.
    for role, quaternion in (overrides or {}).items():
        node = mapping[role]
        corrections[node] = Rotation.from_quat(quaternion).as_matrix() @ bind[node, :3, :3]
    ratios = []
    for side in ('Left', 'Right'):
        chain = [side + end for end in ('Leg', 'Shin', 'Foot')]
        target_length = sum(np.linalg.norm(bind[mapping[b], :3, 3] - bind[mapping[a], :3, 3]) for a, b in zip(chain, chain[1:]))
        source_length = sum(np.linalg.norm(neutral[names.index(b)] - neutral[names.index(a)]) for a, b in zip(chain, chain[1:]))
        ratios.append(float(target_length / source_length))
    return corrections, float(np.mean(ratios)), dict(leg_length_ratios=ratios, pelvis_landmark_alignment_residual=float(residual),
        axis_alignment_xyzw=overrides or {}, axis_alignment_space='Target reference world axes to SOMA neutral world axes; premultiplied onto target reference joint rotation')


def transfer(rig, motion, skeleton, mapping, offset, overrides=None, *, context_local=None):
    corrections, scale, diagnostic = calibration(rig, mapping, skeleton, overrides)
    roles = {node: skeleton.bone_order_names.index(role) for role, node in mapping.items()}
    local_reference = [local_matrix(node) for node in rig.document['nodes']]
    frames, globals_out = len(motion['root_positions']), []
    if context_local is not None:
        context_local = np.asarray(context_local, dtype=float)
        expected = (frames, len(local_reference), 4, 4)
        if context_local.shape != expected or not np.isfinite(context_local).all():
            raise ValueError('Transfer context must contain one finite local transform per frame and rig node')
        if not np.allclose(context_local[..., 3, :], [0, 0, 0, 1], atol=1e-7, rtol=0):
            raise ValueError('Transfer context must contain affine transforms')
        basis = context_local[..., :3, :3]
        if (np.max(np.abs(basis @ basis.swapaxes(-1, -2) - np.eye(3))) > 1e-4
                or np.max(np.abs(np.linalg.det(basis) - 1)) > 1e-4):
            raise ValueError('Transfer context requires rigid local transforms; animated scale or shear is unsupported')
        diagnostic = {**diagnostic, 'source_context_preserved': True,
                      'context_policy': 'Retain every non-pelvis local translation and all unmapped local transforms; replace mapped orientations and pelvis position'}
    translations, rotations = {n: [] for n in roles}, {n: [] for n in roles}
    for frame in range(frames):
        world = {}
        def visit(node):
            if node in world:
                return world[node]
            parent = np.eye(4) if rig.parents[node] < 0 else visit(rig.parents[node])
            local = (local_reference[node] if context_local is None else context_local[frame, node]).copy()
            if node in roles:
                desired = motion['global_rot_mats'][frame, roles[node]] @ corrections[node]
                # Source FK matrices contain float32 orthogonality drift. Solve
                # using the same proper quaternion rotation exported to glTF,
                # so the expected transforms do not accumulate that drift.
                local[:3, :3] = Rotation.from_matrix(np.linalg.inv(parent[:3, :3]) @ desired).as_matrix()
                if node == mapping['Hips']:
                    local[:3, 3] = (np.linalg.inv(parent) @ np.r_[motion['root_positions'][frame] * scale + offset, 1])[:3]
                translations[node].append(local[:3, 3].copy())
                rotations[node].append(Rotation.from_matrix(local[:3, :3]).as_quat())
            world[node] = parent @ local
            return world[node]
        globals_out.append(np.array([visit(node) for node in range(len(local_reference))]))
    translations = {node: np.array(values) for node, values in translations.items()}
    rotations = {node: np.array(values) for node, values in rotations.items()}
    for values in rotations.values():
        for frame in range(1, frames):
            if values[frame] @ values[frame - 1] < 0:
                values[frame] *= -1
    return np.array(globals_out), translations, rotations, scale, diagnostic


def export(character, profile_path, source, output, fps=30):
    import torch
    from kimodo.skeleton import SOMASkeleton77
    character, source, profile_path, output = map(lambda p: Path(p).resolve(), (character, source, profile_path, output))
    profile, character_hash, source_hash = read(profile_path), sha256(character), sha256(source)
    if profile.get('character_sha256') != character_hash:
        raise ValueError('Rig profile character checksum mismatch')
    rig, skeleton, motion = RigAsset.load(character), SOMASkeleton77(), load_motion(source)
    mapping, offset = resolve_profile(rig, profile)
    names, _, feet = validate_motion(motion, fps)
    if names != skeleton.bone_order_names:
        raise ValueError('Transfer requires native SOMA77 motion')
    rots, poses, _ = skeleton.fk(torch.tensor(motion['local_rot_mats'], dtype=torch.float32), torch.tensor(motion['root_positions'], dtype=torch.float32))
    if not np.allclose(rots.numpy(), motion['global_rot_mats'], atol=1e-4, rtol=0) or not np.allclose(poses.numpy(), motion['posed_joints'], atol=1e-4, rtol=0):
        raise ValueError('Source motion disagrees with SOMA77 forward kinematics')
    matrices, translations, rotations, scale, diagnostics = transfer(rig, motion, skeleton, mapping, offset, profile.get('axis_alignment_xyzw'))
    document, binary = copy.deepcopy(rig.document), bytearray(rig.binary)
    animation = dict(name='Strep_transferred_clip', samplers=[], channels=[])
    times = np.arange(len(matrices), dtype=np.float32) / fps
    time_accessor = append_accessor(document, binary, times, 'SCALAR')
    for node in translations:
        local = local_matrix(document['nodes'][node])
        document['nodes'][node].pop('matrix', None)
        document['nodes'][node].update(translation=local[:3, 3].tolist(), rotation=Rotation.from_matrix(local[:3, :3]).as_quat().tolist(), scale=[1, 1, 1])
        for path, values, kind in [('translation', translations[node], 'VEC3'), ('rotation', rotations[node], 'VEC4')]:
            acc = append_accessor(document, binary, values, kind)
            animation['channels'].append(dict(sampler=len(animation['samplers']), target=dict(node=node, path=path)))
            animation['samplers'].append(dict(input=time_accessor, output=acc, interpolation='LINEAR'))
    document['animations'] = [animation]
    document.setdefault('asset', {})['generator'] = 'Strep explicit rig transfer v1'
    document.setdefault('extras', {})['strep_transfer'] = dict(character_sha256=character_hash, source_motion_sha256=source_hash,
        profile_sha256=sha256(profile_path), fps=fps, frames=len(times), repeated=False, automatic_floor_lift_m=0,
        root_node=mapping['Hips'], leg_scale=scale, world_offset_m=offset.tolist())
    output.mkdir(parents=True, exist_ok=False)
    write_glb(output / 'character.glb', document, binary)
    decoded = RigAsset.load(output / 'character.glb')
    matrix_error, vertex_error, min_y = 0., 0., []
    for frame, expected in enumerate(matrices):
        actual = sample_animation(decoded.document, decoded.binary, 0, frame)
        expected_vertices, actual_vertices = rig.vertices(expected), decoded.vertices(actual)
        matrix_error = max(matrix_error, float(np.max(np.abs(actual - expected))))
        vertex_error = max(vertex_error, float(np.linalg.norm(actual_vertices - expected_vertices, axis=1).max()))
        min_y.append(float(actual_vertices[:, 1].min()))
    if max(matrix_error, vertex_error) > 1e-5:
        raise ValueError('Target GLB roundtrip verification failed')
    foot_diagnostics = {}
    for role in feet:
        if role not in mapping:
            continue
        points = matrices[:, mapping[role], :3, 3]
        speed = np.linalg.norm(np.diff(points[:, [0, 2]], axis=0), axis=1) * fps
        contacts = motion['foot_contacts'][:, feet.index(role)] >= .5
        samples = speed[contacts[:-1] & contacts[1:]]
        foot_diagnostics[role] = dict(predicted_support_intervals=len(samples), speed_p95_m_s=float(np.percentile(samples, 95)) if len(samples) else None)
    save(output / 'root-motion.json', dict(space='Target mapped pelvis world transform, Y-up metres; root extraction not applied', node=mapping['Hips'],
        times_s=times.tolist(), positions_m=matrices[:, mapping['Hips'], :3, 3].tolist(),
        rotations_xyzw=Rotation.from_matrix(matrices[:, mapping['Hips'], :3, :3]).as_quat().tolist()))
    save(output / 'contacts.json', dict(provenance='Unchanged source predictions; target contacts are not solved or verified',
        mapping={role: mapping.get(role) for role in feet}, intervals=contact_events(motion['foot_contacts'], feet, fps)))
    save(output / 'inventory.json', rig.inventory())
    shutil.copyfile(profile_path, output / 'rig-profile.json')
    np.savez_compressed(output / 'target-transforms.npz', global_matrices=matrices, times_s=times)
    report = dict(created_at=now(), character=str(character), character_sha256=character_hash, source=str(source), source_sha256=source_hash,
        profile_sha256=sha256(profile_path), implementation_sha256=sha256(__file__), importer_sha256=sha256(Path(__file__).with_name('rig_asset.py')),
        frames=len(times), fps=fps, last_key_time_s=float(times[-1]), sample_coverage_s=len(times)/fps,
        root_node=mapping['Hips'], scale_from_mean_leg_lengths=scale, mapping=mapping, calibration=diagnostics,
        source_global_rotation_orthogonality_max_error=float(np.max(np.abs(motion['global_rot_mats'] @ motion['global_rot_mats'].swapaxes(-1, -2) - np.eye(3)))),
        rotation_projection='Proper local quaternion rotations; float32 FK orthogonality drift is removed before verification',
        world_offset_m=offset.tolist(), automatic_floor_lift_m=0, original_animations_replaced_in_derived_file=rig.inventory()['original_animations'],
        roundtrip_max_matrix_error=matrix_error, roundtrip_max_vertex_error_m=vertex_error,
        target_mesh_min_y_m=min(min_y), target_mesh_floor_depth_max_m=max(0, -min(min_y)),
        target_mesh_floor_frames_above_1cm=int(np.sum(np.array(min_y) < -.01)), predicted_contact_foot_speed=foot_diagnostics,
        glb_sha256=sha256(output / 'character.glb'), engine_import=None, human_approved=False,
        limitations=['Deterministic rotation transfer; no target-mesh contact correction or collision avoidance.',
            'Default-node reference pose and explicit anatomical mapping require review. Bone-axis twist is underdetermined from positions.',
            'Unmapped fingers/helpers keep reference local transforms; twist is not distributed across helper bones.',
            'Only self-contained, unit-scale, single-skin GLB without morphs/compression is supported in v1.',
            'Original asset and source motion remain separate and unchanged; asset redistribution requires its own license.'])
    if character_hash != sha256(character) or source_hash != sha256(source):
        raise ValueError('Input changed during transfer')
    save(output / 'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inventory = commands.add_parser('inspect'); inventory.add_argument('--character', type=Path, required=True); inventory.add_argument('--output', type=Path, required=True)
    run = commands.add_parser('transfer')
    for name in ('character', 'profile', 'source', 'output'):
        run.add_argument('--' + name, type=Path, required=True)
    run.add_argument('--fps', type=float, default=30)
    args = parser.parse_args()
    if args.command == 'inspect':
        save(args.output, dict(character_sha256=sha256(args.character), **RigAsset.load(args.character).inventory()))
    else:
        report = export(args.character, args.profile, args.source, args.output, args.fps)
        print({k: report[k] for k in ('frames', 'target_mesh_floor_depth_max_m', 'roundtrip_max_vertex_error_m')})
