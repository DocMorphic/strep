import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from swept_triangle_separation import pair_bounds, audit
from swept_surface_boxes import audit as box_audit


A = np.array([[0., 0, 0], [2, 0, 0], [0, 2, 0]])
B = A+[1.5, 1.5, 0]
F = np.array([[0, 1, 2]])


def bound(vertices, radius=0.):
    return dict(start_s=0., center_s=.5, end_s=1., center_vertices=vertices,
                radius_m=np.full(len(vertices), radius))


def test_diagonal_separation_resolves_overlapping_axis_aligned_boxes():
    left, right = bound(A, .1), bound(B, .1)
    assert box_audit(left, F, right, F)['outcome'] == 'unresolved'
    result = audit(left, F, right, F)
    assert result['outcome'] == 'surface_separation_bound'
    assert result['checked_pairs'] == result['candidate_pairs'] == 1
    assert result['minimum_tested_margin_m'] == pytest.approx(1/np.sqrt(2)-.2-1e-8, abs=1e-12)
    assert not result['collision_free_certified']


def test_expanding_motion_balls_and_touching_triangles_remain_unresolved():
    assert audit(bound(A, .4), F, bound(B, .4), F)['outcome'] == 'unresolved'
    for other in [A, A+[1, 1, 0], np.array([[0., 0, -1], [0, 0, 1], [0, 1, 0]])]:
        assert not pair_bounds(A[None], np.zeros((1, 3)), other[None], np.zeros((1, 3)))['separated'][0]


def test_rotation_translation_winding_and_actor_swap_preserve_separation():
    rng = np.random.default_rng(83)
    for _ in range(20):
        rotation = Rotation.random(random_state=rng).as_matrix(); shift = rng.normal(size=3)*100
        a, b = [x[rng.permutation(3)]@rotation.T+shift for x in [A, B]]
        for x, y in [(a, b), (b, a)]:
            assert pair_bounds(x[None], np.full((1, 3), .1), y[None], np.full((1, 3), .1))['separated'][0]


def test_returned_axis_separates_every_sampled_ball_perturbation():
    rng = np.random.default_rng(88)
    a, b = np.repeat(A[None], 30, axis=0), np.repeat(B[None], 30, axis=0)
    ra, rb = [rng.uniform(0, .1, (30, 3)) for _ in range(2)]
    result = pair_bounds(a, ra, b, rb)
    assert result['separated'].all()
    for _ in range(20):
        moves = [rng.normal(size=(30, 3, 3)) for _ in range(2)]
        moves = [v/np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-12)*r[:, :, None]
                 for v, r in zip(moves, [ra, rb])]
        left, right = [np.einsum('nvi,ni->nv', x+move, result['axes']) for x, move in zip([a, b], moves)]
        assert np.all(right.min(axis=1)-left.max(axis=1) >= result['margin_m'])


def test_budget_never_treats_untested_pairs_as_separated():
    vertices = np.tile(A, (4, 1)); faces = np.arange(12).reshape(4, 3)
    result = audit(bound(vertices), faces, bound(np.tile(B, (4, 1))), faces, candidate_limit=2)
    assert result['candidate_pairs'] == 16 and result['checked_pairs'] == 0
    assert result['outcome'] == 'unresolved' and result['reason'] == 'candidate_budget'


def test_all_pairs_checked_and_batch_failure_is_explicit():
    vertices = np.tile(A, (4, 1)); faces = np.arange(12).reshape(4, 3)
    separated = audit(bound(vertices), faces, bound(np.tile(B, (4, 1))), faces, batch_size=3)
    assert separated['outcome'] == 'surface_separation_bound' and separated['checked_pairs'] == 16
    overlapping = audit(bound(vertices), faces, bound(vertices), faces, batch_size=3)
    assert overlapping['outcome'] == 'unresolved' and overlapping['checked_pairs'] == 3
    assert overlapping['untested_pairs'] == 13 and overlapping['unresolved_examples']


def test_large_coordinates_receive_nonzero_projection_reserve():
    result = pair_bounds((A+1e9)[None], np.zeros((1, 3)), (B+1e9)[None], np.zeros((1, 3)))
    assert result['projection_reserve_m'][0] > 1e-5 and result['separated'][0]


@pytest.mark.parametrize('kwargs', [dict(candidate_limit=0), dict(candidate_limit=True), dict(batch_size=0), dict(tolerance_m=-1)])
def test_invalid_limits_rejected(kwargs):
    with pytest.raises(ValueError): audit(bound(A), F, bound(B), F, **kwargs)


def test_invalid_radii_and_shapes_rejected():
    with pytest.raises(ValueError): pair_bounds(A[None], -np.ones((1, 3)), B[None], np.zeros((1, 3)))
    with pytest.raises(ValueError): pair_bounds(A, np.zeros(3), B, np.zeros(3))
    with pytest.raises(ValueError): pair_bounds(A[None]*np.nan, np.zeros((1, 3)), B[None], np.zeros((1, 3)))
