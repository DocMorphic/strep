import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from grasp_physical_step import epigraph_step, norm_remainder


def test_epigraph_balances_competing_surfaces_and_keeps_unused_coordinates_fixed():
    # Worst violation min max(1-x, x) occurs at x=.5. y has no effect.
    d, r = epigraph_step([-1., 0.], [[1., 0.], [-1., 0.]], [1.], [[0., 0.]], [0.],
                         [1., 1.], [-1., -1.], [1., 1.])
    assert r['success'] and r['tie_break_success']
    np.testing.assert_allclose(d, [.5, 0.], atol=2e-8)
    assert abs(r['primary_optimum']-.5) < 1e-10


def test_contact_is_not_relaxed_to_reduce_surface_overlap():
    # Contact protects x<=.1, so unresolved geometry must remain in epigraph.
    d, r = epigraph_step([-1.], [[1.]], [.1], [[-1.]], [0.], [1.], [-1.], [1.])
    assert d[0] <= .1+1e-9 and r['primary_optimum'] >= .9-1e-9


def test_impossible_protected_row_is_reported_without_a_proposal():
    delta, record = epigraph_step([-1.], [[1.]], [-.1], [[0.]], [0.], [1.], [-1.], [1.])
    assert delta is None and not record['success']


def test_rotation_remainder_covers_nonlinear_norm_at_box_corners():
    radius = np.array([.01, .02, .03, .001]); limits = np.array([.5])
    theta = np.array([.2, .1, -.15])
    for signs in np.ndindex(2, 2, 2):
        delta = radius[:3]*(2*np.array(signs)-1)
        before = 1-theta@theta/limits[0]**2
        linear = before-2*theta@delta/limits[0]**2
        exact = 1-(theta+delta)@(theta+delta)/limits[0]**2
        np.testing.assert_allclose(linear-exact, norm_remainder(radius, limits)[0], atol=1e-15)
