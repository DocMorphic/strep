import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from hand_contact_plane import hand_region, plane_excess, measure


def test_region_uses_all_eight_weights_and_closes_triangle_seam():
    parents = [-1, 0, 1, 0]
    nodes = np.tile([3, 3, 3, 3, 2, 2, 2, 2], (4, 1))
    weights = np.array([[.1]*4+[.15]*4, [.2]*4+[.05]*4,
                        [.2]*4+[.05]*4, [.2]*4+[.05]*4])
    vertices, faces = hand_region(parents, 1, nodes, weights, [[0, 1, 2], [1, 2, 3]])
    np.testing.assert_array_equal(vertices, [0, 1, 2])
    np.testing.assert_array_equal(faces, [0])


def test_disjoint_plane_screen_cannot_approve_whole_mesh():
    points = np.array([[0, 0, -.001], [1, 0, -.002], [0, 1, -.003]])
    row = measure(points, [0, 0, 0], [0, 0, 1], 0)
    assert row['selected_surface_plane_pass'] and row['full_mesh_validation_required']
    assert not row['quality_approved']
    assert not measure(points, [0, 0, 0], [0, 0, 1], 1)['selected_surface_plane_pass']


def test_plane_values_bound_every_triangle_convex_combination():
    points = np.array([[0, 0, -.001], [1, 0, -.002], [0, 1, -.003]])
    weights = np.random.default_rng(13).dirichlet([1, 1, 1], 100)
    values = plane_excess(weights @ points, [0, 0, 0], [0, 0, 1], 0)
    assert np.all(values <= plane_excess(points, [0, 0, 0], [0, 0, 1], 0).max())


def test_rigid_scene_transform_preserves_excess():
    p = np.array([[1., 2, 3], [2, 1, 0]])
    mid = np.array([.1, .2, .3]); axis = np.array([0., 0, 1])
    r = Rotation.from_rotvec([.4, -.1, .2]).as_matrix(); shift = np.array([3., 4, 5])
    np.testing.assert_allclose(plane_excess(p @ r.T+shift, mid @ r.T+shift, axis @ r.T, 1),
                               plane_excess(p, mid, axis, 1))


def test_bad_hierarchy_and_weights_fail_closed():
    with pytest.raises(ValueError, match='Acyclic'):
        hand_region([1, 0], 0, [[0], [1], [0]], [[1], [1], [1]], [[0, 1, 2]])
    with pytest.raises(ValueError, match='normalized'):
        hand_region([-1], 0, [[0], [0], [0]], [[.2], [1], [1]], [[0, 1, 2]])


def test_invalid_plane_normal_and_actor_fail_closed():
    with pytest.raises(ValueError, match='unit'):
        plane_excess([[0, 0, 0]], [0, 0, 0], [0, 0, 2], 0)
    with pytest.raises(ValueError, match='actor'):
        plane_excess([[0, 0, 0]], [0, 0, 0], [0, 0, 1], True)
