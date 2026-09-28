"""Finite-difference motion diagnostics; no physical balance or quality classifier."""
import numpy as np
from scipy.spatial.transform import Rotation


def measure(motion, fps=30., window_frames=30):
    joints = np.asarray(motion['posed_joints'], dtype=float)
    root = np.asarray(motion['root_positions'], dtype=float)
    rotations = np.asarray(motion['local_rot_mats'], dtype=float)
    if (joints.ndim != 3 or joints.shape[-1] != 3 or len(joints) < 3
            or root.shape != (len(joints), 3) or rotations.shape != (*joints.shape[:2], 3, 3)
            or not np.isfinite(fps) or fps <= 0 or type(window_frames) is not int or window_frames < 1
            or not all(np.isfinite(x).all() for x in (joints, root, rotations))):
        raise ValueError('Invalid motion/window for dynamics')
    start = max(2, len(joints) - window_frames)
    velocity = np.diff(joints, axis=0) * fps
    acceleration = np.diff(velocity, axis=0) * fps
    root_velocity = np.diff(root, axis=0) * fps
    root_acceleration = np.diff(root_velocity, axis=0) * fps
    relative = rotations[1:] @ rotations[:-1].swapaxes(-1, -2)
    angles = np.degrees(Rotation.from_matrix(relative.reshape(-1, 3, 3)).magnitude()).reshape(relative.shape[:2])
    measures = {}
    for name, values, first_frame in [
        ('joint_rms_speed_m_s', np.sqrt(np.mean(np.sum(velocity**2, axis=-1), axis=1)), 1),
        ('joint_rms_acceleration_m_s2', np.sqrt(np.mean(np.sum(acceleration**2, axis=-1), axis=1)), 2),
        ('root_speed_m_s', np.linalg.norm(root_velocity, axis=1), 1),
        ('root_acceleration_m_s2', np.linalg.norm(root_acceleration, axis=1), 2),
        ('local_rotation_step_degrees', angles.max(axis=1), 1)]:
        first = start - first_frame
        window = values[first:]
        measures[name] = dict(whole_clip_peak=float(values.max()),
            whole_clip_peak_arrival_frame=int(values.argmax() + first_frame),
            ending_peak=float(window.max()), ending_p95=float(np.percentile(window, 95)),
            ending_peak_arrival_frame=int(window.argmax() + start))
    return dict(fps=fps, ending_start_frame=start, ending_end_frame_exclusive=len(joints), measures=measures,
                scope='Finite differences are indexed by arrival frame; the first window derivative uses preceding frames. '
                      'Native joint RMS values and local rotation steps diagnose jumps; no force, balance, contact or realism approval.')
