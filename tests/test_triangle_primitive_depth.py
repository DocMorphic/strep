"""Interior, degeneracy and independent dense-sample depth checks."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from triangle_primitive_depth import query


SHAPES = [Geometry('box', (2., 2., 2.)), Geometry('sphere', (1.,)), Geometry('cylinder', (1., 2.))]


@pytest.mark.parametrize('shape', SHAPES)
def test_triangle_interior_hits_solid_while_all_vertices_are_outside(shape):
    tri = np.array([[[-4., .25, -4.], [4., .25, -4.], [0., .25, 4.]]])
    assert not np.any(shape.penetration_depth(tri[0], np.zeros(3), np.eye(3)))
    out = query(tri, shape, [0, 0, 0], np.eye(3))
    expected = .75
    assert out['lower_m'][0] <= expected <= out['upper_m'][0]
    assert out['upper_m'][0] - out['lower_m'][0] <= 1e-6
    np.testing.assert_allclose(shape.penetration_depth(out['witnesses_world_m'], np.zeros(3), np.eye(3)),
        [expected], atol=1e-6)


@pytest.mark.parametrize('shape', SHAPES)
def test_rotated_translated_scene_preserves_depth_brackets(shape):
    tri = np.array([[[-3., .6, -3.], [3., .6, -3.], [0., .6, 3.]],
        [[2, 2, 2], [3, 2, 2], [2, 3, 2]]])
    r = Rotation.from_rotvec([.4, -.8, .2]).as_matrix(); p = np.array([.7, -.2, 1.3])
    out = query(tri @ r.T + p, shape, p, r)
    assert out['lower_m'][0] <= .4 <= out['upper_m'][0]
    assert out['upper_m'][1] == 0
    assert np.isfinite(out['witnesses_world_m']).all()


@pytest.mark.parametrize('shape', SHAPES)
def test_brackets_enclose_independent_dense_barycentric_oracle(shape):
    rng = np.random.default_rng(731); tri = rng.uniform(-1.5, 1.5, (25, 3, 3))
    out = query(tri, shape, [0, 0, 0], np.eye(3))
    uv = np.array([(i/100, j/100) for i in range(101) for j in range(101-i)])
    bary = np.column_stack((1-uv.sum(1), uv))
    for i, triangle in enumerate(tri):
        points = bary @ triangle
        dense = float(shape.penetration_depth(points, np.zeros(3), np.eye(3)).max())
        witness = float(shape.penetration_depth(out['witnesses_world_m'][i:i+1], np.zeros(3), np.eye(3))[0])
        assert dense <= out['upper_m'][i] + 1e-12
        assert out['lower_m'][i] <= witness + 1e-12
        assert witness <= out['upper_m'][i] + 1e-12
        # Cover radius of this independent triangle lattice bounds missed peaks.
        assert out['upper_m'][i] <= dense + np.linalg.norm(np.ptp(triangle, axis=0))/100 + 1e-6


@pytest.mark.parametrize('shape', SHAPES)
def test_tangent_and_degenerate_faces_are_retained(shape):
    tri = np.array([[[1, -.1, 0], [1, .1, 0], [1, 0, .1]],
        [[-2, 0, 0], [0, 0, 0], [2, 0, 0]]], dtype=float)
    out = query(tri, shape, [0, 0, 0], np.eye(3))
    assert out['lower_m'][0] == 0 and out['upper_m'][0] <= 1e-6
    assert out['degenerate_faces'].tolist() == [1]
    assert out['lower_m'][1] <= 1 <= out['upper_m'][1]
    assert not out['continuous_collision_certified'] and not out['exact_arithmetic_certified']


def test_cylinder_cap_and_radial_limits_both_apply():
    shape = Geometry('cylinder', (.2, 4.))
    tri = np.array([[[-2, 0, -2], [2, 0, -2], [0, 0, 2]],
        [[-2, 1.95, -2], [2, 1.95, -2], [0, 1.95, 2]]])
    out = query(tri, shape, [0, 0, 0], np.eye(3))
    for i, expected in enumerate([.2, .05]): assert out['lower_m'][i] <= expected <= out['upper_m'][i]


@pytest.mark.parametrize('fault', ['nan', 'empty', 'resolution-bool', 'resolution-small', 'rotation', 'scale'])
def test_invalid_queries_fail(fault):
    tri = np.array([[[0., 0, 0], [1, 0, 0], [0, 1, 0]]]); r = np.eye(3); resolution = 1e-6
    if fault == 'nan': tri[0, 0, 0] = np.nan
    if fault == 'empty': tri = tri[:0]
    if fault == 'resolution-bool': resolution = True
    if fault == 'resolution-small': resolution = 1e-15
    if fault == 'rotation': r[0, 0] = 2
    if fault == 'scale': tri += 1e10
    with pytest.raises(ValueError): query(tri, SHAPES[0], [0, 0, 0], r, resolution_m=resolution)
