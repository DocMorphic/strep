"""Hash-bound SOMA pose guides for the unchanged Kimodo checkpoint.

Coordinates are native Y-up metres, relative to the generated clip's initial
smoothed root XZ origin. These are learned constraints, not scene collision IK.
"""
import re
from pathlib import Path
from strep import ROOT, sha256

KINDS = {'root2d', 'fullbody', 'left-hand', 'right-hand', 'left-foot', 'right-foot', 'end-effector'}
EFFECTORS = {'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot'}


def validate_guide_origin(request, guides):
    """An explicit shared translation; never silently move scene/pose targets."""
    if 'guide_origin' not in request:
        return None
    if request['guide_origin'] != 'start_pose':
        raise ValueError('guide_origin must be start_pose, or omitted to preserve source placement')
    for index, guide in enumerate(guides):
        if 0 in guide['frame_indices']:
            return index, guide['frame_indices'].index(0)
    raise ValueError('start_pose guide_origin requires a pose guide at target frame 0')


def validate_guides(guides, frame_count):
    if not isinstance(guides, list) or len(guides) > 32:
        raise ValueError('Provide at most 32 generation pose guides')
    occupied = set()
    for guide in guides:
        required = {'type', 'motion', 'sha256', 'source_frames', 'frame_indices'}
        if not isinstance(guide, dict) or not required <= set(guide) or set(guide) - required - {'joint_names'}:
            raise ValueError('Pose guides require type, motion, sha256, source_frames and frame_indices')
        if not isinstance(guide['type'], str) or guide['type'] not in KINDS:
            raise ValueError('Unsupported generation constraint type')
        path = guide['motion']
        if not isinstance(path, str) or not path or '\\' in path or ':' in path or path.startswith('/') or '..' in path.split('/') or not path.endswith('.npz'):
            raise ValueError('Pose motion must be a project-relative NPZ path')
        if not isinstance(guide['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', guide['sha256']):
            raise ValueError('Pose motion requires a SHA256 checksum')
        frames, sources = guide['frame_indices'], guide['source_frames']
        if not isinstance(frames, list) or not 1 <= len(frames) <= frame_count or any(type(f) is not int or not 0 <= f < frame_count for f in frames) or frames != sorted(set(frames)):
            raise ValueError('Guide frames must be sorted, unique and inside the generated timeline')
        if not isinstance(sources, list) or len(sources) != len(frames) or any(type(f) is not int or f < 0 for f in sources):
            raise ValueError('Provide one nonnegative source frame per guide frame')
        if occupied.intersection(frames):
            raise ValueError('Overlapping guides share implicit root constraints; combine effectors in one guide')
        occupied.update(frames)
        joints = guide.get('joint_names')
        if guide['type'] == 'end-effector':
            if not isinstance(joints, list) or not joints or any(not isinstance(j, str) or j not in EFFECTORS for j in joints) or len(set(joints)) != len(joints):
                raise ValueError('End-effector guide requires distinct hand/foot joint_names')
        elif joints is not None or 'joint_names' in guide:
            raise ValueError('joint_names only applies to end-effector guides')
    return guides


def compile_guides(request):
    """Validate source bytes and snapshot selected poses in upstream JSON form."""
    import numpy as np
    import torch
    from kimodo.geometry import matrix_to_axis_angle
    from kimodo.constraints import compute_global_heading
    from kimodo.skeleton import SOMASkeleton77
    from inspect_motion import validate_motion
    guides = validate_guides(request.get('generation_constraints', []), sum(round(s['duration_s'] * 30) for s in request['segments']))
    origin_anchor = validate_guide_origin(request, guides)
    compiled, provenance = [], []
    skeleton = SOMASkeleton77()
    for guide in guides:
        path = (ROOT / guide['motion']).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or sha256(path) != guide['sha256']:
            raise ValueError('Pose source is outside project, missing or checksum mismatched')
        with np.load(path, allow_pickle=False) as archive:
            data = dict(archive)
        validate_motion(data, 30)
        if data['posed_joints'].shape[1] != 77 or max(guide['source_frames']) >= len(data['posed_joints']):
            raise ValueError('Pose guide requires SOMA77 and valid source frames')
        frames = guide['source_frames']
        local = torch.tensor(data['local_rot_mats'][frames], dtype=torch.float32)
        root = torch.tensor(data['root_positions'][frames], dtype=torch.float32)
        rotations, positions, _ = skeleton.fk(local, root)
        if not np.allclose(positions.numpy(), data['posed_joints'][frames], atol=1e-4, rtol=0) or not np.allclose(rotations.numpy(), data['global_rot_mats'][frames], atol=1e-4, rtol=0):
            raise ValueError('Source pose arrays disagree with SOMA77 forward kinematics')
        smooth = data.get('smooth_root_pos', data['root_positions'])
        if smooth.shape != data['root_positions'].shape or not np.isfinite(smooth).all():
            raise ValueError('Invalid source smoothed root trajectory')
        item = dict(type=guide['type'], frame_indices=guide['frame_indices'], smooth_root_2d=smooth[frames][:, [0, 2]].tolist())
        if guide['type'] == 'root2d':
            item['global_root_heading'] = compute_global_heading(positions, skeleton).tolist()
        else:
            item.update(local_joints_rot=matrix_to_axis_angle(local).tolist(), root_positions=root.tolist())
            if 'joint_names' in guide:
                item['joint_names'] = guide['joint_names']
        compiled.append(item)
        provenance.append({**guide, 'source_fps_assumption': 30,
            'smooth_root_source': 'smooth_root_pos' if 'smooth_root_pos' in data else 'root_positions fallback',
            'scope': 'Root path and heading' if guide['type'] == 'root2d' else 'Pose-derived root path, hip height and heading plus selected body/effector channels; SOMA77 reduced to SOMA30; fingers and mesh contacts are not constrained'})
    if origin_anchor is not None:
        anchor_index, anchor_sample = origin_anchor
        offset = np.asarray(compiled[anchor_index]['smooth_root_2d'][anchor_sample], dtype=float)
        for item, source in zip(compiled, provenance):
            item['smooth_root_2d'] = (np.asarray(item['smooth_root_2d']) - offset).tolist()
            if 'root_positions' in item:
                root = np.asarray(item['root_positions'])
                root[:, [0, 2]] -= offset
                item['root_positions'] = root.tolist()
            source['origin_transform'] = dict(mode='start_pose', anchor_guide_index=anchor_index,
                anchor_source_frame=guides[anchor_index]['source_frames'][anchor_sample],
                target_frame=0, subtracted_xz_m=offset.tolist(),
                scope='Same XZ translation applied to every guide; source files, heights and local rotations unchanged. No scene geometry or actor placement is modified.')
    return compiled, provenance


def load_guides(compiled, skeleton, device=None):
    from kimodo.constraints import load_constraints_lst
    result = load_constraints_lst(compiled, skeleton, device=device)
    # Pinned upstream crop_move rebuilds joint indices on CPU. Keep all sparse
    # indices on CPU, as its own multiprompt transition guides do. Pose values
    # stay on the model device; create_conditions moves assembled indices there.
    for guide in result:
        for name in ['frame_indices', 'pos_indices', 'rot_indices']:
            if hasattr(guide, name): setattr(guide, name, getattr(guide, name).cpu())
    return result
