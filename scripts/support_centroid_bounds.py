"""Necessary mesh displacement for a planar centroid target and clearance.

If every selected vertex moves by at most D, their arithmetic centroid moves
by at most D (triangle inequality). Its distance to the target cylinder above
the clearance plane is therefore a lower bound, independent of the rig/solver.
Passing this relaxation is not evidence of feasible articulated motion.
"""
import math


def number(value, name, low=-1000., high=1000.):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Finite bounded '+name+' required')
    return float(value)


def vector(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError('Three coordinates required for '+name)
    return [number(x, name) for x in value]


def bound(points, target, normal, plane_offset, clearance, horizontal_tolerance, maximum_displacement):
    if not isinstance(points, (list, tuple)) or not 1 <= len(points) <= 20000:
        raise ValueError('Complete nonempty support population required (at most 20000 vertices)')
    points = [vector(p, 'support point') for p in points]
    target, normal = vector(target, 'target'), vector(normal, 'normal')
    norm = math.hypot(*normal)
    if abs(norm-1.) > 1e-12:
        raise ValueError('Unit support plane normal required')
    normal = [v/norm for v in normal]
    plane_offset = number(plane_offset, 'plane offset')
    clearance = number(clearance, 'clearance', 0.)
    horizontal_tolerance = number(horizontal_tolerance, 'horizontal tolerance', 0.)
    maximum_displacement = number(maximum_displacement, 'maximum displacement', 0.)
    center = [math.fsum(p[k] for p in points)/len(points) for k in range(3)]
    delta = [a-b for a,b in zip(center, target)]
    dot = lambda a,b: math.fsum(x*y for x,y in zip(a,b))
    tangent = [v-dot(delta, normal)*n for v,n in zip(delta, normal)]
    horizontal = max(0., math.hypot(*tangent)-horizontal_tolerance)
    vertical = max(0., clearance-(dot(center, normal)-plane_offset))
    centroid_lower = math.hypot(horizontal, vertical)
    floor_lower = max(0., max(clearance-(dot(p, normal)-plane_offset) for p in points))
    lower = max(centroid_lower, floor_lower)
    # Conservative rejection reserve; this is not formal interval arithmetic.
    reserve = 1e-9*(1+max(abs(v) for p in [*points, target] for v in p)+abs(plane_offset))
    return dict(status='incompatible_support_target' if lower > maximum_displacement+reserve else 'not_ruled_out',
        vertices=len(points), source_centroid_m=center, required_tangent_m=horizontal,
        required_normal_m=vertical, centroid_displacement_lower_bound_m=centroid_lower,
        individual_clearance_lower_bound_m=floor_lower, minimum_required_vertex_max_displacement_m=lower,
        maximum_vertex_displacement_m=maximum_displacement, comparison_reserve_m=reserve,
        feasibility_proven=False, formal_interval_certificate=False, quality_approved=False)
