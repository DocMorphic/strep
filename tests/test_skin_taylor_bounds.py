import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_skin_motion_bounds import fixture, channel
from skin_taylor_bounds import SkinTaylorBounds, rotation_jet, rotation_derivative
from swept_triangle_separation import pair_bounds, audit
from test_swept_triangle_separation import A, B, F, bound
from audit_skin_taylor import placed_bound


def replay(rig, sampler, value):
    center = value['center_s']; delta = 1e-6
    numerical = (rig.vertices(sampler.sample(center+delta))-rig.vertices(sampler.sample(center-delta)))/(2*delta)
    np.testing.assert_allclose(value['center_velocities'], numerical, atol=2e-8, rtol=1e-7)
    for time in np.linspace(value['start_s'], value['end_s'], 151):
        predicted = value['center_vertices']+(time-center)*value['center_velocities']
        error = np.linalg.norm(rig.vertices(sampler.sample(time))-predicted, axis=1)
        assert np.all(error <= value['remainder_radius_m'])


def test_linear_translation_is_exact_up_to_padding():
    rig, sampler = fixture([channel(1, 'translation', [[0, 0, 0], [3, 2, -1]])])
    value = SkinTaylorBounds(rig, sampler).interval(.1, .9)
    np.testing.assert_allclose(value['center_velocities'], np.tile([3, 2, -1], (3, 1)), atol=1e-14)
    np.testing.assert_allclose(value['remainder_radius_m'], 1e-10, atol=1e-20)
    replay(rig, sampler, value)


@pytest.mark.parametrize('angle', [1e-10, 1e-7, 1.999e-6, 2.001e-6, .5, np.pi])
def test_rotation_branches_hierarchy_blending_and_inverse_bind(angle):
    q = Rotation.from_rotvec([[0, 0, 0], [0, angle, 0]]).as_quat(); q[1] *= -1
    rig, sampler = fixture([channel(1, 'rotation', q), channel(0, 'rotation', q),
        channel(0, 'translation', [[2, 0, 0], [3, 1, -1]]),
        channel(1, 'translation', [[0, 0, 0], [1, -1, 2]])])
    rig.document['nodes'][1]['scale'] = [1.000001, 1., 1.]
    rig.inverse[1, 3, 0] = 1e-6
    replay(rig, sampler, SkinTaylorBounds(rig, sampler).interval(.2, .8))


def test_rotation_acceleration_bound_against_numerical_derivative():
    rng = np.random.default_rng(333)
    for _ in range(30):
        a, b = Rotation.random(2, random_state=rng).as_quat(); dt = rng.uniform(.01, 2)
        q, dq, first, second = rotation_jet(a, b, dt, .4)
        actual_first = np.linalg.norm(rotation_derivative(q, dq), ord=2)
        derivatives = [rotation_derivative(*rotation_jet(a, b, dt, u)[:2]) for u in [.4-1e-5, .4+1e-5]]
        actual_second = np.linalg.norm((derivatives[1]-derivatives[0])/(2e-5*dt), ord=2)
        assert actual_first <= first+1e-10 and actual_second <= second+1e-8


def test_random_rotation_axes_match_actual_skin_velocities_and_remainders():
    rng = np.random.default_rng(402)
    for _ in range(12):
        rig, sampler = fixture([channel(1, 'rotation', Rotation.random(2, random_state=rng).as_quat()),
            channel(0, 'rotation', Rotation.random(2, random_state=rng).as_quat()),
            channel(0, 'translation', rng.normal(size=(2, 3))),
            channel(1, 'translation', rng.normal(size=(2, 3)))])
        replay(rig, sampler, SkinTaylorBounds(rig, sampler).interval(.1, .9))


def test_knots_cannot_be_crossed_and_clamped_channels_have_zero_velocity():
    rig, sampler = fixture([channel(1, 'translation', [[0, 0, 0], [2, 1, 0]], times=(.2, .8))])
    provider = SkinTaylorBounds(rig, sampler)
    with pytest.raises(ValueError, match='native knot'): provider.interval(0, 1)
    for start, end in [(0, .2), (.2, .8), (.8, 1)]:
        value = provider.interval(start, end); replay(rig, sampler, value)
        if start != .2: np.testing.assert_array_equal(value['center_velocities'], 0.)


def test_constant_step_and_nonaffine_static_matrix():
    rig, sampler = fixture([channel(1, 'translation', [[1, 2, 3], [1, 2, 3]], mode='STEP')])
    replay(rig, sampler, SkinTaylorBounds(rig, sampler).interval(0, 1))
    matrix = np.eye(4); matrix[3, 0] = 1e-8
    rig.document['nodes'][0] = dict(matrix=matrix.T.reshape(-1).tolist())
    with pytest.raises(ValueError, match='affine'): SkinTaylorBounds(rig, sampler)


