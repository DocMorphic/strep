"""Complete pair coverage and outward bounds precede local separation guards."""
from fractions import Fraction
from itertools import product
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_triangle_separation_guards as guards


def args(distance=.01, frames=1):
    triangle = np.array([[0., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    vertices = {'a': np.repeat(triangle[None], frames, axis=0),
                'b': np.repeat((triangle+[distance, 0., 0.])[None], frames, axis=0)}
    jac = {k: np.zeros((*v.shape, 1)) for k, v in vertices.items()}
    jac['a'][..., 0, 0] = 1.
    faces = {k: np.array([[0, 1, 2]]) for k in vertices}
    return [vertices, jac, faces, np.arange(frames, dtype=float), np.zeros(1), -np.ones(1), np.ones(1), .02]


def test_every_corner_pair_is_guarded_when_whole_box_can_reach_another_triangle():
    model = guards.build(*args())
    assert len(model.gaps_m) == 9 and model.jacobian.shape == (9, 1)
    np.testing.assert_allclose(model.gaps_m, .01, rtol=0., atol=0.)
    np.testing.assert_allclose(model.jacobian.toarray(), -1., rtol=0., atol=0.)
    assert model.clearances_m.tolist() == [1e-8]*9
    assert [(d['left_vertex'], d['right_vertex']) for d in model.descriptors] == list(product(range(3), repeat=2))
    frame = model.report['frames'][0]
    assert frame['triangle_pairs'] == frame['candidate_pairs'] == frame['positively_separated_pairs'] == 1
    assert frame['unresolved_pairs'] == [] and frame['whole_box_disjoint_pairs'] == 0
    assert not model.report['quality_approved'] and not model.report['release_approved']


def test_whole_box_separation_can_omit_rows_only_with_a_complete_pair_partition(monkeypatch):
    monkeypatch.setattr(guards, 'separation_axis', lambda *a: pytest.fail('Whole box already disjoint'))
    model = guards.build(*args(distance=1.))
    assert model.gaps_m.shape == (0,) and model.jacobian.shape == (0, 1)
    assert model.report['complete_triangle_pairs'] == model.report['frames'][0]['whole_box_disjoint_pairs'] == 1


def test_overlapping_anchor_is_reported_unresolved_without_a_false_guard():
    model = guards.build(*args(distance=0.))
    assert len(model.gaps_m) == 0 and model.report['frames'][0]['positively_separated_pairs'] == 0
    assert model.report['frames'][0]['unresolved_pairs'] == [dict(left_triangle=0, right_triangle=0, support_gap_m=0.)]


def test_positive_anchor_smaller_than_requested_clearance_gets_its_exact_starting_margin():
    model = guards.build(*args(distance=1e-10))
    assert model.clearances_m.tolist() == [1e-10]*9
    assert np.all(model.gaps_m >= model.clearances_m)


def test_every_actor_pair_frame_and_original_face_index_is_retained():
    a = args(frames=2)
    a[0]['c'] = a[0]['b']+[1., 0., 0.]
    a[1]['c'] = np.zeros_like(a[1]['b']); a[2]['c'] = a[2]['b'].copy()
    a[2]['a'] = np.array([[0, 1, 2], [0, 2, 1]])
    model = guards.build(*a)
    assert model.report['complete_triangle_pairs'] == 10 and len(model.report['frames']) == 6
    assert len(model.gaps_m) == 36
    assert {d['left_triangle'] for d in model.descriptors} == {0, 1}
    assert {d['time_s'] for d in model.descriptors} == {0., 1.}
    for frame in model.report['frames']:
        assert frame['triangle_pairs'] == frame['whole_box_disjoint_pairs']+frame['candidate_pairs']
        assert frame['candidate_pairs'] == frame['positively_separated_pairs']+len(frame['unresolved_pairs'])


def test_outward_bounds_enclose_exact_rational_affine_extrema_including_cancellation():
    points = np.array([[[.1, -.3, 1e-200]]])
    jac = np.array([[[[.3, -.7, 1e-200], [-.1, .9, 1e-200], [1e-200, -1e-200, 1e-200]]]])
    lo, hi = np.array([-.02, -.01, -.015]), np.array([.01, .02, .005])
    lower, upper = guards.coordinate_bounds(points, jac, lo, hi)
    for axis in range(3):
        base = Fraction(float(points[0, 0, axis]))
        lows, highs = [], []
        for j, a, b in zip(jac[0, 0, axis], lo, hi):
            products = [Fraction(float(j))*Fraction(float(v)) for v in (a, b)]
            lows.append(min(products)); highs.append(max(products))
        assert Fraction(float(lower[0, 0, axis])) <= base+sum(lows)
        assert Fraction(float(upper[0, 0, axis])) >= base+sum(highs)


def test_original_control_bounds_can_certify_separation_even_with_a_large_trust_radius():
    a = args(); a[6][0] = .001
    model = guards.build(*a)
    assert model.report['frames'][0]['whole_box_disjoint_pairs'] == 1
    assert len(model.gaps_m) == 0


def test_complete_resource_budget_failure_returns_no_subset(monkeypatch):
    monkeypatch.setattr(guards, 'separation_axis', lambda *a: pytest.fail('Pair budget before geometry'))
    a = args(frames=2)
    with pytest.raises(ValueError, match='resource budget'):
        guards.build(*a, maximum_triangle_pairs=1)
    with pytest.raises(ValueError, match='resource budget'):
        guards.build(*args(), maximum_elements=1)


def test_guard_row_budget_failure_returns_no_partial_population():
    with pytest.raises(ValueError, match='no subset'):
        guards.build(*args(), maximum_guard_rows=8)


@pytest.mark.parametrize('fault', ['actors', 'columns', 'vertices', 'nan', 'faces-float', 'faces-oob',
    'face-duplicate', 'degenerate', 'clock', 'box', 'trust', 'clearance', 'pair-budget'])
def test_malformed_complete_population_rejects(fault):
    a = args(); kw = {}
    if fault == 'actors': a[1].pop('b')
    elif fault == 'columns': a[1]['a'] = a[1]['a'][..., :0]
    elif fault == 'vertices': a[0]['a'] = a[0]['a'][..., :2]
    elif fault == 'nan': a[1]['a'][0, 0, 0, 0] = np.nan
    elif fault == 'faces-float': a[2]['a'] = a[2]['a'].astype(float)
    elif fault == 'faces-oob': a[2]['a'][0, 0] = 3
    elif fault == 'face-duplicate': a[2]['a'][0, 0] = 1
    elif fault == 'degenerate': a[0]['a'][0, 1] = a[0]['a'][0, 0]
    elif fault == 'clock': a[3] = [-1.]
    elif fault == 'box': a[5] = a[6].copy()
    elif fault == 'trust': a[7] = True
    elif fault == 'clearance': kw['clearance_m'] = True
    else: kw['maximum_triangle_pairs'] = True
    with pytest.raises(ValueError): guards.build(*a, **kw)


def test_returned_guard_arrays_are_detached_from_the_original_point_inputs():
    a = args(); old = {k:v.copy() for k,v in a[0].items()}
    model = guards.build(*a)
    model.gaps_m.fill(np.nan); model.jacobian.data.fill(np.nan); model.descriptors[0]['axis_world'][0] = np.nan
    for name in old: np.testing.assert_array_equal(a[0][name], old[name])
