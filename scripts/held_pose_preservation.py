"""Preserve seed poses after local-fit reconstruction.

The caller supplies the actual solver's locked-key mask, including adjoining
window endpoints. This function does not infer contacts, widen edit budgets,
reconstruct free keys, or certify boundary dynamics or motion quality.
"""
from copy import deepcopy
import numpy as np

POSE_KEYS = ('root_positions', 'posed_joints', 'local_rot_mats', 'global_rot_mats')


def restore_locked_pose(seed, candidate, locked):
    """Return an independent candidate with exact seed arrays at locked keys.

    Pass the warm-start motion as seed when one was used. Matching native
    dtypes are required: implicit conversion would defeat exact preservation.
    Auxiliary candidate arrays and metadata are copied unchanged.
    """
    if not isinstance(seed, dict) or not isinstance(candidate, dict):
        raise ValueError('Seed and candidate motion mappings required')
    for label, motion in [('seed', seed), ('candidate', candidate)]:
        for key in POSE_KEYS:
            value = motion.get(key)
            if not isinstance(value, np.ndarray) or not np.issubdtype(value.dtype, np.floating):
                raise ValueError(f'{label} {key} must be a floating-point array')
            if not np.isfinite(value).all():
                raise ValueError(f'{label} {key} must be finite')
        joints = motion['posed_joints']
        if joints.ndim != 3 or joints.shape[2] != 3 or min(joints.shape[:2]) < 1:
            raise ValueError(f'{label} joint array must have shape (frames, joints, 3)')
        frames, count = joints.shape[:2]
        shapes = {'root_positions': (frames, 3), 'posed_joints': (frames, count, 3),
                  'local_rot_mats': (frames, count, 3, 3), 'global_rot_mats': (frames, count, 3, 3)}
        if any(motion[k].shape != shape for k, shape in shapes.items()):
            raise ValueError(f'{label} pose arrays have incompatible shapes')
    for key in POSE_KEYS:
        if seed[key].shape != candidate[key].shape or seed[key].dtype != candidate[key].dtype:
            raise ValueError(f'Seed and candidate {key} shape and dtype must match')
    if not isinstance(locked, np.ndarray) or locked.dtype != np.bool_ or locked.shape != (frames,):
        raise ValueError('One boolean locked-key mask entry per frame required')
    result = deepcopy(candidate)
    for key in POSE_KEYS:
        result[key][locked] = seed[key][locked]
    return result
