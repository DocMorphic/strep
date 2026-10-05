"""Nested-prism penetration bounds for rigid boxes, spheres and cylinders.

Finite separating-axis projections are not Euclidean separation distances.
Arithmetic is Float64 with a reported pad, not interval arithmetic certification.
This read-only query does not qualify physics release or continuous collision.
"""
from functools import lru_cache
import numpy as np
from object_geometry import Geometry, finite

MAX_SEGMENTS = 128


def require(value, message):
    if not value: raise ValueError(message)


def rigid(rotation):
    r = finite(rotation, (3, 3), 'collision rotation')
    require(np.allclose(r.T@r, np.eye(3), atol=1e-10, rtol=0) and abs(np.linalg.det(r)-1) <= 1e-10,
            'Proper rigid collision rotations required')
    return r


@lru_cache(maxsize=64)
def ring(segments, outer=False):
    # Outer prism face normals (rather than its vertices) are at inner vertex
    # angles. Power-of-two refinement then nests BOTH sequences of prisms.
    angles = np.arange(segments)*2*np.pi/segments+(np.pi/segments if outer else 0)
    points = np.stack([np.cos(angles), np.zeros(segments), np.sin(angles)], axis=1)
    edges = np.roll(points, -1, axis=0)-points
    edges /= np.linalg.norm(edges, axis=1)[:, None]
    normals = points+np.roll(points, -1, axis=0)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    for array in (points, edges, normals): array.setflags(write=False)
    return points, edges, normals


def resolution(geometry, tolerance, maximum):
    if geometry.shape != 'cylinder': return 0, 0.
    radius = geometry.dimensions[0]; segments = 4
    while True:
        error = radius*(1/np.cos(np.pi/segments)-1)
        if error <= tolerance: return segments, float(error)
        segments *= 2
        require(segments <= maximum, 'Complete cylinder bounds exceed segment budget; no coarser fallback')


def polytope(geometry, rotation, segments, outer):
    if geometry.shape == 'box':
        return rotation.T, rotation.T
    _, edges, normals = ring(segments, outer)
    axis = np.array([[0., 1., 0.]])
    return np.concatenate([normals, axis])@rotation.T, np.concatenate([edges, axis])@rotation.T


def support(geometry, rotation, segments, axes, outer):
    local = axes@rotation
    if geometry.shape == 'box':
        value = abs(local)@(np.asarray(geometry.dimensions)/2)
        return value
    points, _, _ = ring(segments, outer)
    radius, height = geometry.dimensions
    radial = np.max(local@points.T, axis=1)*radius
    cap = abs(local[:, 1])*height/2
    return radial/(np.cos(np.pi/segments) if outer else 1)+cap


def projection_gap(first, r, n, second, s, m, delta, outer):
    normals, edges = polytope(first, r, n, outer); other_normals, other_edges = polytope(second, s, m, outer)
    axes = np.concatenate([normals, other_normals, np.cross(edges[:, None], other_edges[None]).reshape(-1, 3)])
    lengths = np.hypot(np.hypot(axes[:, 0], axes[:, 1]), axes[:, 2])
    # Retain every nonzero near-parallel edge axis; no angle cutoff/dedup.
    axes = axes[lengths > 0]/lengths[lengths > 0, None]
    a = support(first, r, n, axes, outer); b = support(second, s, m, axes, outer)
    return float(np.max(abs(axes@delta)-a-b)), len(axes)


def bounds(first, position, rotation, second, other_position, other_rotation, *,
           radial_tolerance_m=0.001, maximum_segments=128, numerical_padding_m=1e-9):
    """Lower/upper translation-to-separation depth; keep uncertainty explicit.

    Inscribed/circumscribed regular prisms enclose each analytic cylinder.
    Their Minkowski difference contains nested convex sets. The distance from
    an interior origin to the boundary is monotone under these inclusions.
    Complete face-normal/edge-cross SAT therefore brackets overlap depth.
    No direction or triangle is selected based on the contact outcome.
    """
    require(isinstance(first, Geometry) and isinstance(second, Geometry), 'Explicit primitive geometries required')
    require(type(radial_tolerance_m) in (int, float) and np.isfinite(radial_tolerance_m) and radial_tolerance_m > 0,
            'Positive finite radial approximation tolerance required')
    require(type(maximum_segments) is int and maximum_segments in (4, 8, 16, 32, 64, 128),
            'Power-of-two segment budget from 4 through 128 required')
    require(type(numerical_padding_m) in (int, float) and np.isfinite(numerical_padding_m) and numerical_padding_m >= 0,
            'Finite nonnegative arithmetic pad required')
    p = finite(position, (3,), 'collision position'); q = finite(other_position, (3,), 'other collision position')
    r, s = rigid(rotation), rigid(other_rotation)
    delta = q-p
    require(np.isfinite(delta).all(), 'Finite relative collision position required')
    pad = float(numerical_padding_m+64*np.finfo(float).eps*(np.linalg.norm(delta)+first.bounding_radius()+second.bounding_radius()))
    require(np.isfinite(pad), 'Finite arithmetic uncertainty required')
    if first.shape == 'sphere' or second.shape == 'sphere':
        # The sphere expands the other convex solid by its radius. Its center's
        # analytic signed distance includes side/cap/rim and interior cases.
        sphere, solid, center, solid_center, solid_r = (first, second, p, q, s) if first.shape == 'sphere' else (second, first, q, p, r)
        gap = float(solid.distance_gradient(center[None], solid_center, solid_r)[0][0]-sphere.dimensions[0])
        inner_gap = outer_gap = gap; axes_count = 0; method = 'analytic-sphere-offset'
        # No prism is needed for this branch, even for a cylinder/sphere pair.
        n = m = 0; error = other_error = 0.
    else:
        n, error = resolution(first, radial_tolerance_m, maximum_segments)
        m, other_error = resolution(second, radial_tolerance_m, maximum_segments)
        inner_gap, inner_axes = projection_gap(first, r, n, second, s, m, delta, False)
        outer_gap, outer_axes = projection_gap(first, r, n, second, s, m, delta, True)
        axes_count = inner_axes+outer_axes; method = 'complete-nested-polytope-sat'
    # Positive SAT projection gaps use different finite direction sets and need
    # not be ordered. Only the clamped penetration depths follow set inclusion.
    require(np.isfinite([inner_gap, outer_gap]).all(), 'Finite collision projections required')
    lower = max(0., -inner_gap-pad)
    upper = 0. if outer_gap > pad else max(0., -outer_gap)+pad
    require(lower <= upper+pad, 'Ordered penetration interval required')
    return dict(schema='strep-primitive-penetration-bounds-v1', method=method,
                first_geometry=first.record(), second_geometry=second.record(),
                penetration_lower_m=lower, penetration_upper_m=upper,
                inner_projection_gap_m=inner_gap, outer_projection_gap_m=outer_gap,
                approximation_radial_expansion_m=[error, other_error], radial_segments=[n, m],
                approximation_radial_inset_m=[g.dimensions[0]*(1-np.cos(np.pi/k)) if k else 0. for g, k in ((first, n), (second, m))],
                axes_evaluated=axes_count, numerical_padding_m=pad,
                definitely_separated=outer_gap > pad, definitely_penetrating=inner_gap < -pad,
                floating_point_interval_certified=False, continuous_collision_certified=False,
                physics_release_qualified=False, quality_approved=False, release_approved=False)
