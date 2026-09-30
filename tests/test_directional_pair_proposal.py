import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from directional_pair_proposal import surface_directions, solve


def fixture():
    return dict(gaps=np.array([-.01, -.004]), gap_jacobian=np.array([[1.,0,0],[-1.,0,0]]),
        depth_caps=np.array([.01,.005]), vectors=np.zeros((1,3)), jacobians=np.eye(3)[None],
        radii=np.array([.002]), objective=np.array([1.,0,0]), trust=.01)


def test_directions_are_a_deterministic_signed_orthonormal_frame():
    pairs = surface_directions([.2,.3,.4]); basis = np.array([p[1] for p in pairs[::2]])
    np.testing.assert_allclose(basis@basis.T, np.eye(3), atol=1e-15)
    for (_, positive), (_, negative) in zip(pairs[::2], pairs[1::2]):
        np.testing.assert_array_equal(positive, -negative)
    np.testing.assert_allclose(surface_directions([0,1,0])[0][1], [0,1,0])


@pytest.mark.parametrize('value', [[0,0,0], [np.nan,0,1], [1,2], [np.inf,0,0]])
def test_invalid_normal(value):
    with pytest.raises(ValueError): surface_directions(value)


@pytest.mark.parametrize('field,value', [('trust',0), ('objective',[np.nan,0,0]),
    ('norm_tolerances',[-1]), ('radii',[-1]), ('gap_jacobian',np.ones((2,4)))])
def test_invalid_conic_inputs(field,value):
    args=fixture(); args[field]=value
    with pytest.raises(ValueError): solve(**args)


def fake_solver(monkeypatch, step, status='Solved'):
    import conic_root_descent
    class Backend:
        @staticmethod
        def DefaultSettings(): return SimpleNamespace()
        NonnegativeConeT = ZeroConeT = SecondOrderConeT = staticmethod(lambda n:n)
        @staticmethod
        def DefaultSolver(*args):
            return SimpleNamespace(solve=lambda:SimpleNamespace(x=np.array(step)/.01,
                status=status, iterations=1, solve_time=0.))
    monkeypatch.setattr(conic_root_descent, 'solver_module', lambda:Backend)


@pytest.mark.parametrize('step,status,passed', [([.0005,0,0],'Solved',True),
    ([.0011,0,0],'Solved',False), ([0,.003,0],'Solved',False),
    ([0,0,.011],'Solved',False), ([0,0,0],'MaxIterations',False)])
def test_solver_status_does_not_override_physical_checks(monkeypatch,step,status,passed):
    fake_solver(monkeypatch, step, status)
    result, report=solve(**fixture())
    assert (result is not None) == passed
    assert report['proposal_hard_checks'] == passed
    assert report['quality_approved'] is False


def test_pinned_solver_respects_local_surface_cap_and_tangential_norm():
    from strep import ROOT
    if not (ROOT/'reports/conic-solver-bootstrap-v1.json').exists():
        pytest.skip('Optional locally pinned solver integration')
    args=fixture(); step,report=solve(**args)
    assert report['proposal_hard_checks']
    assert step[0] == pytest.approx(.001, abs=1e-8)
    args['objective']=np.array([0,1.,0]); step,report=solve(**args)
    assert report['proposal_hard_checks']
    assert step[1] == pytest.approx(.002, abs=1e-8)
    args['radii']=np.array([0.]); step,report=solve(**args)
    assert report['proposal_hard_checks']
    np.testing.assert_allclose(step,0,atol=1e-10)
