import sys
from pathlib import Path
import numpy as np
import pytest
import trimesh
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from vertex_exit_witnesses import extract, gaps, VertexExitObjective


def test_closed_mesh_inside_vertex_has_correct_exit_distance():
    mesh = trimesh.creation.box()
    points = np.array([[.1, .2, .3], [2., 0, 0], [.5, 0, 0]])
    report = extract(points, mesh.vertices, mesh.faces)
    rows = report['witnesses']; assert len(rows) == 1 and rows[0]['vertex'] == 0
    row = rows[0]
    assert row['initial_distance_m'] == pytest.approx(.2)
    actual = gaps(points[[0]], mesh.vertices[[row['target_vertices']]], [row['barycentric']], [row['exit_normal']])
    np.testing.assert_allclose(actual, [-.2])
    assert report['full_mesh_validation_required'] and not report['quality_approved']


def test_moving_partner_and_source_both_change_exit_gap():
    p = np.array([[0., 0, -.2]]); t = np.array([[[0., 0, 0], [1, 0, 0], [0, 1, 0]]])
    b = [[1., 0, 0]]; n = [[0., 0, 1]]
    np.testing.assert_allclose(gaps(p+[0, 0, .1], t, b, n), [-.1])
    np.testing.assert_allclose(gaps(p, t+[0, 0, .1], b, n), [-.3])
    np.testing.assert_allclose(gaps(p+[2, 3, 4], t+[2, 3, 4], b, n), [-.2])


def test_rotating_and_translating_geometry_preserves_depth():
    from scipy.spatial.transform import Rotation
    mesh = trimesh.creation.box(); p = np.array([[.1, .2, .3]])
    rotation = Rotation.from_rotvec([.2, .4, -.1]).as_matrix(); shift = [1, 2, 3]
    row = extract(p@rotation.T+shift, mesh.vertices@rotation.T+shift, mesh.faces)['witnesses'][0]
    assert row['initial_distance_m'] == pytest.approx(.2)


def test_outside_vertices_do_not_imply_collision_free_surface():
    mesh = trimesh.creation.box()
    report = extract([[1., 0, 0], [-1, 0, 0]], mesh.vertices, mesh.faces)
    assert report['witnesses'] == [] and report['full_mesh_validation_required']
    objective = VertexExitObjective([None, None], [{}, {}], [[], []])
    assert objective.depths([None, None]).shape == (0,)


def test_invalid_barycentric_and_open_target_rejected():
    with pytest.raises(ValueError, match='convex'):
        gaps([[0, 0, 0]], np.zeros((1, 3, 3)), [[-1, 1, 1]], [[0, 0, 1]])
    mesh = trimesh.creation.box()
    with pytest.raises(ValueError, match='Closed'):
        extract([[0, 0, 0]], mesh.vertices, mesh.faces[:-1])
