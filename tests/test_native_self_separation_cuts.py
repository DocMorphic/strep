"""Self bounds retain the original epoch and every triangle vertex pair."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_self_separation_cuts as cuts


def mesh():
    return np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0],
                     [0, 0, .2], [1, 0, .2], [0, 1, .2]]), np.array([[0, 1, 2], [3, 4, 5]])


def test_all_nine_rows_and_both_triangle_derivatives_are_retained():
    v, f = mesh(); model = cuts.SelfSeparationCuts(v, f, [[0, 1]])
    assert len(set(zip(model.left, model.right))) == model.report['rows'] == 9
    np.testing.assert_allclose(model.evaluate(v)[0], .1999, atol=1e-16)
    rng = np.random.default_rng(27); jac = rng.normal(size=(6, 3, 7))
    value, derivative = model.evaluate(v, jac)
    for col in range(7):
        h = 1e-6
        observed = (model.evaluate(v+h*jac[:, :, col])[0]-model.evaluate(v-h*jac[:, :, col])[0])/(2*h)
        np.testing.assert_allclose(derivative[:, col], observed, atol=3e-10, rtol=0)
    assert derivative.shape == (9, 7) and np.isfinite(value).all()


def test_common_translation_cancels_and_rigid_reference_transform_preserves_bounds():
    v, f = mesh(); original = cuts.SelfSeparationCuts(v, f, [[0, 1]])
    jac = np.repeat(np.eye(3)[None], 6, axis=0)
    np.testing.assert_array_equal(original.evaluate(v, jac)[1], np.zeros((9, 3)))
    r = Rotation.from_rotvec([.2, -.3, .4]).as_matrix(); moved = v@r.T+[2., -1., .4]
    transformed = cuts.SelfSeparationCuts(moved, f, [[1, 0]])
    np.testing.assert_allclose(original.evaluate(v)[0], transformed.evaluate(moved)[0], atol=8e-16)
    assert transformed.report['pairs'] == [[0, 1]]


def test_original_overlap_remains_unresolved_and_is_not_assigned_positive_clearance():
    v = np.array([[-1., -1, 0], [1, -1, 0], [0, 1, 0], [0, -.5, -1], [0, -.5, 1], [0, .5, 0]])
    f = np.array([[0, 1, 2], [3, 4, 5]])
    model = cuts.SelfSeparationCuts(v, f, [[0, 1]])
    assert model.report['unresolved_source_axis_pairs'] == 1
    assert model.report['source_axis_gaps_m'][0] < 0
    assert model.evaluate(v)[0].min() >= -1e-15
    assert np.all(model.lower_m < 0)
    assert not model.report['self_collision_free_certified']


def test_shared_vertex_rows_are_kept_and_detect_a_new_crossing():
    v = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, -1, 1]])
    f = np.array([[0, 1, 2], [0, 3, 4]])
    model = cuts.SelfSeparationCuts(v, f, [[0, 1]])
    assert (0, 0) in set(zip(model.left, model.right))
    assert model.lower_m.max() == 0
    crossed = v.copy(); crossed[3] = [.2, .2, -.3]; crossed[4] = [.2, .2, .3]
    assert model.evaluate(crossed)[0].min() < 0
    assert not model.report['quality_approved']


def test_input_mutations_do_not_change_source_bounds():
    v, f = mesh(); pairs = [[0, 1]]; model = cuts.SelfSeparationCuts(v, f, pairs)
    original = model.lower_m.copy(); v[:] = 3; f[:] = 0; pairs[0][:] = [1, 1]
    np.testing.assert_array_equal(model.lower_m, original)
    assert model.report['pairs'] == [[0, 1]]


@pytest.mark.parametrize('fault', ['empty', 'duplicate', 'reverse', 'same', 'bool-id', 'bad-id',
    'float-id', 'extra-id', 'nan', 'bool-vertices', 'float-faces', 'bad-face', 'degenerate',
    'negative-clearance', 'bool-clearance', 'large-clearance', 'budget'])
def test_invalid_or_incomplete_construction_rejects(fault):
    v, f = mesh(); pairs = [[0, 1]]; kwargs = {}
    if fault == 'empty': pairs = []
    elif fault == 'duplicate': pairs *= 2
    elif fault == 'reverse': pairs.append([1, 0])
    elif fault == 'same': pairs = [[0, 0]]
    elif fault == 'bool-id': pairs[0][0] = False
    elif fault == 'bad-id': pairs[0][0] = 2
    elif fault == 'float-id': pairs[0][0] = 0.
    elif fault == 'extra-id': pairs[0].append(0)
    elif fault == 'nan': v[0, 0] = np.nan
    elif fault == 'bool-vertices': v = v.astype(bool)
    elif fault == 'float-faces': f = f.astype(float)
    elif fault == 'bad-face': f[0, 0] = 6
    elif fault == 'degenerate': v[1] = v[0]
    elif fault == 'negative-clearance': kwargs['clearance_m'] = -.001
    elif fault == 'bool-clearance': kwargs['clearance_m'] = True
    elif fault == 'large-clearance': kwargs['clearance_m'] = .006
    else: kwargs['maximum_rows'] = 8
    with pytest.raises(ValueError): cuts.SelfSeparationCuts(v, f, pairs, **kwargs)


@pytest.mark.parametrize('fault', ['partial-vertices', 'partial-jac', 'nan-jac', 'bool-jac', 'columns', 'workspace'])
def test_invalid_or_over_budget_evaluation_rejects(monkeypatch, fault):
    v, f = mesh(); model = cuts.SelfSeparationCuts(v, f, [[0, 1]]); jac = np.zeros((6, 3, 4))
    if fault == 'partial-vertices': v = v[:-1]
    elif fault == 'partial-jac': jac = jac[:-1]
    elif fault == 'nan-jac': jac[0, 0, 0] = np.nan
    elif fault == 'bool-jac': jac = jac.astype(bool)
    elif fault == 'columns': jac = np.zeros((6, 3, 193))
    else: monkeypatch.setattr(cuts, 'MAX_WORKSPACE_BYTES', 1)
    with pytest.raises(ValueError): model.evaluate(v, jac)
