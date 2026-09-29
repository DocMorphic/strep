import sys
from pathlib import Path
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_half_floor import half_floor_rows, half_floor_values, HalfFloorConstraints
from test_root_release_block import make_problem as toy_problem
from study_coupled_breadth_block import make_problem
from strep import ROOT, read


def toy():
    p = toy_problem()
    p.position_eps = 1e-6
    p.evaluator.sample_clock = 'float32'
    skin = []
    for f in range(len(p.initial)):
        skin.append(p.fitter.rig.vertices(p.evaluator.pose(p.world[f])))
        if f+1 < len(p.initial):
            skin.append(p.fitter.rig.vertices(p.evaluator.half_pose(p.world[f], p.world[f+1], f)))
    p.reference_skin = np.asarray(skin)
    return p


def test_half_rows_cover_both_edges_and_match_independent_directional_difference():
    p = toy()
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    c, j, record = half_floor_rows(p, x, False)
    assert record['edges'] == [2, 3, 4, 5]
    direction = np.random.default_rng(952).normal(size=len(x))
    measured = (half_floor_values(p, x+1e-6*direction, False)-half_floor_values(p, x-1e-6*direction, False))/2e-6
    np.testing.assert_allclose(measured, j@direction, atol=1e-8)
    lowered = x.copy()
    lowered[4] -= .01
    assert half_floor_values(p, lowered).min() < 0.


def test_half_builder_cache_is_point_and_problem_specific():
    p = toy()
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    empty = lambda p, x, q:(np.zeros(0), np.zeros((0, p.width)), [])
    builder = HalfFloorConstraints(base_builder=empty)
    first = builder(p, x)
    assert builder(p, x.copy()) is first and len(builder.builds)==1
    changed = x.copy()
    changed[1] += 1e-5
    assert builder(p, changed) is not first and len(builder.builds)==2
    builder(toy(), x)
    assert len(builder.builds)==3


def test_invalid_derivative_step_fails_closed():
    p = toy()
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    with pytest.raises(ValueError):
        half_floor_rows(p, x, difference_step=0.)


def test_actual_rig_half_derivative_and_saved_floor_violation():
    folder = ROOT/'reports/coupled-clip-sequence-v1/takes/motion-036-rig-02'
    if not (folder/'starting-parameters.npz').exists():
        pytest.skip('Completed sequence fixture required')
    request = read(folder/'request.json')
    request['frames'] = request['windows'][0]['frames']
    values = np.load(folder/'starting-parameters.npz')['parameters']
    with threadpool_limits(limits=1):
        p = make_problem(folder, request, initial_parameters=values)
        x = values[np.ix_(p.frames, p.free)].ravel()
        c, j, _ = half_floor_rows(p, x, False)
        d = np.random.default_rng(953).normal(size=len(x))
        d /= np.linalg.norm(d)
        finite = (half_floor_values(p, x+1e-6*d, False)-half_floor_values(p, x-1e-6*d, False))/2e-6
        assert np.max(np.abs(finite-j@d)) < 2e-4
        last = read(folder/'block-01-solver.json')['history'][-1]['attempts'][-1]
        rejected = x+np.asarray(last['proposed_delta'])*.03125
        assert half_floor_values(p, rejected).min() < -1e-8
