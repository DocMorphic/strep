"""Mixed-cone proposals preserve hard native caps and every surface halfspace."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_scene_conic import direction as norm_direction
from native_pair_surface_conic import direction
from native_surface_lift import lift


def test_direct_halfspaces_agree_with_full_lifted_norm_model():
    native = NormRows([[0., 0, 0]], [.015], [1.])
    nj = sparse.csc_matrix([[1.], [0.], [0.]])
    gaps = np.array([-.01, .005, .003]); sj = sparse.csc_matrix([[1.], [-1.], [.2]])
    x, lo, hi = np.zeros(1), -np.ones(1), np.ones(1)
    delta, report = direction(native, nj, gaps, sj, x, lo, hi, .02)
    extra, ej, _ = lift(gaps, sj, x, lo, hi, .02)
    full = NormRows(np.r_[native.vectors, extra.vectors], np.r_[native.caps, extra.caps], np.r_[native.scales, extra.scales])
    lifted, old = norm_direction(full, sparse.vstack([nj, ej]), x, lo, hi, .02, hard_rows=1)
    assert delta is not None and lifted is not None
    assert report['affine_optimum'] == pytest.approx(old['affine_optimum'], abs=1e-7)
    np.testing.assert_allclose(delta, lifted, atol=1e-7, rtol=0)
    assert native.residual(nj, delta).max() <= 1e-8
    assert report['scalar_rows_encoded'] == 3 and report['scalar_rows_omitted'] == 0
    assert not report['quality_approved'] and not report['release_approved']


def test_all_nine_competing_pairs_are_retained_with_twenty_micron_native_bound():
    native = NormRows([[0., 0, 0]], [2e-5], [.0001])
    nj = sparse.csc_matrix([[1.], [0.], [0.]])
    slopes = np.array([1., 1, 1, -1, -1, -1, 0, 0, 0])
    gaps = np.full(9, -.002)
    delta, report = direction(native, nj, gaps, sparse.csc_matrix(slopes[:, None]),
        [0.], [-1.], [1.], .02, clearance=0.)
    assert delta is not None and abs(delta[0]) <= 2e-5+1e-9
    assert report['scalar_rows_encoded'] == 9 and report['affine_optimum'] == pytest.approx(.4, abs=1e-7)
    assert report['predicted_native_excess'] <= 1e-7


def test_fixed_failed_native_row_prevents_surface_solution():
    native = NormRows([[.1, 0, 0]], [.01], [1.])
    delta, report = direction(native, sparse.csc_matrix((3, 1)), [-.01], sparse.csc_matrix([[1.]]), [0.], [-1.], [1.], .02)
    assert delta is None and report['status'] == 'FixedProtectedConflict'


@pytest.mark.parametrize('settings', [dict(trust=True), dict(trust=0), dict(clearance=.006), dict(scale=True),
    dict(maximum_rows=0), dict(maximum_nonzeros=0), dict(maximum_nonzeros=1)])
def test_invalid_resource_and_model_settings_reject(settings):
    native = NormRows([[0., 0, 0]], [1.], [1.])
    with pytest.raises(ValueError):
        direction(native, sparse.csc_matrix([[1.], [0.], [0.]]), [0.], sparse.csc_matrix([[1.]]),
            [0.], [-1.], [1.], **{'trust':.02, **settings})
