"""Empirical response must supplement original constraints, never relax them."""
import sys
from pathlib import Path
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_observed_secant_model import augment
from native_material_grouped_crossing_step import direction
from native_triangle_separation_guards import SeparationGuards


def args():
    native = NormRows([[.01, 0, 0], [0, 0, 0]], [.1, .1], [.1, .1])
    j = sparse.csr_matrix([[1., 2.], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]])
    return [native, j, np.zeros(2), np.array([.01, 0]),
            NormRows([[.04, .002, 0], [0, .2, 0]], native.caps.copy(), native.scales.copy())]


def test_complete_sample_reconstruction_and_original_prefix_are_preserved():
    a = args(); combined, j, info = augment(*a)
    np.testing.assert_array_equal(j[:6].toarray(), a[1].toarray())
    np.testing.assert_array_equal(combined.vectors[:2], a[0].vectors)
    np.testing.assert_array_equal(combined.caps, np.tile(a[0].caps, 2))
    np.testing.assert_allclose(combined.vectors[2:]+(j[6:]@a[3]).reshape(2, 3), a[4].vectors, atol=1e-15, rtol=0)
    assert info['sample_norm_failures'] == 1 and info['proposal_norm_rows'] == 4
    assert not info['empirical_secant_is_derivative'] and not info['nonlinear_or_storage_enclosure']
    assert not info['acceptance_tolerance_changed'] and not info['release_approved']


def test_orthogonal_directions_have_no_empirical_support_and_keep_original_model():
    a = args(); combined, j, _ = augment(*a)
    step = np.array([0, .01])
    np.testing.assert_array_equal(j[6:]@step, j[:6]@step)
    # A new dependency is present for the originally fixed row, not silently omitted.
    assert j[10, 0] == 20 and j[4].nnz == 0


@pytest.mark.parametrize('observed_slope,expected_cap', [(20., .0005), (.1, .01)])
def test_both_original_and_empirical_caps_remain_hard_in_real_grouped_solve(observed_slope, expected_cap):
    native = NormRows([[0, 0, 0]], [.01], [1.])
    original = sparse.csr_matrix([[1.], [0], [0]])
    model, j, _ = augment(native, original, [0.], [.01], NormRows([[.01*observed_slope, 0, 0]], [.01], [1.]))
    guard = SeparationGuards(np.array([.1]), sparse.csr_matrix((1, 1)), np.array([.001]), [{}],
                             dict(controls=1, complete_pair_partition=True))
    delta, info = direction(model, j, np.full(9, -.02), sparse.csr_matrix(np.ones((9, 1))),
        [{'kind':'triangle-separation'}]*9, np.zeros(1), -np.ones(1), np.ones(1), .02,
        separation_guards=guard, triangle_groups=[list(range(9))])
    assert delta is not None and 0 < delta[0] <= expected_cap
    assert delta[0] > expected_cap*.99
    assert np.all(model.residual(j, delta) <= 0)
    assert info['original_norm_rows'] == 2


@pytest.mark.parametrize('fault', ['zero', 'tiny', 'trust', 'caps', 'scales', 'sample-shape',
    'jacobian-shape', 'jacobian-nan', 'sample-nan', 'anchor-failed', 'negative-cap', 'budget', 'bool-budget'])
def test_invalid_or_unbounded_response_model_is_rejected(fault):
    a = args(); kw = {}
    if fault == 'zero': a[3].fill(0)
    elif fault == 'tiny': a[3] *= 1e-10
    elif fault == 'trust': a[3][0] = .021
    elif fault == 'caps': a[4].caps[0] += 1e-12
    elif fault == 'scales': a[4].scales[0] += 1e-12
    elif fault == 'sample-shape': a[4].vectors = np.zeros((1, 3))
    elif fault == 'jacobian-shape': a[1] = sparse.csr_matrix((6, 1))
    elif fault == 'jacobian-nan': a[1].data[0] = np.nan
    elif fault == 'sample-nan': a[4].vectors[0, 0] = np.nan
    elif fault == 'anchor-failed': a[0].vectors[0, 0] = .11
    elif fault == 'negative-cap': a[0].caps[0] = a[4].caps[0] = -1
    elif fault == 'budget': kw['maximum_elements'] = 23
    else: kw['maximum_elements'] = True
    with pytest.raises(ValueError): augment(*a, **kw)


def test_output_mutation_cannot_modify_original_or_sample():
    a = args(); combined, j, _ = augment(*a)
    combined.caps[0] = 5; combined.vectors[0, 0] = 5; j.data.fill(5)
    assert a[0].caps[0] == .1 and a[0].vectors[0, 0] == .01 and a[4].vectors[0, 0] == .04
    assert a[1][0, 0] == 1
