import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from proximity_candidate_filter import filter_faces, ProximityMesh, line_box_candidates


def test_filter_preserves_order_and_excludes_only_distant_bounding_spheres():
    centers = np.array([[0, 0, 0], [3, 0, 0], [0, 1.01, 0], [5, 5, 5.]])
    radii = np.array([.1, .1, .02, .1]); ids = np.array([3, 2, 1, 0])
    kept = filter_faces(ids, [-1]*3, [1]*3, centers, radii, 1e-8)
    assert kept.tolist() == [2, 0]


def test_near_tied_squared_distances_stay_inside_the_ambiguity_band():
    centers = np.array([[.001002, 0, 0], [.001, 0, 0], [10, 0, 0.]])
    assert filter_faces(np.arange(3), [-.001]*3, [.001]*3, centers, np.zeros(3), 1e-8).tolist() == [0, 1]


def test_point_on_any_retained_triangle_within_radius_cannot_be_filtered_out():
    rng = np.random.default_rng(2903); triangles = rng.normal(size=(400, 3, 3)); centers = triangles.mean(1)
    radii = np.linalg.norm(triangles-centers[:, None], axis=2).max(1); weights = rng.dirichlet([1, 1, 1], size=400)
    witnesses = np.einsum('ni,nij->nj', weights, triangles); query = np.array([.2, -.3, .4]); radius = .7
    known_close = np.flatnonzero(np.linalg.norm(witnesses-query, axis=1) <= radius)
    selected = filter_faces(np.arange(400), query-radius, query+radius, centers, radii, 1e-8)
    assert set(known_close) <= set(selected)


def test_empty_filter_falls_back_to_original_candidates():
    ids = np.arange(3)
    np.testing.assert_array_equal(filter_faces(ids, [-1]*3, [1]*3, np.full((3, 3), 100.), np.zeros(3), 1e-8), ids)


@pytest.mark.parametrize('shape', ['box', 'sphere'])
def test_actual_trimesh_distances_match_for_interior_exterior_and_surface(shape):
    trimesh = pytest.importorskip('trimesh'); pytest.importorskip('rtree')
    mesh = trimesh.creation.box() if shape == 'box' else trimesh.creation.icosphere(subdivisions=2)
    rng = np.random.default_rng(802); points = np.r_[rng.uniform(-2, 2, (64, 3)), mesh.vertices[:12], np.zeros((1, 3))]
    proxy = ProximityMesh(mesh); before = trimesh.proximity.signed_distance(mesh, points)
    after = trimesh.proximity.signed_distance(proxy, points)
    np.testing.assert_allclose(after, before, atol=1e-12, rtol=0)
    assert proxy.triangles_tree.retained_candidates <= proxy.triangles_tree.raw_candidates
    assert proxy.ray is mesh.ray


def test_line_slab_filter_keeps_parallel_edge_and_behind_origin_hits():
    lower = np.array([[1, 0, 0], [-2, 0, 0], [1, 2, 0], [1, 1, 0.]])
    upper = lower+1
    assert line_box_candidates([0, 1, .5], [1, 0, 0], lower, upper).tolist() == [True, True, False, True]


def test_line_filter_never_excludes_known_triangle_intersections():
    rng = np.random.default_rng(412); triangles = rng.normal(size=(200, 3, 3)); weights = rng.dirichlet([1, 1, 1], size=200)
    targets = np.einsum('ni,nij->nj', weights, triangles); origin = np.array([.2, -.5, 1.])
    for triangle, target in zip(triangles, targets):
        assert line_box_candidates(origin, target-origin, triangle.min(0)[None], triangle.max(0)[None])[0]


@pytest.mark.parametrize('shape', ['box', 'sphere'])
def test_filtered_ray_parity_and_signed_distances_match_library(shape):
    trimesh = pytest.importorskip('trimesh'); pytest.importorskip('rtree')
    mesh = trimesh.creation.box() if shape == 'box' else trimesh.creation.icosphere(subdivisions=2)
    points = np.random.default_rng(671).uniform(-1.2, 1.2, (128, 3))
    proxy = ProximityMesh(mesh, filter_rays=True)
    np.testing.assert_array_equal(proxy.ray.contains_points(points), mesh.ray.contains_points(points))
    np.testing.assert_allclose(trimesh.proximity.signed_distance(proxy, points), trimesh.proximity.signed_distance(mesh, points), atol=1e-12, rtol=0)
    assert proxy.ray.statistics['retained_candidates'] < proxy.ray.statistics['raw_candidates']
