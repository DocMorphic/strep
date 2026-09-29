import sys
from pathlib import Path
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read
from study_coupled_breadth_block import make_problem
from coupled_breadth_conic import constraints
from conic_root_descent import direction
import json


@pytest.fixture(scope='module')
def problem():
    folder = ROOT/'reports/coupled-breadth-block-v1'
    if not (folder/'request.json').exists():
        pytest.skip('Provisioned frozen coupled fixture required')
    with threadpool_limits(limits=1):
        return make_problem(folder, read(folder/'request.json'))


def test_conic_adapter_retains_strict_floor_and_added_norms(problem):
    p = problem
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    with threadpool_limits(limits=1):
        c, j, cones = constraints(p, x)
        actual = p.evaluate(x)
        assert np.allclose(c, actual[2][:len(c)], atol=1e-12)
        assert np.allclose(j, actual[3][:len(c)], atol=1e-12)
        assert all(np.linalg.norm(item['vector']) <= item['cap']+1e-10 for item in cones)
        assert sum(item['kind']=='root_radius' for item in cones) == len(p.frames)
        assert any(item['kind']=='anchor' for item in cones)
        lowered = x.copy()
        lowered[1] -= .002
        floor, _, _ = constraints(p, lowered)
        assert floor[:len(p.reference_skin[0])].min() < -.1


def test_added_affine_cones_match_smooth_geometry_directions(problem):
    p = problem
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    direction = np.random.default_rng(142).normal(size=len(x))
    direction /= np.linalg.norm(direction)
    with threadpool_limits(limits=1):
        _, _, center = constraints(p, x, False)
        _, _, plus = constraints(p, x+1e-6*direction, False)
        _, _, minus = constraints(p, x-1e-6*direction, False)
    for item, a, b in zip(center, plus, minus):
        if item['kind'] in ('anchor', 'root_radius'):
            numerical = (a['vector']-b['vector'])/2e-6
            np.testing.assert_allclose(numerical, item['jacobian']@direction, atol=2e-7, rtol=2e-5)


def test_actual_proposal_metadata_can_be_saved_without_numpy_scalars(problem):
    p = problem
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    with threadpool_limits(limits=1):
        delta, proof = direction(p, x, 1e-4, constraint_builder=constraints)
    assert delta is not None and proof['predicted_objective_change'] < 0
    assert json.loads(json.dumps(proof, allow_nan=False))['tightened_cones'] == 0


@pytest.mark.parametrize('case', ['motion-026-rig-02', 'motion-061-rig-02'])
def test_physical_guard_rejects_saved_normalized_tolerance_leaks(case):
    folder = ROOT/'reports/coupled-breadth-population-v1/takes'/case
    if not (folder/'parameters.npz').exists():
        pytest.skip('Completed failed population fixture required')
    with threadpool_limits(limits=1):
        p = make_problem(folder, read(folder/'request.json'))
        assert p.geometric_guard(p.initial)
        values = np.load(folder/'parameters.npz')['parameters']
        x = values[np.ix_(p.frames, p.free)].ravel()
        # These passed the old normalized residual screen but failed the
        # independent physical anchor allowance. They must fail step selection.
        assert p.evaluate(x)[2].min() >= -1e-8
        assert not p.geometric_guard(values)
