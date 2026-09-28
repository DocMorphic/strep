import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from frame_capped_restoration import frame_caps, row_budgets, RelaxedRows, solve
from elastic_hand_step import solve as shared_solve
from screen_path_guard import select_step


def region():
    return dict(opposing_normal_degrees=0., directions=[dict(source=a,target=1-a,
        within_tolerance_count=3, source_area_witness=dict(area_m2=.001),
        target_area_witness=dict(area_m2=.001)) for a in (0,1)])


def test_shared_allowance_can_regress_a_shallower_frame_but_capped_cannot():
    def objective(x):
        return .5 * 1e6 * (x[0]-.008)**2, np.array([1e6*(x[0]-.008)])
    def inequalities(x):
        return np.array([-.021, -.011-x[0], .01-x[0]]), np.array([[0.],[-1.],[-1.]])
    seed=np.array([0.]); lower=np.array([-.01]); upper=np.array([.01])
    old=shared_solve(objective, inequalities, seed, lower, upper, 2)
    new=solve(objective, inequalities, seed, lower, upper, row_budgets([.02,.01],[1,1],.001,.005))
    assert old.success and new.success
    assert old.x[0] > .007
    assert new.x[0] <= 1e-9
    for result, expected in [(old,False),(new,True)]:
        decision=select_step([.02,.01],[.02,.01+result.x[0]],objective(seed)[0],objective(result.x)[0],region())
        assert decision['accepted'] == expected


def test_passing_frames_also_preserve_existing_peak():
    np.testing.assert_allclose(frame_caps([.001,.002],.005),[.002,.002])
    np.testing.assert_allclose(frame_caps([0.,.004,.02],.005),[.005,.005,.02])
    np.testing.assert_allclose(row_budgets([0.,.004,.02],[0,2,1],.001,.005),[.006,.006,.021])


def test_derivative_and_hard_rows_match_independent_finite_difference():
    def original(x):
        return np.array([x[0]**2-.01,np.sin(x[1])-.02, .03-x@x]), np.array([[2*x[0],0],[0,np.cos(x[1])],-2*x])
    fn=RelaxedRows(original,[.02,.03],2); y=np.array([.1,.2,.7])
    value,jac=fn(y)
    delta=1e-6
    finite=np.column_stack([(fn(y+np.eye(3)[i]*delta)[0]-fn(y-np.eye(3)[i]*delta)[0])/(2*delta) for i in range(3)])
    np.testing.assert_allclose(jac,finite,atol=1e-9)
    assert value[-1] == original(y[:-1])[0][-1]
    assert jac[-1,-1] == 0


def test_hard_constraint_violation_is_never_restored():
    with pytest.raises(ValueError,match='unrelaxed'):
        solve(lambda x:(x@x,2*x),lambda x:(np.array([-.01,-.1]),np.zeros((2,1))),[0],[-1],[1],[.02])


def test_zero_surface_rows_solve_unrelaxed_problem():
    result=solve(lambda x:((x[0]-.2)**2,np.array([2*(x[0]-.2)])),
        lambda x:(np.array([.1-x[0]]),np.array([[-1.]])),[0],[-1],[1],[])
    assert result.success
    assert abs(result.x[0]-.1)<1e-8
    assert result.restoration_slack_m==0


@pytest.mark.parametrize('depths,counts,margin,screen',[
    ([],[],.001,.005),([float('nan')],[1],.001,.005),([-.01],[1],.001,.005),
    ([.01],[1.5],.001,.005),([.01],[True],.001,.005),([.01],[-1],.001,.005),
    ([.01],[1,2],.001,.005),([.01],[1],-.001,.005),([.01],[1],.001,float('inf')),
    ([.12],[1],.001,.005),
])
def test_invalid_budgets_rejected(depths,counts,margin,screen):
    with pytest.raises(ValueError): row_budgets(depths,counts,margin,screen)
