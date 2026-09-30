import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from joint_angular_rates import angular_vectors, compare_angular_rates


def track(angles):
    return Rotation.from_rotvec(np.asarray(angles)[:, None]*np.array([0., 0., 1.])).as_matrix()[:, None]


def compare(a, b, t):
    return compare_angular_rates(a, b, t, [t[0], t[len(t)//2], t[-1]], ['wrist'], speed_tolerance=1e-5, acceleration_tolerance=1e-5)


def test_stationary_joint_origin_can_have_excessive_angular_motion():
    t = np.arange(9)/120; source = track(t*0); candidate = track(np.array([0, 0, 0, .02, .04, .02, 0, 0, 0]))
    result = compare(source, candidate, t)
    assert result['angular_speed_rad_s']['maximum_increase'] == pytest.approx(2.4)
    assert result['angular_acceleration_rad_s2']['maximum_increase'] == pytest.approx(576.)
    assert result['angular_speed_rad_s']['exceeding_observations'] > 0


def test_constant_spin_and_time_scaling():
    t = np.arange(9)/120; r = track(2*t); a = angular_vectors(r, t); b = angular_vectors(r, 2*t)
    np.testing.assert_allclose(a[0][0][:, 0], np.tile([0, 0, 2], (8, 1)), atol=1e-12)
    np.testing.assert_allclose(a[1][0], 0, atol=1e-10)
    np.testing.assert_allclose(b[0][0], a[0][0]/2, atol=1e-12)
    np.testing.assert_allclose(b[1][0], a[1][0]/4, atol=1e-10)


def test_rotating_the_world_frame_preserves_rate_norms():
    t = np.arange(17)/120; r = track(3*t*t)
    placement = Rotation.from_euler('xyz', [.6, -.8, .9]).as_matrix()
    for (a, _), (b, _) in zip(angular_vectors(r, t), angular_vectors(placement@r, t)):
        np.testing.assert_allclose(np.linalg.norm(a, axis=2), np.linalg.norm(b, axis=2), atol=1e-10)


def test_quaternion_sign_does_not_change_rotation_rates():
    t = np.arange(9)/120; q = Rotation.from_rotvec(t[:, None]*[0, 1., 0]).as_quat(); q[1::2] *= -1
    matrices = Rotation.from_quat(q).as_matrix()[:, None]
    result = compare(matrices, matrices, t)
    assert all(r['exceeding_observations'] == 0 for r in result.values())


@pytest.mark.parametrize('fault', ['scale', 'reflection', 'shear', 'nan', 'clock', 'pi'])
def test_invalid_or_ambiguous_angular_tracks_are_rejected(fault):
    t = np.arange(9)/120; r = track(t)
    if fault == 'scale': r *= 2
    if fault == 'reflection': r[..., 0] *= -1
    if fault == 'shear': r[:, :, 0, 1] += .1
    if fault == 'nan': r[0, 0, 0, 0] = np.nan
    if fault == 'clock': t[4] += .001
    if fault == 'pi': r[4, 0] = Rotation.from_rotvec([np.pi, 0, 0]).as_matrix(); r[3, 0] = np.eye(3)
    with pytest.raises(ValueError): angular_vectors(r, t)
