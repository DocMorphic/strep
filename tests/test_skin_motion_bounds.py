import sys
from pathlib import Path
from types import SimpleNamespace, MethodType
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from skin_motion_bounds import SkinMotionBounds, angular_bound


def fixture(channels):
    # Non-topological node ordering, two skin influences, nonidentity inverse
    # bind, and an unskinned primitive exercise the actual production sampler.
    document = dict(nodes=[dict(translation=[2., 0, 0]), dict(children=[0])])
    sampler = object.__new__(AnimationSampler)
    sampler.document = document; sampler.channels = channels; sampler.duration = 1.
    rig = SimpleNamespace(document=document, parents=[1, -1], joints=[1, 0],
        inverse=np.repeat(np.eye(4)[None], 2, axis=0))
    rig.inverse[1, 0, 3] = -1.
    rig.primitives = [dict(node=0, positions=np.array([[3., 0, 0], [0, 1., 0]]),
        joints=np.array([[0, 1], [1, 0]]), weights=np.array([[.25, .75], [.8, .2]])),
        dict(node=0, positions=np.array([[1., 0, 0]]), joints=None)]
    rig.vertices = MethodType(RigAsset.vertices, rig)
    return rig, sampler


def channel(node, path, values, times=(0., 1.), mode='LINEAR'):
    return (node, path, np.asarray(times), np.asarray(values, float), mode)


def assert_enclosed(rig, sampler, result, count=121):
    poses = np.array([rig.vertices(sampler.sample(t)) for t in np.linspace(result['start_s'], result['end_s'], count)])
    distance = np.linalg.norm(poses-result['center_vertices'], axis=2)
    assert np.all(distance <= result['radius_m']+1e-12)
    rates = np.linalg.norm(np.diff(poses, axis=0), axis=2)/((result['end_s']-result['start_s'])/(count-1))
    assert np.all(rates <= result['speed_bound_m_s']+1e-10)


def test_uniform_translation_bound_is_tight_and_keeps_vertex_order():
    rig, sampler = fixture([channel(1, 'translation', [[0, 0, 0], [2, 0, 0]])])
    result = SkinMotionBounds(rig, sampler).interval(0., 1.)
    np.testing.assert_allclose(result['speed_bound_m_s'], [2., 2., 2.], atol=1e-10)
    np.testing.assert_allclose(result['radius_m'], [1., 1., 1.], atol=2e-10)
    assert_enclosed(rig, sampler, result)


def test_rotating_hierarchy_with_moving_joint_and_blended_skin():
    q = Rotation.from_euler('z', [0, 120], degrees=True).as_quat()
    rig, sampler = fixture([channel(1, 'rotation', q), channel(0, 'rotation', q),
        channel(1, 'translation', [[0, 0, 0], [1, 0, 0]]),
        channel(0, 'translation', [[2, 0, 0], [3, 0, 0]])])
    result = SkinMotionBounds(rig, sampler).interval(.1, .95)
    assert_enclosed(rig, sampler, result)
    assert not result['collision_free_certified']


def test_returning_arc_does_not_use_endpoint_vertex_interpolation():
    q = Rotation.from_euler('z', [0, 180, 360], degrees=True).as_quat()
    rig, sampler = fixture([channel(1, 'rotation', q, times=(0, .5, 1))])
    start, middle, end = [rig.vertices(sampler.sample(t)) for t in [0., .5, 1.]]
    np.testing.assert_allclose(start, end, atol=1e-14)
    assert np.linalg.norm(middle-start, axis=1).max() > 5
    result = SkinMotionBounds(rig, sampler).interval(0., 1.)
    assert result['native_spans'] == 2
    assert_enclosed(rig, sampler, result)


def test_native_knots_and_clamped_channel_ends_are_split():
    rig, sampler = fixture([channel(1, 'translation', [[0, 0, 0], [1, 0, 0], [0, 0, 0]], times=(.2, .25, .8))])
    bound = SkinMotionBounds(rig, sampler)
    result = bound.interval(0., 1.)
    assert result['native_spans'] == 4
    np.testing.assert_allclose(result['speed_bound_m_s'], 20., atol=1e-9)
    np.testing.assert_allclose(bound.interval(.8, 1.)['speed_bound_m_s'], 0., atol=1e-100)
    assert_enclosed(rig, sampler, result)


@pytest.mark.parametrize('angle', [1e-10, 1e-7, .5, np.pi])
def test_shortest_arc_and_small_angle_sampler_are_bounded(angle):
    a, b = Rotation.from_rotvec([[0, 0, 0], [0, 0, angle]]).as_quat()
    rate = angular_bound(a, -b, 2.)
    assert rate >= angle/2 - 1e-14
    assert rate == pytest.approx(angular_bound(a, b, 2.))
    values = np.array([a, -b]); times = np.array([0., 2.])
    q = [AnimationSampler.value('rotation', times, values, 'LINEAR', t) for t in np.linspace(0, 2, 51)]
    actual = (Rotation.from_quat(q[1:])*Rotation.from_quat(q[:-1]).inv()).magnitude()/.04
    assert actual.max() <= rate+1e-12


def test_constant_step_is_bounded_but_jumps_cubic_and_scale_drift_are_explicit():
    rig, sampler = fixture([channel(1, 'translation', [[1, 0, 0], [1, 0, 0]], mode='STEP')])
    result = SkinMotionBounds(rig, sampler).interval(0, 1)
    assert_enclosed(rig, sampler, result)
    for bad, message in [
        (channel(1, 'translation', [[0, 0, 0], [1, 0, 0]], mode='STEP'), 'jump'),
        (channel(1, 'translation', np.zeros((6, 3)), mode='CUBICSPLINE'), 'CUBICSPLINE'),
        (channel(1, 'scale', [[1, 1, 1], [1.000001, 1, 1]]), 'scale')]:
        rig, sampler = fixture([bad])
        with pytest.raises(ValueError, match=message): SkinMotionBounds(rig, sampler)


def test_static_scale_drift_and_homogeneous_bind_component_are_accounted_for():
    rig, sampler = fixture([channel(1, 'rotation', Rotation.from_euler('z', [0, 60], degrees=True).as_quat()),
                            channel(1, 'translation', [[0, 0, 0], [2, 0, 0]])])
    rig.document['nodes'][1]['scale'] = [1.000001, 1., 1.]
    rig.inverse[1, 3, 0] = 1e-6
    assert_enclosed(rig, sampler, SkinMotionBounds(rig, sampler).interval(0, 1))


@pytest.mark.parametrize('interval', [(0, 0), (-1, 1), (0, 2), (1, 0), (0, np.nan)])
def test_invalid_intervals_rejected(interval):
    rig, sampler = fixture([channel(1, 'translation', np.zeros((2, 3)))])
    with pytest.raises(ValueError): SkinMotionBounds(rig, sampler).interval(*interval)
