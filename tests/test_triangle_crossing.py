import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
from triangle_crossing import classify, audit
from bounded_partner_surface import penetration


A = np.array([[-2., -1., 0.], [2., -1., 0.], [0., 2., 0.]])
B = np.array([[0., 0., -1.], [0., 0., 1.], [0., 1., 0.]])


def test_transverse_crossing_has_analytic_interval():
    result = classify(A, B)
    assert result['kind'] == 'proper_crossing'
    assert result['overlap_length_m'] == pytest.approx(1.)


def test_swap_winding_rigid_transform_and_scale_invariance():
    rng = np.random.default_rng(715)
    for scale in [.001, 1., 1000.]:
        for _ in range(8):
            rotation = Rotation.random(random_state=rng).as_matrix()
            translation = rng.uniform(-100, 100, 3)
            a, b = [(x[rng.permutation(3)] @ rotation.T)*scale+translation for x in [A, B]]
            for left, right in [(a, b), (b, a)]:
                result = classify(left, right, 1e-8*scale)
                assert result['kind'] == 'proper_crossing'
                assert result['overlap_length_m'] == pytest.approx(scale, abs=1e-10)


@pytest.mark.parametrize('other', [B+[0,4,0], A+[0,0,1], A+[7,0,0]])
def test_nonintersecting_triangles(other):
    assert classify(A, other)['kind'] == 'disjoint'


def test_coplanar_overlap_and_boundary_are_not_proper_crossings():
    assert classify(A, A*.5)['kind'] == 'coplanar_or_near_parallel_overlap'
    assert classify(A, B+[0,2,0])['kind'] == 'boundary_or_near_contact'
    assert classify(A, A+[0,0,1e-9])['kind'] == 'coplanar_or_near_parallel_overlap'


def test_degenerate_and_invalid_geometry():
    assert classify(A, np.zeros((3,3)))['kind'] == 'degenerate'
    with pytest.raises(ValueError): classify(A, B*np.nan)
    with pytest.raises(ValueError): classify(A, B, 0)
    with pytest.raises(ValueError): audit(A, [[0.,1.,2.]], B, [[0,1,2]])


def test_crossed_closed_boxes_with_no_vertices_inside():
    left = trimesh.creation.box(extents=[4,.5,.5])
    right = trimesh.creation.box(extents=[.5,4,1])
    for source, target in [(left,right),(right,left)]:
        assert penetration(source.vertices,target.vertices,target.faces)['max_depth_m'] == 0
    result = audit(left.vertices,left.faces,right.vertices,right.faces)
    assert result['counts'].get('proper_crossing',0) > 0
    assert not result['collision_free_certified']


def test_containment_still_requires_vertex_test():
    inner, outer = [trimesh.creation.box(extents=[s,s,s]) for s in [.5,2.]]
    result = audit(inner.vertices,inner.faces,outer.vertices,outer.faces)
    assert result['candidate_pairs'] == 0
    assert penetration(inner.vertices,outer.vertices,outer.faces)['max_depth_m'] > .5
    assert not result['collision_free_certified']


def test_spatial_index_preserves_all_bruteforce_intersections():
    rng = np.random.default_rng(291)
    left,right=[rng.uniform(-1,1,(12,3,3)) for _ in range(2)]
    expected={(i,j) for i,a in enumerate(left) for j,b in enumerate(right) if classify(a,b)['kind']!='disjoint'}
    result=audit(left.reshape(-1,3),np.arange(36).reshape(-1,3),right.reshape(-1,3),np.arange(36).reshape(-1,3))
    assert {(r['left_triangle'],r['right_triangle']) for r in result['records']} == expected


def test_whole_bounds_separation_skips_index_but_keeps_every_degenerate_face(monkeypatch):
    import triangle_crossing
    def forbidden(*args, **kwargs): raise AssertionError('Separated bounds need no spatial index')
    monkeypatch.setattr(triangle_crossing.index, 'Index', forbidden)
    left = np.vstack([A, np.zeros((3, 3))])
    right = B + [10., 0., 0.]
    result = audit(left, [[0, 1, 2], [3, 4, 5]], right, [[0, 1, 2]])
    assert result['whole_bounds_rejected'] and result['candidate_pairs'] == 0
    assert result['left_faces'] == 2 and result['degenerate_faces'] == [[1], []]
    assert not result['collision_free_certified']


def test_near_touching_bounds_never_use_whole_box_rejection():
    result = audit(A, [[0, 1, 2]], A + [0., 0., 1e-9], [[0, 1, 2]], tolerance_m=1e-8)
    assert not result['whole_bounds_rejected'] and result['candidate_pairs'] == 1
    assert result['records'][0]['kind'] == 'coplanar_or_near_parallel_overlap'
