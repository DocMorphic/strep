import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_witness_cuts import select
from contact_restoration_problem import FrozenContactProblem


def records():
    return [dict(source=0,target=1,points=[[10,[1,2,3],[.2,.3,.5],[1.,0,0]],[11,[3,4,5],[1.,0,0],[0,1.,0]]]),
            dict(source=1,target=0,points=[[12,[0,1,2],[0,1.,0],[0,0,1.]]])]


def test_all_violating_rows_selected_without_changing_identity_or_geometry():
    old=records();selected,info=select(old,[.021,.019,.023],[.018,.018,.019],.02)
    assert info['selected_rows']==2 and info['seed_feasible']
    assert selected[0]['points']==old[0]['points'][:1] and selected[1]['points']==old[1]['points']
    selected[0]['points'][0][2][0]=99
    assert old[0]['points'][0][2][0]==.2


def test_infeasible_cut_remains_reported_not_silently_dropped_or_relaxed():
    chosen,info=select(records(),[.03,.01,.021],[.025,.01,.019],.02)
    assert not info['seed_feasible'] and info['selected_rows']==2
    assert info['infeasible_seed_rows'][0]['vertex']==10
    assert info['infeasible_seed_rows'][0]['frame_cap_m']==.02


def test_passing_frame_uses_exact_threshold_but_failing_frame_keeps_guard_epsilon():
    actual=[.005+5e-10,0,0]
    assert select(records(),actual,[0,0,0],.005,0)[1]['selected_rows']==1
    assert select(records(),actual,[0,0,0],.005,1e-9)[1]['selected_rows']==0


@pytest.mark.parametrize('actual,seed,cap',[(np.zeros(2),np.zeros(3),.02),(np.zeros(3),np.zeros(2),.02),([np.nan,0,0],np.zeros(3),.02),(np.zeros(3),np.zeros(3),-.1)])
def test_invalid_witness_inputs_rejected(actual,seed,cap):
    with pytest.raises(ValueError):select(records(),actual,seed,cap)


def test_augmented_rows_are_before_hard_constraints_and_keep_core_budget():
    class Surface:
        count=2
        def clearance(self,x):return np.array([3.,4.]),np.array([[30.],[40.]])
    problem=FrozenContactProblem.__new__(FrozenContactProblem)
    problem.core=lambda x:(np.array([1.,2.]),np.array([[10.],[20.]]))
    problem.fitter=type('Fitter',(),{'step_pair':staticmethod(lambda x:(np.array([5.]),np.array([[50.]])))})()
    problem.budgets=np.array([.01,.02])
    cuts=[(Surface(),.025)]
    values,jac=problem.inequalities(np.zeros(1),cuts)
    np.testing.assert_array_equal(values,[1,2,3,4,5]);np.testing.assert_array_equal(jac[:,0],[10,20,30,40,50])
    np.testing.assert_allclose(problem.augmented_budgets(cuts),[.01,.02,.026,.026])
