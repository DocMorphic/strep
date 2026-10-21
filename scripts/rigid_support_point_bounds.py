"""Conditional rigid-point movement bound; caller must establish applicability.

For p' = Q(p-c*a) + c*a', ||a'-a|| <= D and angle(Q) <= theta,
||p'-p|| <= |c|*D + 2*||p-c*a||*sin(theta/2).
The coefficient c is the actual homogeneous skin response, not an assumed 1.
This does not apply to a point partly influenced outside the moving subtree,
to changing relative child transforms, or to nonrigid pivot transforms.
Supply limits for every changed ancestor, including the pivot itself.
The ancestor chain's local-key limits bound its world angle at those keys;
they must not be reused at interpolated times without an interpolation bound.
"""
import math
from support_centroid_bounds import number,vector


def composed_angle_bound(local_limits_degrees):
    if not isinstance(local_limits_degrees,(list,tuple)) or not 1<=len(local_limits_degrees)<=64:
        raise ValueError('One to 64 explicit local rotation bounds required')
    values=[number(v,'local rotation bound',0.,180.) for v in local_limits_degrees]
    return min(180.,math.fsum(values))


def rigid_point_movement(point,pivot,response,translation_limit,rotation_limit_degrees):
    point=vector(point,'point');pivot=vector(pivot,'pivot')
    response=number(response,'homogeneous translation response',-1000.,1000.)
    translation_limit=number(translation_limit,'pivot translation limit',0.,1000.)
    angle=number(rotation_limit_degrees,'world rotation limit',0.,180.)
    radius=math.hypot(*(p-response*a for p,a in zip(point,pivot)))
    translation=abs(response)*translation_limit
    rotation=2*radius*math.sin(math.radians(angle)/2)
    geometric=math.fsum((translation,rotation))
    # An engineering roundoff reserve, not a formal interval certificate.
    reserve=64*math.ulp(1.+math.fsum(map(abs,point+pivot))+abs(response)+geometric)
    return dict(maximum_point_displacement_m=geometric+reserve,
        geometric_upper_bound_m=geometric,translation_allowance_m=translation,
        rotation_allowance_m=rotation,pivot_relative_radius_m=radius,
        roundoff_reserve_m=reserve,conditional_on_rigid_pivot=True,
        applicability_verified=False,formal_interval_certificate=False,feasibility_proven=False)
