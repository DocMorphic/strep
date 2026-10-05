import itertools
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from primitive_penetration_bounds import bounds, ring
from release_geometry import require_release_geometry, preview_penetration_bounds

I = np.eye(3)


@pytest.mark.parametrize('height,radial,vertical', [(1., 0., 0.), (1., .39, 0.), (1., .41, 0.),
    (1., 0., .99), (1., 0., 1.01), (.1, .1, .09), (.1, .4, .1)])
def test_parallel_cylinders_bracket_analytic_minkowski_cylinder_depth(height, radial, vertical):
    cylinder = Geometry('cylinder', (.2, height))
    result = bounds(cylinder, [0, 0, 0], I, cylinder, [radial, vertical, 0], I)
    expected = max(0., min(.4-radial, height-abs(vertical)))
    assert result['penetration_lower_m'] <= expected+1e-14 <= result['penetration_upper_m']+1e-14
    assert result['penetration_upper_m']-result['penetration_lower_m'] <= .00200001
    assert all(result[k] is False for k in ('floating_point_interval_certified', 'continuous_collision_certified', 'physics_release_qualified', 'quality_approved', 'release_approved'))


@pytest.mark.parametrize('point', [[0, 0, 0], [.1, 0, 0], [.3, 0, 0], [.3, .6, 0], [0, .6, 0], [0, 1, 0]])
def test_sphere_cylinder_side_cap_rim_interior_and_separation(point):
    c = Geometry('cylinder', (.2, 1.)); ball = Geometry('sphere', (.1,))
    rho = np.hypot(point[0], point[2]); q = np.array([rho-.2, abs(point[1])-.5])
    distance = np.linalg.norm(np.maximum(q, 0))+min(max(q), 0)
    expected = max(0., .1-distance)
    a = bounds(c, [0, 0, 0], I, ball, point, I); b = bounds(ball, point, I, c, [0, 0, 0], I)
    assert a['penetration_lower_m'] <= expected+1e-14 <= a['penetration_upper_m']+1e-14
    assert a['penetration_lower_m'] == b['penetration_lower_m'] and a['penetration_upper_m'] == b['penetration_upper_m']
    assert a['radial_segments'] == [0, 0] and a['axes_evaluated'] == 0


def vertices(shape, segments, outer=False):
    if shape.shape == 'box': return np.array(list(itertools.product(*[[-v/2, v/2] for v in shape.dimensions])))
    radius, height = shape.dimensions; points = ring(segments, outer)[0]*radius/(np.cos(np.pi/segments) if outer else 1)
    top = points.copy(); bottom = points.copy(); top[:, 1] = height/2; bottom[:, 1] = -height/2
    return np.concatenate([top, bottom])


@pytest.mark.parametrize('second', [Geometry('box', (.3, .4, .7)), Geometry('cylinder', (.25, .8))])
@pytest.mark.parametrize('seed', range(6))
def test_rotated_box_and_cylinder_bounds_agree_with_independent_minkowski_hull(second, seed):
    rng = np.random.default_rng(seed); first = Geometry('cylinder', (.2, .9))
    r, s = Rotation.random(random_state=rng).as_matrix(), Rotation.random(random_state=rng).as_matrix()
    q = rng.uniform(-.12, .12, 3); result = bounds(first, [0, 0, 0], r, second, q, s, radial_tolerance_m=.004)
    n, m = result['radial_segments']
    for outer, key in [(False, 'penetration_lower_m'), (True, 'penetration_upper_m')]:
        a, b = vertices(first, n, outer)@r.T, vertices(second, m, outer)@s.T+q
        difference = (a[:, None]-b[None]).reshape(-1, 3)
        hull = ConvexHull(difference); expected = max(0., -float(hull.equations[:, 3].max()))
        assert result[key] == pytest.approx(expected, abs=result['numerical_padding_m']*1.01)
    swapped = bounds(second, q, s, first, [0, 0, 0], r, radial_tolerance_m=.004)
    assert swapped['penetration_lower_m'] == pytest.approx(result['penetration_lower_m'], abs=1e-12)
    assert swapped['penetration_upper_m'] == pytest.approx(result['penetration_upper_m'], abs=1e-12)


def test_common_rigid_transform_and_refinement_keep_nested_depth_intervals():
    a, b = Geometry('cylinder', (.3, .6)), Geometry('box', (.25, .5, .5))
    r = Rotation.from_rotvec([.4, .2, -.1]).as_matrix(); s = Rotation.from_rotvec([-.2, .6, .1]).as_matrix()
    p = np.array([.1, .2, .3]); q = p+[.1, -.04, .05]
    before = bounds(a, p, r, b, q, s, radial_tolerance_m=.006)
    common = Rotation.from_rotvec([1., .2, .5]).as_matrix(); offset = np.array([50., -20., 100.])
    after = bounds(a, common@p+offset, common@r, b, common@q+offset, common@s, radial_tolerance_m=.006)
    assert after['penetration_lower_m'] == pytest.approx(before['penetration_lower_m'], abs=1e-12)
    assert after['penetration_upper_m'] == pytest.approx(before['penetration_upper_m'], abs=1e-12)
    fine = bounds(a, p, r, b, q, s, radial_tolerance_m=.001)
    assert fine['penetration_lower_m'] >= before['penetration_lower_m']-1e-12
    assert fine['penetration_upper_m'] <= before['penetration_upper_m']+1e-12


