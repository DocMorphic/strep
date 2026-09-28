"""Contact-normal alignment and twist targets for a skinned hand frame."""
import numpy as np
from scipy.spatial.transform import Rotation


def unit(vector):
    vector = np.asarray(vector, float)
    length = np.linalg.norm(vector)
    if not np.isfinite(vector).all() or length < 1e-10:
        raise ValueError('Finite nonzero direction required')
    return vector/length


def align_direction(source, target):
    a, b = unit(source), unit(target)
    cross = np.cross(a, b); sine = np.linalg.norm(cross); cosine = np.clip(a@b, -1., 1.)
    if sine < 1e-12:
        if cosine > 0: return np.eye(3)
        axis = unit(np.cross(a, np.eye(3)[np.argmin(np.abs(a))]))
        return Rotation.from_rotvec(np.pi*axis).as_matrix()
    return Rotation.from_rotvec(np.arctan2(sine, cosine)*cross/sine).as_matrix()


def twist_target(normal, tangent, target_normal, degrees):
    if not np.isfinite(degrees): raise ValueError('Finite twist required')
    n = unit(target_normal)
    aligned = align_direction(normal, n)@unit(tangent)
    aligned = unit(aligned-n*(aligned@n))
    return Rotation.from_rotvec(np.deg2rad(degrees)*n).apply(aligned)


def hand_frame(surface_vertices, joint_positions, faces, vertex, wrist, knuckles):
    tri = surface_vertices[faces]
    normal = unit(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0))
    direction = joint_positions[knuckles].mean(0)-joint_positions[wrist]
    tangent = unit(direction-normal*(normal@direction))
    return surface_vertices[vertex], normal, tangent


def angular_error(a, b):
    return float(np.rad2deg(np.arccos(np.clip(unit(a)@unit(b), -1., 1.))))
