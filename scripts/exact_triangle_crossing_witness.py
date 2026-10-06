"""Exact interior witness for two triangles represented by finite binary floats.

Independent rational plane/edge construction, not a whole-mesh collision test.
The input coordinates have already undergone animation/skinning rounding.
Unwitnessed boundary/coplanar cases do not establish separation or clearance.
"""
from fractions import Fraction
import json
import math
from numbers import Real

SCHEMA = 'strep-exact-triangle-crossing-witness-v1'


def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def add(a, b): return tuple(x+y for x, y in zip(a, b))
def scale(a, s): return tuple(x*s for x in a)
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def triangle(value):
    try:
        if len(value) != 3 or any(len(row) != 3 for row in value): raise ValueError()
        converted = []
        for row in value:
            if any(isinstance(x, bool) or not isinstance(x, Real) or not math.isfinite(float(x)) for x in row):
                raise ValueError()
            converted.append(tuple(Fraction(float(x)) for x in row))
        return tuple(converted)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Finite numeric triangles of shape (3,3) required') from exc


def cuts(points, distances):
    result = [p for p, d in zip(points, distances) if d == 0]
    for i, j in ((0, 1), (1, 2), (2, 0)):
        if distances[i]*distances[j] < 0:
            result.append(add(points[i], scale(sub(points[j], points[i]), distances[i]/(distances[i]-distances[j]))))
    return result


def barycentric(points, point):
    u, v, p = sub(points[1], points[0]), sub(points[2], points[0]), sub(point, points[0])
    uu, uv, vv, pu, pv = dot(u, u), dot(u, v), dot(v, v), dot(p, u), dot(p, v)
    det = uu*vv-uv*uv
    b, c = (vv*pu-uv*pv)/det, (uu*pv-uv*pu)/det
    return (1-b-c, b, c)


def witness(left, right):
    a, b = triangle(left), triangle(right)
    result = dict(schema=SCHEMA, input_binary_float_hex=[[[float(x).hex() for x in row] for row in t] for t in (a, b)],
        kind=None, strict_interior_crossing_proved=False, quality_approved=False, release_approved=False,
        whole_scene_certified=False, continuous_collision_certified=False,
        scope='Exact rational construction for the supplied represented triangles only. Input animation/skinning arithmetic, '
              'penetration depth, boundary/coplanar clearance, other triangles, self-collision and continuous time are not certified.')
    na, nb = cross(sub(a[1], a[0]), sub(a[2], a[0])), cross(sub(b[1], b[0]), sub(b[2], b[0]))
    if not dot(na, na) or not dot(nb, nb): result['kind'] = 'degenerate'; return result
    direction = cross(na, nb)
    if not dot(direction, direction): result['kind'] = 'parallel_or_coplanar'; return result
    da = [dot(sub(p, b[0]), nb) for p in a]
    db = [dot(sub(p, a[0]), na) for p in b]
    if not all(min(d) < 0 < max(d) for d in (da, db)):
        result['kind'] = 'no_strict_straddle'; return result
    ca, cb = cuts(a, da), cuts(b, db)
    ia, ib = [[dot(p, direction) for p in points] for points in (ca, cb)]
    low, high = max(min(ia), min(ib)), min(max(ia), max(ib))
    if low >= high: result['kind'] = 'no_positive_interval'; return result
    middle = (low+high)/2
    point = add(ca[0], scale(direction, (middle-dot(ca[0], direction))/dot(direction, direction)))
    weights = [barycentric(t, point) for t in (a, b)]
    residuals = [dot(sub(point, t[0]), normal) for t, normal in ((a, na), (b, nb))]
    if any(residuals): raise ArithmeticError('Exact intersection construction left a plane')
    if not all(min(w) > 0 for w in weights):
        result['kind'] = 'no_interior_witness'; return result
    result.update(kind='proper_crossing', strict_interior_crossing_proved=True,
        witness_world_rational=[str(x) for x in point], witness_world_approx_m=[float(x) for x in point],
        barycentric_rational=[[str(x) for x in w] for w in weights],
        plane_residuals_rational=[str(x) for x in residuals],
        shared_projection_interval_rational=[str(low), str(high)],
        normal_cross_squared_rational=str(dot(direction, direction)))
    return result


def verify(result):
    """Reconstruct from exact input float encodings and reject altered witnesses."""
    try:
        a, b = [[[float.fromhex(x) for x in row] for row in t] for t in result['input_binary_float_hex']]
        expected = witness(a, b)
        if json.dumps(result, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
            raise ValueError('Exact crossing witness does not replay')
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Exact crossing witness does not replay') from exc
    return expected
