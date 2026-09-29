import itertools
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from conic_linear_screen import screen
from conic_root_descent import direction
from test_root_release_block import make_problem


def test_screen_matches_every_corner_with_asymmetric_coordinate_bounds():
    rng = np.random.default_rng(849)
    j = rng.normal(size=(100, 5))
    c = rng.uniform(-1., 3., len(j))
    lower = rng.uniform(-.3, 0., 5)
    upper = rng.uniform(.05, .7, 5)
    kept, rows, proof = screen(c, j, lower, upper)
    ids = proof['retained_indices']
    omitted = np.setdiff1d(np.arange(len(c)), ids)
    assert len(omitted) and len(ids)
    np.testing.assert_array_equal(kept, c[ids])
    np.testing.assert_array_equal(rows, j[ids])
    for corner in itertools.product(*zip(lower, upper)):
        margins = c+j@np.asarray(corner)
        assert np.all(margins[omitted] > 0.)
        assert np.all(np.isin(np.flatnonzero(margins <= 0.), ids))


def test_boundary_and_roundoff_sensitive_rows_are_retained():
    c = np.array([1., 1.+1e-14, 2., -1.])
    j = np.ones((4, 1))
    _, _, proof = screen(c, j, np.array([-1.]), np.array([1.]))
    assert proof['retained_indices'] == [0, 1, 3]


@pytest.mark.parametrize('c,j,lo,hi', [
    ([1.], [[1., 2.]], [0.], [1.]),
    ([np.nan], [[1.]], [0.], [1.]),
    ([1.], [[np.inf]], [0.], [1.]),
    ([1.], [[1.]], [2.], [1.]),
    ([1.], [[1e308]], [-2.], [2.]),
])
def test_malformed_or_nonfinite_rows_fail_closed(c, j, lo, hi):
    with pytest.raises(ValueError):
        screen(c, j, lo, hi)


def test_screened_proposal_is_checked_against_the_full_linear_system():
    p = make_problem()
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    delta, proof = direction(p, x, .001, linear_screen=True)
    assert delta is not None
    assert proof['linear_screen']['omitted_rows'] > 0
    assert proof['predicted_linear_minimum'] >= -1e-8
    assert proof['predicted_objective_change'] < 0
