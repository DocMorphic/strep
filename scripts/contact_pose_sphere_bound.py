"""Conservative Euclidean skin-reach certificate using exact rational arithmetic."""
from fractions import Fraction
from math import isqrt
import numpy as np
from contact_pose_reachability import point_bound


def sqrt_enclosure(value, bits=96):
    """Rational bounds around sqrt(value), without rounded sqrt assumptions."""
    if not isinstance(value, Fraction) or value < 0 or type(bits) is not int or bits < 1:
        raise ValueError('Nonnegative rational and positive integer precision required')
    scale = 1 << bits
    numerator = value.numerator*scale*scale
    denominator = value.denominator
    lower = isqrt(numerator//denominator)
    upper = lower+(lower*lower*denominator < numerator)
    return Fraction(lower, scale), Fraction(upper, scale)


def sphere_bound(positions, weights, local_points, target, *, joint_budget=.22,
                 pin_tolerance=.005, rotation_norm_bound=1.02, arithmetic_reserve=1e-6):
    """Bound ||target - sum(w*t_ref)|| by D sum(w) + K sum(w*||q||) + eps.

    Every candidate joint displacement is at most D, rotations have operator
    norm at most K, and the material point must be within eps of its target.
    Upper rational square-root enclosures make the rotation allowance larger,
    never smaller. The squared conflict margin is compared exactly.
    """
    # Reuse established geometry/parameter validation; this does not rely on
    # the component certificate's verdict or rounded reported measurements.
    point_bound(positions, weights, local_points, target, joint_budget=joint_budget,
                pin_tolerance=pin_tolerance, rotation_norm_bound=rotation_norm_bound,
                arithmetic_reserve=arithmetic_reserve)
    positions, weights, local_points, target = map(lambda x: np.asarray(x, float),
                                                   [positions, weights, local_points, target])
    exact = lambda value: Fraction.from_float(float(value))
    w = list(map(exact, weights)); mass = sum(w, Fraction(0))
    levers = [sqrt_enclosure(sum((exact(v)**2 for v in q), Fraction(0)))[1] for q in local_points]
    lever_upper = sum((weight*lever for weight, lever in zip(w, levers)), Fraction(0))
    offset = [exact(target[a])-sum((weight*exact(p[a]) for weight,p in zip(w,positions)), Fraction(0)) for a in range(3)]
    distance_squared = sum((v*v for v in offset), Fraction(0))
    distance_lower, distance_upper = sqrt_enclosure(distance_squared)
    rotation_allowance = exact(rotation_norm_bound)*lever_upper
    tolerance = exact(pin_tolerance)+exact(arithmetic_reserve)
    allowed = exact(joint_budget)*mass+rotation_allowance+tolerance
    squared_margin = distance_squared-allowed**2
    displacement_lower = max(Fraction(0), (distance_lower-rotation_allowance-tolerance)/mass)
    return dict(conflict_verified=bool(squared_margin > 0),
                joint_displacement_lower_bound_m=float(displacement_lower),
                joint_displacement_lower_bound_exact=str(displacement_lower),
                joint_budget_m=joint_budget, pin_tolerance_m=pin_tolerance,
                rotation_operator_norm_bound=rotation_norm_bound, arithmetic_reserve_m=arithmetic_reserve,
                weight_sum=float(mass), weighted_bind_lever_upper_m=float(lever_upper),
                target_distance_lower_m=float(distance_lower), target_distance_upper_m=float(distance_upper),
                allowed_distance_upper_m=float(allowed),
                certificate=dict(distance_squared_exact=str(distance_squared), allowed_distance_upper_exact=str(allowed),
                                 squared_margin_exact=str(squared_margin), sqrt_enclosure_bits=96),
                quality_approved=False,
                scope='Necessary native-key joint-change/pin compatibility under the stated rotation norm assumption. '
                      'Exact squared comparison with outward rational lever bounds. No conflict is not feasibility; no export or realism claim.')
