"""Rigid contact-shape diagnostic; neither joint reachability nor motion approval."""
import numpy as np
from scipy.spatial.transform import Rotation


def place(points, anchor, normal, desired_anchor, desired_normal, twist_degrees=0.):
    points = np.asarray(points, float)
    anchor, normal, desired_anchor, desired_normal = [np.asarray(v, float) for v in
        (anchor, normal, desired_anchor, desired_normal)]
    if (points.ndim != 2 or points.shape[1:] != (3,) or not len(points)
            or not np.isfinite(points).all() or not np.isfinite(twist_degrees)
            or any(v.shape != (3,) or not np.isfinite(v).all() for v in (anchor, normal, desired_anchor, desired_normal))
            or any(abs(np.linalg.norm(v)-1.) > 1e-8 for v in (normal, desired_normal))):
        raise ValueError('Finite geometry, anchors, unit normals and twist required')
    axis = np.cross(normal, desired_normal); sine = np.linalg.norm(axis)
    cosine = float(np.clip(normal @ desired_normal, -1., 1.))
    if sine > 1e-12:
        align = Rotation.from_rotvec(axis/sine*np.arctan2(sine, cosine)).as_matrix()
    elif cosine < 0:
        basis = np.eye(3)[int(np.argmin(np.abs(normal)))]
        axis = np.cross(normal, basis); axis /= np.linalg.norm(axis)
        align = Rotation.from_rotvec(axis*np.pi).as_matrix()
    else:
        align = np.eye(3)
    rotation = Rotation.from_rotvec(desired_normal*np.deg2rad(twist_degrees)).as_matrix() @ align
    translation = desired_anchor-rotation@anchor
    return points@rotation.T+translation, rotation, translation


def summarize(surface, depths):
    if len(depths) != 2 or any(not np.isfinite(d['max_depth_m']) or d['max_depth_m'] < 0 for d in depths):
        raise ValueError('Two finite nonnegative directional depth results required')
    counts = surface['counts']
    proper = counts.get('proper_crossing', 0)
    unresolved = sum(v for k, v in counts.items() if k not in ('disjoint', 'proper_crossing'))
    degenerate = sum(len(v) for v in surface['degenerate_faces'])
    maximum = max(d['max_depth_m'] for d in depths)
    return dict(proper_crossings=proper, unresolved_pairs=unresolved, degenerate_faces=degenerate,
        maximum_vertex_depth_m=maximum,
        sampled_hand_screen_pass=proper == 0 and unresolved == 0 and degenerate == 0 and maximum <= 1e-8,
        rig_feasibility_verified=False, animation_quality_approved=False, collision_free_certified=False)
