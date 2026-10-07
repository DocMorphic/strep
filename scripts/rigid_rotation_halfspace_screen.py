"""Exact rational screen of a point against independently rotating halfspaces.

This concerns represented input coordinates and explicit rational radian bounds.
It does not identify a mesh's interior, certify skinning arithmetic, replay
animation constraints, or prove that a broader articulated edit is impossible.
"""
from fractions import Fraction
import math
from numbers import Real

SCHEMA = 'strep-rigid-rotation-halfspace-screen-v1'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _point(value):
    try:
        _require(len(value) == 3, 'Three finite represented coordinates required')
        _require(all(isinstance(x, Real) and not isinstance(x, bool) and math.isfinite(float(x)) for x in value),
                 'Three finite represented coordinates required')
        return tuple(Fraction(float(x)) for x in value)
    except (TypeError, OverflowError) as exc:
        raise ValueError('Three finite represented coordinates required') from exc


def _bound(value):
    # No implicit degree conversion or downward-rounded decimal coercion.
    _require(isinstance(value, str) and 1 <= len(value) <= 128,
             'Explicit finite nonnegative rational radian string required')
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('Explicit finite nonnegative rational radian string required') from exc
    _require(0 <= result <= 1, 'Radian bound must lie between zero and one')
    return result


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def sqrt_upper(value, bits=128):
    """Outward rational square-root enclosure, with an exact square check."""
    _require(isinstance(value, Fraction) and value >= 0, 'Nonnegative rational radicand required')
    _require(type(bits) is int and 16 <= bits <= 256, 'Choose 16-256 square-root enclosure bits')
    denominator = 1 << bits
    scaled_numerator = value.numerator * denominator**2
    root = math.isqrt(scaled_numerator // value.denominator)
    if root**2 * value.denominator < scaled_numerator:
        root += 1
    result = Fraction(root, denominator)
    _require(result**2 >= value, 'Outward square-root check failed')
    return result


def screen(source_point, source_pivot, target_pivot, target_triangles,
           source_angle_radians, target_angle_radians, *, bits=128):
    """Upper-bound every outward plane residual for independent rigid rotations.

    Each triangle supplies an oriented normal and a plane anchor. Source point
    and target planes rotate independently about their specified fixed pivots.
    For z=point-target_pivot and n=the unnormalized reference normal:

      upper = reference residual
            + theta_target * sqrt(|n|²|z|²-(n.z)²)
            + theta_target²/2 * |n.z|
            + theta_source * sqrt(|n|²|point-source_pivot|²).

    The bounds sin(phi)<=phi and |1-cos(phi)|<=phi²/2 enclose target-normal
    rotation. Source chord displacement is at most theta_source*radius.
    All arithmetic after coordinate conversion is rational; square roots are
    rounded outward and checked by exact squaring. A nonnegative upper bound
    is inconclusive, never a separation/feasibility result.
    """
    point, source, target = [_point(v) for v in (source_point, source_pivot, target_pivot)]
    sa, ta = _bound(source_angle_radians), _bound(target_angle_radians)
    _require(type(bits) is int and 16 <= bits <= 256, 'Choose 16-256 square-root enclosure bits')
    _require(isinstance(target_triangles, (list, tuple)) and 1 <= len(target_triangles) <= 10000,
             'Complete explicitly supplied plane family required')
    z, moving = _sub(point, target), _sub(point, source)
    rows = []
    encodings = []
    for index, triangle in enumerate(target_triangles):
        _require(isinstance(triangle, (list, tuple)) and len(triangle) == 3,
                 'Three complete represented triangle vertices required')
        a, b, c = [_point(v) for v in triangle]
        n = _cross(_sub(b, a), _sub(c, a))
        norm_squared = _dot(n, n)
        _require(norm_squared > 0, 'Every declared plane must have a nondegenerate oriented triangle')
        dot = _dot(n, z)
        tangent_squared = norm_squared*_dot(z, z)-dot**2
        _require(tangent_squared >= 0, 'Exact tangent radicand must be nonnegative')
        base = _dot(n, _sub(point, a))
        target_bound = ta*sqrt_upper(tangent_squared, bits) + ta**2*abs(dot)/2
        source_bound = sa*sqrt_upper(norm_squared*_dot(moving, moving), bits)
        upper = base + target_bound + source_bound
        rows.append(dict(index=index, reference_plane_residual_rational=str(base),
                         target_rotation_reserve_rational=str(target_bound),
                         source_rotation_reserve_rational=str(source_bound),
                         plane_residual_upper_rational=str(upper),
                         strictly_behind_for_all_declared_rotations=upper < 0))
        encodings.append([[float(x).hex() for x in v] for v in (a, b, c)])
    return dict(schema=SCHEMA, source_point_hex=[float(x).hex() for x in point],
                source_pivot_hex=[float(x).hex() for x in source], target_pivot_hex=[float(x).hex() for x in target],
                target_triangles_hex=encodings, source_angle_radians_rational=str(sa),
                target_angle_radians_rational=str(ta), square_root_bits=bits,
                planes=rows, complete_declared_planes=len(rows),
                all_planes_strictly_containing_for_every_declared_rotation=all(r['strictly_behind_for_all_declared_rotations'] for r in rows),
                exact_rational_residual_bounds=True, actual_mesh_interior_certified=False,
                actual_animation_constraints_replayed=False, broader_articulated_infeasibility_proven=False,
                quality_approved=False, release_approved=False,
                scope='Every explicitly supplied oriented reference halfspace, represented binary-float coordinates, fixed pivots and independent rigid rotations within rational radian bounds. '
                      'Strict negative upper bounds prove membership in the rotated halfspace intersection under those assumptions only. '
                      'The input planes need not be a closed convex mesh; mesh containment, degree conversion, skinning/quantization, temporal/source/contact constraints and broader articulated edits are not certified. '
                      'Nonnegative bounds are inconclusive. No animation feasibility, automatic selection, collision-free or quality approval.')


def verify(result):
    """Recompute the full encoded certificate and reject missing/altered fields."""
    try:
        decode = lambda p: [float.fromhex(x) for x in p]
        expected = screen(decode(result['source_point_hex']), decode(result['source_pivot_hex']),
                          decode(result['target_pivot_hex']),
                          [[decode(v) for v in t] for t in result['target_triangles_hex']],
                          result['source_angle_radians_rational'], result['target_angle_radians_rational'],
                          bits=result['square_root_bits'])
        _require(result == expected, 'Encoded halfspace screen differs from complete replay')
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Encoded halfspace screen differs from complete replay') from exc
    return expected
