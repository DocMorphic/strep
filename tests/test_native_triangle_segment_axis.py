"""Joint nine-line ranking against independent small linear programs."""
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.optimize import linprog
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_triangle_segment_axis import choose, segment_scores
from native_triangle_control_axis import candidate_axes


def maximum(gaps, slopes):
    result = linprog([0., -1.], A_ub=np.c_[-slopes, np.ones(9)], b_ub=gaps,
        bounds=[(0., 1.), (None, None)], method='highs')
    assert result.success
    return float(result.x[1])


def fixture(n=3):
    left = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    right = left+np.array([.1, .2, .4])
    rng = np.random.default_rng(7041)
    return left, right, rng.normal(size=(3, 3, n)), rng.normal(size=(3, 3, n)), rng.normal(size=n)


def test_common_fraction_rejects_incompatible_independent_row_maxima():
    gaps = np.array([[0., 1., 2., 2., 2., 2., 2., 2., 2.]])
    slopes = np.array([[1., -1., 0., 0., 0., 0., 0., 0., 0.]])
    score, fraction = segment_scores(gaps, slopes)
    assert np.minimum(gaps, gaps+slopes).shape == (1, 9)
    assert np.maximum(gaps, gaps+slopes).min() == 1.
    assert score[0] == .5 and fraction[0] == .5


@pytest.mark.parametrize('seed', range(5))
def test_complete_nine_line_scores_match_independent_linear_programs(seed):
    rng = np.random.default_rng(seed)
    gaps, slopes = rng.normal(size=(2, 36, 9))
    scores, fractions = segment_scores(gaps, slopes)
    for g, s, value, fraction in zip(gaps, slopes, scores, fractions):
        assert 0 <= fraction <= 1
        assert value == pytest.approx(maximum(g, s), abs=2e-10)
        assert value == float((g+fraction*s).min())


def test_constant_plateau_prefers_zero_fraction():
    score, fraction = segment_scores(np.ones((2, 9)), np.zeros((2, 9)))
    np.testing.assert_array_equal(score, [1., 1.])
    np.testing.assert_array_equal(fraction, [0., 0.])


def test_complete_axes_and_all_vertices_match_independent_line_programs():
    left, right, jl, jr, step = fixture()
    axes = candidate_axes(left, right)
    normal, report = choose(left, right, jl, jr, step, baseline_normal=axes[5])
    expected = []
    for axis in axes:
        gaps = ((left@axis)[:, None]-(right@axis)[None, :]).ravel()
        slopes = np.einsum('ijkc,k,c->ij', jl[:, None]-jr[None, :], axis, step).ravel()
        expected.append(maximum(gaps, slopes))
    assert report['selected_joint_segment_gap_m'] == pytest.approx(max(expected), abs=2e-10)
    np.testing.assert_array_equal(normal, axes[report['selected_index']])
    assert report['all_nine_pairs_scored_per_direction'] and report['common_fraction_per_triangle']
    assert not report['native_segment_endpoints_checked'] and not report['simultaneous_affine_feasibility_proven']
    assert not report['nonlinear_geometry_infeasibility_proven'] and not report['quality_approved']


def test_ninety_sixth_control_is_used_and_inputs_remain_immutable():
    left, _, _, _, _ = fixture()
    right = left+[0., 0., 1.]
    jl = np.zeros((3, 3, 96));jr = np.zeros_like(jl);jl[:, 2, -1] = -1.
    step = np.zeros(96);step[-1] = 1.
    originals = [v.copy() for v in (left, right, jl, jr, step)]
    _, stationary = choose(left, right, jl, jr, np.zeros(96))
    normal, moving = choose(left, right, jl, jr, step)
    assert moving['selected_joint_segment_gap_m'] == 2.
    assert stationary['selected_joint_segment_gap_m'] == 1.
    assert moving['selected_fraction'] == 1.
    for actual, original in zip((left, right, jl, jr, step), originals):
        np.testing.assert_array_equal(actual, original)
    normal[:] = 0
    np.testing.assert_array_equal(left, originals[0])


def test_supplied_baseline_and_both_orientations_remain_even_outside_face_edge_family():
    left, right, jl, jr, step = fixture()
    baseline = np.array([.31, .52, .73]);baseline /= np.linalg.norm(baseline)
    axes = candidate_axes(left, right)
    _, report = choose(left, right, jl, jr, step, baseline_normal=baseline)
    assert report['candidate_directions'] == len(axes)+2
    assert report['baseline_index'] == len(axes)


@pytest.mark.parametrize('fault', ['empty', 'subset', 'too-many', 'shape', 'bool', 'complex', 'nan', 'overflow'])
def test_invalid_line_population_rejects_without_partial_scores(fault):
    gaps = np.zeros((1, 9));slopes = np.ones_like(gaps)
    if fault == 'empty':gaps = slopes = np.zeros((0, 9))
    elif fault == 'subset':gaps = slopes = np.zeros((1, 8))
    elif fault == 'too-many':gaps = slopes = np.zeros((37, 9))
    elif fault == 'shape':slopes = np.zeros((2, 9))
    elif fault == 'bool':gaps = gaps.astype(bool)
    elif fault == 'complex':slopes = slopes.astype(complex)
    elif fault == 'nan':slopes[0, -1] = np.nan
    elif fault == 'overflow':slopes[0, :2] = [1e308, -1e308]
    with pytest.raises(ValueError):segment_scores(gaps, slopes)


@pytest.mark.parametrize('fault', ['degenerate', 'missing-vertex', 'missing-control', 'too-many', 'nan', 'overflow', 'baseline-shape', 'baseline-unit'])
def test_invalid_complete_triangle_input_rejects(fault):
    left, right, jl, jr, step = fixture();extra = {}
    if fault == 'degenerate':left[:] = 0.
    elif fault == 'missing-vertex':jl = jl[:2]
    elif fault == 'missing-control':step = step[:-1]
    elif fault == 'too-many':jl = jr = np.zeros((3, 3, 97));step = np.zeros(97)
    elif fault == 'nan':jr[-1, -1, -1] = np.nan
    elif fault == 'overflow':jl[:] = 1e308;step[:] = 1e308
    elif fault == 'baseline-shape':extra['baseline_normal'] = [1., 0.]
    elif fault == 'baseline-unit':extra['baseline_normal'] = [2., 0., 0.]
    with pytest.raises(ValueError):choose(left, right, jl, jr, step, **extra)
