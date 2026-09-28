"""Measure generated motion against snapshotted model constraint channels."""
import numpy as np
import torch
from kimodo.skeleton import SOMASkeleton30
from kimodo.constraints import compute_global_heading
from generation_constraints import load_guides


def audit(motion, compiled):
    skeleton = SOMASkeleton30()
    local = skeleton.from_SOMASkeleton77(torch.tensor(motion['local_rot_mats'], dtype=torch.float32))
    rotations, positions, _ = skeleton.fk(local, torch.tensor(motion['root_positions'], dtype=torch.float32))
    heading = compute_global_heading(positions, skeleton).numpy()
    smooth = motion.get('smooth_root_pos', motion['root_positions'])[:, [0, 2]]
    rows = []
    for guide in load_guides(compiled, skeleton):
        frames = guide.frame_indices.numpy()
        expected_heading = guide.global_root_heading.numpy()
        values = dict(root_path_error_m=np.linalg.norm(smooth[frames] - guide.smooth_root_2d.numpy(), axis=-1),
            heading_error_degrees=np.degrees(np.arccos(np.clip(np.sum(heading[frames] * expected_heading, axis=-1), -1, 1))))
        if guide.name != 'root2d':
            indices = guide.pos_indices if hasattr(guide, 'pos_indices') else torch.arange(skeleton.nbjoints)
            values['joint_position_error_m'] = np.linalg.norm(positions[frames][:, indices].numpy() - guide.global_joints_positions[:, indices].numpy(), axis=-1)
            values['hip_height_error_m'] = np.abs(motion['root_positions'][frames, 1] - guide.root_y_pos.numpy())
            if hasattr(guide, 'rot_indices'):
                actual = rotations[frames][:, guide.rot_indices].numpy()
                target = guide.global_joints_rots[:, guide.rot_indices].numpy()
                delta = actual @ target.swapaxes(-1, -2)
                values['effector_rotation_error_degrees'] = np.degrees(np.arccos(np.clip((np.trace(delta, axis1=-2, axis2=-1) - 1) / 2, -1, 1)))
        rows.append(dict(type=guide.name, frame_indices=frames.tolist(),
            maximum={k:float(v.max()) for k,v in values.items()}, samples={k:v.tolist() for k,v in values.items()}))
    failures = [dict(guide=i, metric=k, maximum=value) for i,row in enumerate(rows) for k,value in row['maximum'].items()
        if value > (15 if k.endswith('_degrees') else .03)]
    return dict(guides=rows, numerical_flags=failures, numerical_screen_passed=not failures,
        scope='SOMA30 conditioning-channel diagnostics: 3 cm and 15 degree provisional screens. Not skin contact, collision, action correctness, realism or animator approval.')