def test_common_velocity_cancels_but_approaching_triangles_stay_unresolved():
    zeros = np.zeros((1, 3)); velocity = np.full((1, 3, 3), 100.)
    value = pair_bounds(A[None], zeros, B[None], zeros,
        left_velocity=velocity, right_velocity=velocity, time_radius_s=.5)
    assert value['separated'][0]
    assert not pair_bounds(A[None], zeros, B[None], zeros,
        left_velocity=velocity, right_velocity=velocity-2, time_radius_s=.5)['separated'][0]


def test_directional_axis_bound_contains_synchronized_trajectories_and_errors():
    rng = np.random.default_rng(55)
    a, b = np.repeat(A[None], 20, axis=0), np.repeat(B[None], 20, axis=0)
    va, vb = [rng.normal(size=(20, 3, 3))*.08+20 for _ in range(2)]
    ra, rb = [rng.uniform(.01, .04, (20, 3)) for _ in range(2)]
    result = pair_bounds(a, ra, b, rb, left_velocity=va, right_velocity=vb, time_radius_s=.5)
    assert result['separated'].all()
    for time in np.linspace(-.5, .5, 31):
        points = []
        for x, v, r in [(a, va, ra), (b, vb, rb)]:
            error = rng.normal(size=x.shape); error *= r[:, :, None]/np.linalg.norm(error, axis=2, keepdims=True)
            points.append(np.einsum('nvi,ni->nv', x+time*v+error, result['axes']))
        assert np.all(points[1].min(axis=1)-points[0].max(axis=1) >= result['margin_m'])


def test_directional_audit_checks_all_candidates_and_validates_even_empty_queries():
    left, right = bound(A, 100.), bound(B, 100.)
    for value in (left, right):
        value.update(center_velocities=np.full((3, 3), 100.), remainder_radius_m=np.full(3, .01), time_radius_s=.5)
    result = audit(left, F, right, F, motion_model='taylor')
    assert result['outcome'] == 'surface_separation_bound' and result['checked_pairs'] == 1
    assert audit(left, F, right, F)['outcome'] == 'unresolved'
    right['time_radius_s'] = .4
    with pytest.raises(ValueError, match='time radius'): audit(left, F, right, F, motion_model='taylor')
    with pytest.raises(ValueError): pair_bounds(A[None], np.zeros((1, 3)), B[None], np.zeros((1, 3)), left_velocity=np.zeros((1, 3, 3)))


def test_crossing_between_endpoints_cannot_receive_separation():
    velocity = np.tile([0., 0, 4], (1, 3, 1)); zeros = np.zeros((1, 3))
    # Both endpoint poses have distinct parallel planes, but the moving plane
    # meets the stationary triangle at delta=-.25, inside the interval.
    value = pair_bounds(A[None], zeros, (A+[0, 0, 1])[None], zeros,
        left_velocity=velocity*0, right_velocity=velocity, time_radius_s=.5)
    assert not value['separated'][0]
    # Even zero center velocity is insufficient if acceleration can close gap.
    value = pair_bounds(A[None], zeros+.6, (A+[0, 0, 1])[None], zeros+.6,
        left_velocity=velocity*0, right_velocity=velocity*0, time_radius_s=.5)
    assert not value['separated'][0]


def test_directional_swap_winding_and_rigid_transform_invariance():
    rng = np.random.default_rng(886)
    va = np.array([[.01, .02, .03], [.03, .02, .01], [-.01, -.02, -.03]])+30
    vb = va+.01; radii = np.full((1, 3), .01)
    for _ in range(10):
        rotation = Rotation.random(random_state=rng).as_matrix(); shift = rng.normal(size=3)*100
        a, b = A@rotation.T+shift, B@rotation.T+shift
        v, w = va@rotation.T, vb@rotation.T
        first = pair_bounds(a[None], radii, b[None], radii, left_velocity=v[None], right_velocity=w[None], time_radius_s=.5)
        second = pair_bounds(b[::-1][None], radii, a[::-1][None], radii,
            left_velocity=w[::-1][None], right_velocity=v[::-1][None], time_radius_s=.5)
        assert first['separated'][0] and second['separated'][0]
        assert first['margin_m'][0] == pytest.approx(second['margin_m'][0], abs=1e-10)


def test_scene_placement_rotates_velocity_without_translating_it():
    rig, sampler = fixture([channel(1, 'translation', [[0, 0, 0], [3, 2, -1]])])
    rotation = Rotation.from_euler('y', 90, degrees=True).as_matrix(); shift = np.array([9., 8., 7.])
    provider = SkinTaylorBounds(rig, sampler)
    value = placed_bound(dict(bound=provider, rotation=rotation, translation=shift), .1, .9)
    np.testing.assert_allclose(value['center_velocities'], np.tile([3, 2, -1], (3, 1))@rotation.T)
    for stamp in np.linspace(.1, .9, 17):
        actual = rig.vertices(sampler.sample(stamp))@rotation.T+shift
        predicted = value['center_vertices']+(stamp-value['center_s'])*value['center_velocities']
        assert np.all(np.linalg.norm(actual-predicted, axis=1) <= value['remainder_radius_m'])
