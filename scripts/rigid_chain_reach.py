"""Exact necessary outer reach bound for an explicitly declared rigid chain."""
from fractions import Fraction
import math


GRID = 10**12  # Outward length rounding, at most one picometre per link.


def vector(value):
    if (not isinstance(value, list) or len(value) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   or abs(v) > 1e6 for v in value)):
        raise ValueError('Explicit finite three-component metre vector within 1e6 m required')
    return [Fraction(v) for v in value]


def rational(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def upper_length(squared):
    """Exact rational upper bound on sqrt(squared); no floating decision."""
    scaled = squared.numerator*GRID*GRID
    integer = math.isqrt(scaled//squared.denominator)
    if integer*integer*squared.denominator < scaled:
        integer += 1
    return Fraction(integer, GRID)


def diagnose(anchor_world_m, target_world_m, link_offsets_local_m, position_tolerance_m):
    """Relax all joint orientations/caps; a negative result proves nothing else."""
    anchor, target = vector(anchor_world_m), vector(target_world_m)
    if (not isinstance(link_offsets_local_m, list)
            or not 1 <= len(link_offsets_local_m) <= 64):
        raise ValueError('Explicit chain of 1–64 frozen local translation vectors required')
    if (type(position_tolerance_m) not in (int, float)
            or not math.isfinite(position_tolerance_m)
            or not 0 <= position_tolerance_m <= 1):
        raise ValueError('Explicit finite 0–1 m endpoint tolerance required')
    offsets = [vector(v) for v in link_offsets_local_m]
    squared = [sum(v*v for v in offset) for offset in offsets]
    lengths = [upper_length(q) for q in squared]
    radius = sum(lengths, Fraction(0))
    tolerance = Fraction(position_tolerance_m)
    distance = sum((a-b)**2 for a, b in zip(target, anchor))
    return dict(outer_reach_excluded=distance > (radius+tolerance)**2,
                anchor_world_m=list(anchor_world_m), target_world_m=list(target_world_m),
                link_offsets_local_m=[list(v) for v in link_offsets_local_m],
                position_tolerance_m=position_tolerance_m,
                link_squared_lengths_m2=[rational(q) for q in squared],
                link_upper_lengths_m=[rational(q) for q in lengths],
                upper_reach_radius_m=rational(radius),
                target_distance_squared_m2=rational(distance),
                squared_limit_with_tolerance_m2=rational((radius+tolerance)**2),
                link_count=len(offsets), quality_approved=False, release_approved=False,
                training_admitted=False,
                scope='Necessary outer reach bound for an explicit freely rotating rigid chain with frozen translations and fixed anchor. Exact rational comparison with outward length bounds. No joint orientation/cap, anatomy, collision, time, force, model, engine or human approval; no exclusion is not feasibility.')
