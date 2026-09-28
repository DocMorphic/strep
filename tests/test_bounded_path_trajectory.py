from types import SimpleNamespace
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from bounded_path_trajectory import BoundedPathFitter, ball_pair


def actor():
    return SimpleNamespace(local=np.zeros((150, 1, 4, 4)), dim=12,
                           limits=np.radians([15., 25., 35., 30.]), rig=None)


def test_norm_constraints_allow_axis_budget_and_reject_diagonal_overrun():
    radii=np.array([.3, .7])
    x=np.array([.3, 0., 0., .4, .4, .4])
    slack,jac=ball_pair(x,radii)
    assert slack.min() >= -1e-14
    assert x[0] > radii[0]/np.sqrt(3)
    eps=1e-7
    finite=np.column_stack([(ball_pair(x+np.eye(6)[i]*eps,radii)[0]-ball_pair(x-np.eye(6)[i]*eps,radii)[0])/(2*eps) for i in range(6)])
    np.testing.assert_allclose(jac, finite, atol=1e-8)
    assert ball_pair(np.array([.3,.3,0.,0.,0.,0.]),radii)[0][0] < 0
    with pytest.raises(ValueError):ball_pair(x,[0.,.7])


def test_piecewise_controls_keep_norms_and_expose_excess_speed(monkeypatch):
    # Avoid unrelated skin construction; this test concerns timed controls.
    import paired_hand_trajectory as temporal
    original_actor=temporal.TrajectoryActor
    def without_skin(a,m):
        wrapped=object.__new__(original_actor)
        wrapped.base=a;wrapped.matrix=m;wrapped.dim=m.shape[1]*a.dim
        return wrapped
    monkeypatch.setattr(temporal, 'TrajectoryActor', without_skin)
    fitter=BoundedPathFitter([actor(),actor()])
    rng=np.random.default_rng(42)
    vectors=rng.normal(size=(len(fitter.control_radii),3))
    vectors*=fitter.control_radii[:,None]/np.linalg.norm(vectors,axis=1)[:,None]
    for i,a in enumerate(fitter.base.actors):
        selected=vectors[i*20:(i+1)*20].reshape(5,12)
        expanded=(fitter.matrix@selected).reshape(150,4,3)
        assert np.all(np.linalg.norm(expanded,axis=2)<=a.limits+1e-14)
        assert np.array_equal(expanded[:46],np.zeros_like(expanded[:46]))
        assert np.array_equal(expanded[105:],np.zeros_like(expanded[105:]))
    assert fitter.step_pair(np.zeros(len(fitter.bounds)))[0].min() >= 0
    # Very close knots can violate the separate 5-degree/frame correction cap.
    fast=BoundedPathFitter([actor(),actor()], knots=(74,75,76))
    x=np.zeros(len(fast.bounds));x[12+6]=np.radians(35.)
    assert ball_pair(x,fast.control_radii)[0].min()>=-1e-14
    assert fast.step_pair(x)[0].min()<0