def test_near_parallel_edge_axes_are_retained_and_touch_remains_uncertain():
    c = Geometry('cylinder', (.2, 1.)); r = Rotation.from_rotvec([0, 0, 1e-13]).as_matrix()
    parallel = bounds(c, [0, 0, 0], I, c, [.4, 0, 0], I)
    tilted = bounds(c, [0, 0, 0], I, c, [.4, 0, 0], r)
    assert tilted['axes_evaluated'] > parallel['axes_evaluated']
    assert not parallel['definitely_separated'] and not parallel['definitely_penetrating']
    assert parallel['penetration_lower_m'] == 0 and parallel['penetration_upper_m'] > 0
    # Mathematical uncertainty remains explicit even when release accepts this shape.
    assert require_release_geometry(c)==c
    assert not parallel['physics_release_qualified']


def test_analytic_sphere_branch_needs_no_prism_even_when_budget_is_too_small_for_a_mesh():
    c, s = Geometry('cylinder', (50., 2.)), Geometry('sphere', (.2,))
    result = bounds(c, [0, 0, 0], I, s, [0, 1.1, 0], I, radial_tolerance_m=1e-12, maximum_segments=4)
    assert result['penetration_lower_m'] <= .1 <= result['penetration_upper_m']
    assert result['penetration_upper_m']-result['penetration_lower_m'] <= result['numerical_padding_m']*2.01
    assert result['radial_segments'] == [0, 0] and result['approximation_radial_expansion_m'] == [0, 0]


def test_positive_projection_gaps_are_not_reported_as_ordered_distance_bounds():
    c = Geometry('cylinder', (.2, 1.))
    result = bounds(c, [0, 0, 0], I, c, [.41, 0, 0], I)
    assert result['outer_projection_gap_m'] > result['inner_projection_gap_m']
    assert result['definitely_separated'] and result['penetration_lower_m'] == result['penetration_upper_m'] == 0


def test_public_release_preview_is_bound_query_without_changing_qualification():
    c, box = Geometry('cylinder', (.2, 1.)), Geometry('box', (.3, .4, .5))
    result = preview_penetration_bounds(c, [0, 0, 0], I, box, [.1, 0, 0], I)
    assert result == bounds(c, [0, 0, 0], I, box, [.1, 0, 0], I)
    assert require_release_geometry(c)==c
    assert not result['physics_release_qualified'] and not result['release_approved']


@pytest.mark.parametrize('seed', range(8))
def test_refinement_contains_fine_intervals_across_random_relative_orientations(seed):
    rng = np.random.default_rng(seed); a, b = Geometry('cylinder', (.3, .7)), Geometry('cylinder', (.2, .9))
    r, s = Rotation.random(random_state=rng).as_matrix(), Rotation.random(random_state=rng).as_matrix()
    q = rng.uniform(-.45, .45, 3)
    coarse = bounds(a, [0, 0, 0], r, b, q, s, radial_tolerance_m=.01)
    fine = bounds(a, [0, 0, 0], r, b, q, s, radial_tolerance_m=.001)
    assert fine['penetration_lower_m'] >= coarse['penetration_lower_m']-1e-12
    assert fine['penetration_upper_m'] <= coarse['penetration_upper_m']+1e-12


@pytest.mark.parametrize('first,second,offset,depth', [
    (Geometry('box', (.4, .6, .8)), Geometry('box', (.2, .8, .4)), [.1, 0, 0], .2),
    (Geometry('sphere', (.2,)), Geometry('sphere', (.3,)), [.4, 0, 0], .1),
    (Geometry('box', (.4, .6, .8)), Geometry('sphere', (.1,)), [.25, 0, 0], .05),
])
def test_noncylinder_pairs_keep_analytic_penetration_meaning(first, second, offset, depth):
    result = bounds(first, [0, 0, 0], I, second, offset, I)
    assert result['penetration_lower_m'] <= depth <= result['penetration_upper_m']
    assert result['radial_segments'] == [0, 0] and result['approximation_radial_expansion_m'] == [0, 0]


@pytest.mark.parametrize('options', [dict(radial_tolerance_m=0), dict(radial_tolerance_m=True), dict(radial_tolerance_m=float('nan')),
    dict(radial_tolerance_m=1e-12, maximum_segments=4), dict(maximum_segments=3), dict(maximum_segments=256), dict(maximum_segments=True),
    dict(numerical_padding_m=-1), dict(numerical_padding_m=True), dict(numerical_padding_m=float('inf'))])
def test_invalid_settings_and_complete_budget_reject(options):
    with pytest.raises(ValueError): bounds(Geometry('cylinder', (.2, 1)), [0, 0, 0], I, Geometry('box', (1, 1, 1)), [0, 0, 0], I, **options)


@pytest.mark.parametrize('fault', ['position', 'rotation', 'reflection', 'shear'])
def test_nonfinite_or_nonrigid_poses_reject(fault):
    p, r = [0, 0, 0], I.copy()
    if fault == 'position': p[0] = float('nan')
    elif fault == 'rotation': r[0, 0] = float('inf')
    elif fault == 'reflection': r[0, 0] = -1
    else: r[0, 1] = .001
    with pytest.raises(ValueError): bounds(Geometry('cylinder', (.2, 1)), p, r, Geometry('box', (1, 1, 1)), [0, 0, 0], I)
