"""Conservative rigid-patch guidance for a bounded pre-contact arm correction."""
import numpy as np
from grasp_orientation import unit
from scene_solver_context import context_primitives


def outward_clearance_shift(points, center, direction, radius, clearance):
    """First nonnegative ray translation outside the union of inflated spheres.

    Each point defines an open forbidden interval in translation distance.
    Merging the intervals also handles a safe point that would become unsafe
    while moving another point out. Actual articulated skin must be rechecked.
    """
    points, center = np.asarray(points, float), np.asarray(center, float)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or center.shape != (3,) or not np.isfinite(points).all() or not np.isfinite(center).all():
        raise ValueError('Finite nonempty 3D points and center required')
    if not np.isfinite(radius) or not np.isfinite(clearance) or radius <= 0 or clearance < 0: raise ValueError('Positive radius and nonnegative clearance required')
    direction = unit(direction); delta = points-center; axial = delta@direction
    disc = axial**2+(radius+clearance)**2-np.sum(delta**2,axis=1)
    intervals = sorted((-a-np.sqrt(d),-a+np.sqrt(d)) for a,d in zip(axial,disc) if d>0)
    shift = 0.
    for low,high in intervals:
        if low < shift < high: shift = float(high)
    return shift


def set_problem_frame(problem, frame):
    """Refresh all FK fields; retained contact records are guidance, not events."""
    if type(frame) is not int or not 0 <= frame < len(problem.base['root_positions']): raise ValueError('Valid frame required')
    problem.frame = frame
    problem.initial = problem.t(problem.previous['local_rot_mats'][frame]); problem.root = problem.t(problem.base['root_positions'][frame])
    offsets = np.zeros((len(problem.parents),3))
    for j,parent in enumerate(problem.parents):
        if parent >= 0: offsets[j] = problem.base['global_rot_mats'][frame,parent].T@(problem.base['posed_joints'][frame,j]-problem.base['posed_joints'][frame,parent])
    problem.offsets = problem.t(offsets)
    problem.objects = [(g,o['id'],problem.t(o['positions_m'][frame])[None],problem.t(o['rotations'][frame])[None]) for g,o in context_primitives(problem.context)]
    problem.cache = None


def influenced_hand_vertices(problem, hand):
    root=problem.names.index(hand); descendants=[]
    for joint in range(len(problem.parents)):
        j=joint
        while j>=0 and j!=root:j=problem.parents[j]
        descendants.append(j==root)
    return np.flatnonzero(np.any(np.array(descendants)[problem.skin['lbs_indices']] & (problem.skin['lbs_weights']>0),axis=1))
