"""Irregular-clock optimization and rigid IK bounds; no naturalness claims."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_leg_smoothing import corridor, smooth, lifts, rate_score
from native_leg_floor import lift_pose
from test_native_leg_floor import fixture


def test_irregular_clock_unconstrained_solution_matches_dense_quadratic():
    t = np.array([0., .03, .2, .42, .9, 1.])
    lo = np.array([.2, .21, .25, .4, .22, .2]); hi = np.ones(6)*2
    tau, mu = .15, .5
    x, report = smooth(t, lo, hi, acceleration_time=tau, reference_weight=mu)
    dt = np.diff(t); middle = (dt[:-1]+dt[1:])/2
    d = np.diff(np.eye(6), axis=0)/dt[:, None]
    dd = np.diff(d, axis=0)/middle[:, None]
    weights = np.r_[dt[0]/2, middle, dt[-1]/2]
    h = d.T@np.diag(dt)@d+tau*tau*dd.T@np.diag(middle)@dd+mu*np.diag(weights)
    # Some lower boxes bind; free-column stationarity and active signs prove the
    # convex optimum independently of the optimizer's success flag.
    g = h@x-mu*weights*lo
    active = x == lo
    assert np.any(active) and np.any(~active)
    np.testing.assert_allclose(g[~active], 0, atol=2e-6, rtol=0)
    assert np.all(g[active] >= -2e-6)
    assert report['projected_gradient_residual'] < 1e-7
    # An index-only solver would return the same answer after changing the clock.
    regular, _ = smooth(np.linspace(0, 1, 6), lo, hi, acceleration_time=tau, reference_weight=mu)
    assert np.max(np.abs(x-regular)) > 1e-3


def test_fixed_boxes_are_supported_and_endpoints_can_move():
    t = [0, .1, .3, .6]; lo = np.array([.2, .5, .2, .2])
    fixed, report = smooth(t, lo, lo)
    np.testing.assert_array_equal(fixed, lo); assert report['iterations'] == 0
    x, _ = smooth(t, lo, np.ones(4))
    assert x[0] > lo[0] and x[-1] > lo[-1]


def test_height_corridor_and_smoothed_ik_preserve_foot_and_other_branch():
    world, parents = fixture(); worlds = np.repeat(world[None], 9, axis=0)
    heights = -.01+.003*np.sin(np.arange(9))
    box = corridor(worlds, parents, [1, 2, 3], heights)
    np.testing.assert_allclose(lifts(box, box['lower']), box['lower_lift'], atol=1e-12, rtol=0)
    np.testing.assert_allclose(lifts(box, box['upper']), box['upper_lift'], atol=1e-12, rtol=0)
    bends, report = smooth(np.linspace(0, .8, 9), box['lower'], box['upper'])
    amounts = lifts(box, bends)
    assert report['success'] and np.any(amounts > box['lower_lift']+1e-5)
    for source, height, amount in zip(worlds, heights, amounts):
        changed, _, _ = lift_pose(source, parents, [1, 2, 3], height, clearance=float(height+amount))
        np.testing.assert_allclose(changed[[0, 5]], source[[0, 5]], atol=1e-12, rtol=0)
        np.testing.assert_allclose(changed[3, :3, :3], source[3, :3, :3], atol=1e-12, rtol=0)
        np.testing.assert_allclose(changed[3, :3, 3]-source[3, :3, 3], [0, amount, 0], atol=1e-12, rtol=0)
        assert .00025-1e-12 <= height+amount <= .00475+1e-12


@pytest.mark.parametrize('mutation', ['clearance', 'maximum_height', 'maximum_lift', 'up', 'high_foot', 'deep_foot', 'scale', 'length', 'chain', 'above_hip'])
def test_corridor_rejects_invalid_or_infeasible_conditions(mutation):
    world, parents = fixture(); worlds = np.repeat(world[None], 4, axis=0)
    heights = np.full(4, -.01); kwargs = {}; chain = [1, 2, 3]
    if mutation == 'clearance': kwargs['clearance'] = np.nan
    if mutation == 'maximum_height': kwargs['maximum_height'] = .0001
    if mutation == 'maximum_lift': kwargs['maximum_lift'] = 0
    if mutation == 'up': kwargs['up'] = [0, 2, 0]
    if mutation == 'high_foot': heights[0] = .006
    if mutation == 'deep_foot': heights[0] = -.04
    if mutation == 'scale': worlds[0, 0, 0, 0] = 2
    if mutation == 'length': worlds[0, 3, :3, 3] = worlds[0, 2, :3, 3]
    if mutation == 'chain': chain = [1, 3, 2]
    if mutation == 'above_hip': worlds[:, 3, 1, 3] += 2
    with pytest.raises(ValueError): corridor(worlds, parents, chain, heights, **kwargs)


@pytest.mark.parametrize('times,lo,hi,kwargs', [
    ([0, .1, .1], [.1]*3, [.2]*3, {}),
    ([0, .1, .2], [.3]*3, [.2]*3, {}),
    ([0, .1, .2], [-.1]*3, [.2]*3, {}),
    ([0, .1, .2], [.1]*3, [4.]*3, {}),
    ([0, .1, .2], [.1]*3, [.2]*3, {'reference_weight': 0}),
    ([0, .1, .2], [.1]*3, [.2]*3, {'acceleration_time': -1}),
    ([0, np.nan, .2], [.1]*3, [.2]*3, {}),
])
def test_invalid_optimizer_inputs_rejected(times, lo, hi, kwargs):
    with pytest.raises(ValueError): smooth(times, lo, hi, **kwargs)


def test_lift_conversion_rejects_outside_box():
    world, parents = fixture(); worlds = np.repeat(world[None], 4, axis=0)
    box = corridor(worlds, parents, [1, 2, 3], [-.01]*4)
    with pytest.raises(ValueError): lifts(box, box['upper']+.001)


def test_exact_key_lengths_used_instead_of_freezing_animated_translation():
    world, parents = fixture(); worlds = np.repeat(world[None], 4, axis=0)
    worlds[1, 3, 1, 3] += .0000003
    box = corridor(worlds, parents, [1, 2, 3], [-.01]*4)
    assert box['lengths'][1, 1] != box['lengths'][0, 1]
    np.testing.assert_allclose(lifts(box, box['lower']), box['lower_lift'], atol=1e-12, rtol=0)


def test_rate_ranking_uses_leg_columns_without_modifying_acceptance_caps():
    caps = [np.full((3, 4), .1) for _ in range(4)]
    actual = [v.copy() for v in caps]; before = [v.copy() for v in caps]
    actual[0][:, 0] = 50  # Immutable upper body is outside the ranking columns.
    assert rate_score(actual, caps, [1, 2])['score'] == 0
    actual[1][0, 1] += .2
    report = rate_score(actual, caps, [1, 2], tolerance=0)
    assert report['score'] == pytest.approx((.2/.5)**2/6)
    for a, b in zip(caps, before): np.testing.assert_array_equal(a, b)
    with pytest.raises(ValueError): rate_score(actual, caps, [1, 1])
    with pytest.raises(ValueError): rate_score(actual, caps, [4])
