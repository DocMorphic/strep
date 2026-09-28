import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from grasp_orientation import align_direction, twist_target, angular_error


def test_alignment_handles_equal_opposite_and_oblique_directions():
    for target in ([0, 0, 1], [0, 0, -1], [1, 2, 3]):
        target = np.array(target, float); target /= np.linalg.norm(target)
        rotation = align_direction([0, 0, 1], target)
        np.testing.assert_allclose(rotation@[0, 0, 1], target, atol=1e-12)
        np.testing.assert_allclose(rotation.T@rotation, np.eye(3), atol=1e-12)
        assert abs(np.linalg.det(rotation)-1) < 1e-12


def test_twist_preserves_target_plane_and_signed_angle_after_alignment():
    normal = np.array([1., 2., 3.]); normal /= np.linalg.norm(normal)
    baseline = twist_target([0, 0, 1], [1, 0, 0], normal, 0)
    for degrees in [-20., -10., 0., 10., 20.]:
        tangent = twist_target([0, 0, 1], [1, 0, 0], normal, degrees)
        signed = np.rad2deg(np.arctan2(normal@np.cross(baseline, tangent), baseline@tangent))
        assert abs(signed-degrees) < 1e-10 and abs(tangent@normal) < 1e-12
        assert abs(np.linalg.norm(tangent)-1) < 1e-12


def test_degenerate_direction_is_rejected():
    with pytest.raises(ValueError): align_direction([0, 0, 0], [0, 0, 1])
    with pytest.raises(ValueError): twist_target([0, 0, 1], [0, 0, 1], [0, 0, 1], 10)
    assert angular_error([1, 0, 0], [0, 1, 0]) == 90.
