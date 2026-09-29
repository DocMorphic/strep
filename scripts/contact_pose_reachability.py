"""Necessary native-pose bounds for a material vertex with nonnegative skin weights."""
from fractions import Fraction
import numpy as np


def point_bound(positions, weights, local_points, target, *, joint_budget=.22,
                pin_tolerance=.005, rotation_norm_bound=1.02, arithmetic_reserve=1e-6):
    """Certify an impossible pin without assuming a specific joint orientation.

    v = sum w_j (R_j q_j + t_j). If ||t_j-t_ref_j|| <= D and
    ||R_j||_2 <= K, each component of v differs from sum w_j t_ref_j
    by at most D sum w_j + K sum w_j ||q_j||_1. The L1 lever bound
    is deliberately conservative and avoids rounded square-root certificates.
    """
    positions, weights, local_points, target = map(lambda x: np.asarray(x, float),
                                                   [positions, weights, local_points, target])
    if weights.ndim != 1 or not len(weights) or positions.shape != (len(weights), 3) or local_points.shape != positions.shape or target.shape != (3,):
        raise ValueError('Matching skin influence positions, weights, bind points and XYZ target required')
    if any(not np.isfinite(x).all() for x in [positions, weights, local_points, target]) or (weights < 0).any() or not weights.sum() > 0:
        raise ValueError('Finite geometry and nonnegative nonempty skin weights required')
    for value in [joint_budget, pin_tolerance, rotation_norm_bound, arithmetic_reserve]:
        if type(value) not in (int, float) or not np.isfinite(value) or value < 0:
            raise ValueError('Finite nonnegative bound parameters required')
    if rotation_norm_bound < 1:
        raise ValueError('Rigid rotations require an operator norm bound of at least one')
    exact = lambda v: Fraction.from_float(float(v))
    w = list(map(exact, weights));mass = sum(w, Fraction(0))
    lever = sum((weight*sum((abs(exact(q)) for q in point), Fraction(0))
                 for weight, point in zip(w, local_points)), Fraction(0))
    rotation = exact(rotation_norm_bound)*lever
    tolerance = exact(pin_tolerance)+exact(arithmetic_reserve)
    allowed = exact(joint_budget)*mass+rotation+tolerance
    axes=[]
    for axis in range(3):
        origin = sum((weight*exact(position[axis]) for weight, position in zip(w, positions)), Fraction(0))
        distance = abs(exact(target[axis])-origin)
        margin = distance-allowed
        lower = max(Fraction(0), (distance-rotation-tolerance)/mass)
        axes.append(dict(axis='XYZ'[axis], conflict_verified=bool(margin > 0),
            target_to_weighted_joint_origin_m=float(distance), maximum_distance_m=float(allowed),
            incompatibility_margin_m=float(margin), incompatibility_margin_exact=str(margin),
            joint_displacement_lower_bound_m=float(lower)))
    return dict(axes=axes, any_verified_conflict=any(a['conflict_verified'] for a in axes),
        joint_displacement_lower_bound_m=max(a['joint_displacement_lower_bound_m'] for a in axes),
        joint_budget_m=joint_budget, pin_tolerance_m=pin_tolerance, rotation_operator_norm_bound=rotation_norm_bound,
        arithmetic_reserve_m=arithmetic_reserve, weight_sum=float(mass), weighted_bind_lever_l1_m=float(lever),
        quality_approved=False,
        scope='Necessary native-key joint-displacement/pin compatibility under stated rotation-norm bound. No conflict is not feasibility. No exported-interpolation, dynamics or quality approval.')
