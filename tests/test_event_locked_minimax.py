import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from event_locked_minimax import MinimaxStep
from bounded_path_trajectory import ball_pair


def problem(base=None):
    base=np.zeros(6) if base is None else base
    # One witness improves with x0; another worsens. x3 could cheat if unlocked.
    jac=np.zeros((2,6));jac[:,0]=[1,-1];jac[:,3]=[2,2]
    return MinimaxStep(base,np.array([-.03,-.01]),jac,np.array([0,0,0,1,1,1],bool),
                       np.ones(6),lambda x:ball_pair(x,np.ones(2)),.1)


def test_joint_minimax_balances_conflicting_witnesses_and_locks_event():
    p=problem();x,r=p.solve()
    assert r['success'] and r['minimum_constraint_slack']>=-1e-8
    assert x[0]==pytest.approx(.01,abs=1e-7)
    assert r['predicted_peak_depth_m']==pytest.approx(.02,abs=1e-7)
    assert np.array_equal(x[3:],np.zeros(3))


def test_constraint_jacobian_matches_central_difference():
    p=problem();y=np.array([.13,-.2,.11,6.]);values,jac=p.constraints(y)
    for k in range(len(y)):
        d=np.zeros_like(y);d[k]=1e-6
        finite=(p.constraints(y+d)[0]-p.constraints(y-d)[0])/2e-6
        assert np.allclose(finite,jac[:,k],rtol=1e-6,atol=1e-8)


def test_joint_norm_trust_ball_not_individual_coordinate_box():
    jac=np.ones((1,3));p=MinimaxStep(np.zeros(3),[-1],jac,[False]*3,np.ones(3),lambda x:ball_pair(x,[1]),.02)
    x,r=p.solve();assert r['success']
    assert np.linalg.norm(x)==pytest.approx(.02,abs=1e-8)
    assert np.allclose(x,np.full(3,.02/np.sqrt(3)),atol=1e-6)


def test_original_hard_ball_remains_binding():
    p=MinimaxStep(np.array([.99,0,0]),[-.1],[[1,0,0]],[False]*3,np.ones(3),lambda x:ball_pair(x,[1]),.1)
    x,r=p.solve();assert r['success']
    assert x[0]==pytest.approx(1.,abs=1e-8)
    assert np.linalg.norm(x)<=1+1e-8


def test_reject_infeasible_seed_and_empty_witnesses():
    with pytest.raises(ValueError):problem(np.full(6,2.))
    with pytest.raises(ValueError):MinimaxStep(np.zeros(3),[],np.zeros((0,3)),[False]*3,np.ones(3),lambda x:ball_pair(x,[1]),.1)
