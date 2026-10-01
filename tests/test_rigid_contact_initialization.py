import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rigid_contact_initialization import place, summarize


@pytest.mark.parametrize('normal', [[1., 0, 0], [0., 0, -1], [0., 0, 1]])
def test_contact_alignment_preserves_shape_and_winding(normal):
    points = np.array([[1., 2, 3], [2, 2, 3], [1, 3, 3]])
    anchor = points[0]; desired = np.array([.4, .5, .6]); target_normal = np.asarray(normal)
    transformed, rotation, translation = place(points, anchor, [0, 0, 1], desired, target_normal, 37.)
    np.testing.assert_allclose(transformed[0], desired, atol=1e-14)
    np.testing.assert_allclose(rotation@[0, 0, 1], target_normal, atol=1e-14)
    np.testing.assert_allclose(rotation.T@rotation, np.eye(3), atol=1e-14)
    assert np.linalg.det(rotation) == pytest.approx(1.)
    np.testing.assert_allclose(np.cross(transformed[1]-transformed[0], transformed[2]-transformed[0]), target_normal, atol=1e-14)
    np.testing.assert_allclose((transformed-translation)@rotation, points, atol=1e-14)


def test_azimuth_rotates_about_desired_anchor_not_world_origin():
    points = [[4, 2, 1], [5, 2, 1]]
    value, _, _ = place(points, points[0], [0, 0, 1], [7, 8, 9], [0, 0, 1], 90.)
    np.testing.assert_allclose(value, [[7, 8, 9], [7, 9, 9]], atol=1e-14)
    wrapped, _, _ = place(points, points[0], [0, 0, 1], [7, 8, 9], [0, 0, 1], 450.)
    np.testing.assert_allclose(value, wrapped, atol=1e-14)


def test_invalid_normals_and_nonfinite_geometry_rejected():
    for normal in ([0, 0, 0], [0, 0, 2], [0, 0, float('nan')]):
        with pytest.raises(ValueError): place([[0, 0, 0]], [0, 0, 0], normal, [0, 0, 0], [0, 0, 1])
    with pytest.raises(ValueError): place([[float('inf'), 0, 0]], [0, 0, 0], [0, 0, 1], [0, 0, 0], [0, 0, 1])


def test_screen_requires_no_containment_uncertainty_or_degeneracy():
    surface = dict(counts={'disjoint': 4}, degenerate_faces=[[], []])
    depths = [dict(max_depth_m=0.), dict(max_depth_m=0.)]
    result = summarize(surface, depths)
    assert result['sampled_hand_screen_pass']
    assert not result['rig_feasibility_verified'] and not result['animation_quality_approved']
    assert not result['collision_free_certified']
    assert not summarize(surface, [dict(max_depth_m=.001), depths[1]])['sampled_hand_screen_pass']
    for kind in ('proper_crossing', 'boundary_contact', 'coplanar_or_near_parallel_overlap'):
        assert not summarize(dict(surface, counts={kind: 1}), depths)['sampled_hand_screen_pass']
    assert not summarize(dict(surface, degenerate_faces=[[1], []]), depths)['sampled_hand_screen_pass']
