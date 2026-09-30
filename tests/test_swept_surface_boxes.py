import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from swept_surface_boxes import audit, boxes


def bound(points, radius=0.):
    return dict(start_s=0., center_s=.5, end_s=1., center_vertices=np.asarray(points, float),
                radius_m=np.full(len(points), radius))


A = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0]])
F = np.array([[0, 1, 2]])


def test_static_separation_and_uncertain_motion_are_distinct():
    left, right = bound(A), bound(A+[0, 0, 2])
    result = audit(left, F, right, F)
    assert result['outcome'] == 'surface_separation_bound'
    assert not result['collision_free_certified']
    right['radius_m'][:] = 2.1
    assert audit(left, F, right, F)['outcome'] == 'unresolved'


def test_swept_boxes_include_transit_even_when_both_endpoints_are_separated():
    # Moving triangle at z=-2 and +2 has clear endpoint poses, but crosses A.
    left, right = bound(A), bound(A, 2.)
    assert audit(left, F, right, F)['candidate_pairs'] == 1
    for z in [-2, 2]: assert audit(left, F, bound(A+[0, 0, z]), F)['candidate_pairs'] == 0


def test_spatial_index_matches_exhaustive_boxes_without_candidate_truncation():
    rng = np.random.default_rng(99)
    a, b = [bound(rng.normal(size=(60, 3)), .05) for _ in range(2)]
    faces = np.arange(60).reshape(-1, 3)
    al, ah = boxes(a, faces); bl, bh = boxes(b, faces)
    expected = sum(np.all(lo-1e-8 <= high) and np.all(hi+1e-8 >= low)
                   for lo, hi in zip(al, ah) for low, high in zip(bl, bh))
    result = audit(a, faces, b, faces)
    assert result['candidate_pairs'] == expected > 16
    assert len(result['example_pairs']) == 16 and result['examples_truncated']


def test_changed_clock_negative_radius_and_bad_faces_fail():
    left, right = bound(A), bound(A)
    right['end_s'] = 2.
    with pytest.raises(ValueError, match='clock'): audit(left, F, right, F)
    right = bound(A, -1.)
    with pytest.raises(ValueError): audit(left, F, right, F)
    with pytest.raises(ValueError): audit(left, F.astype(float), bound(A), F)
