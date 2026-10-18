from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sequential_scene_step import SceneStepGuard
from conic_pose_minimax import minimax_step


def test_conic_protects_passing_contact_even_with_worse_global_peak():
    margin=np.array([-1.,.1]);jac=np.array([[1.,0,0],[-1.,0,0]])
    step,r=minimax_step(margin,jac,np.zeros(3),trust=1.,protected_rows=np.array([False,True]))
    assert step is not None and np.all((margin+jac@step)[[1]]>=0)
    assert r['predicted_maximum_model_violation']==pytest.approx(.9,abs=1e-6) and r['protected_row_indices']==[1]


def test_conic_hard_rows_have_no_peak_slack_and_keep_all_rows():
    margin=np.array([-.5,.2]);jac=np.array([[1.,0,0],[-2.,0,0]])
    step,r=minimax_step(margin,jac,np.zeros(3),trust=1.,protected_rows=np.array([False,True]))
    assert step is not None and r['model_rows']==2 and r['omitted_rows']==0 and margin[1]+jac[1]@step>=0


@pytest.mark.parametrize('value',[[1,0],[True],np.array([1.,0.])])
def test_conic_incomplete_or_nonboolean_protection_rejects(value):
    with pytest.raises(ValueError):minimax_step(np.array([-1.,.2]),np.ones((2,3)),np.zeros(3),protected_rows=value)


def guard():return SceneStepGuard(['floor','contact','partner'],[-1.,.1,-.5],np.zeros(3),[.02,.01,.02])


def test_nonlinear_loss_of_passing_contact_rejects_despite_peak_improvement():
    state=guard();report=state.assess(state.names,[-.2,-1e-15,-.1],np.zeros(3))
    assert not report['accepted'] and report['lost_protected_row_indices']==[1]
    with pytest.raises(ValueError):state.advance(state.names,[-.2,-1e-15,-.1],np.zeros(3))
    np.testing.assert_array_equal(state.margins,[-1.,.1,-.5])


def test_newly_passing_rows_become_protected_and_budgets_stay_original():
    state=guard();state.advance(state.names,[.001,.05,-.3],[.2,0,0]);assert state.protected_rows.tolist()==[True,True,False]
    assert not state.assess(state.names,[-1e-15,.1,-.1],[.3,0,0])['accepted']
    assert not state.assess(state.names,[.1,.1,-.1],[.8,.8,0])['accepted']


def test_search_margin_is_stricter_than_original_zero_boundary():
    state=SceneStepGuard(['a'],[.001],np.zeros(3),[.02]);r=state.assess(state.names,[.01],np.zeros(3))
    assert r['accepted'] and r['all_original_numeric_rows_pass'] and not r['all_search_targets_pass'] and r['added_physical_tolerance']==0


def test_no_average_improvement_or_equal_peak_can_substitute_for_worst_progress():
    state=guard();assert not state.assess(state.names,[-1.,.2,0.],np.zeros(3))['accepted']
    assert not state.assess(state.names,[-1.01,.2,.2],np.zeros(3))['accepted']


def test_complete_row_identity_order_and_hidden_last_row_preserved():
    state=guard()
    with pytest.raises(ValueError):state.assess(['contact','floor','partner'],[-.2,.2,-.1],np.zeros(3))
    with pytest.raises(ValueError):state.assess(['floor','contact'],[-.2,.2],np.zeros(3))
    assert not state.assess(state.names,[-.2,.2,-2.],np.zeros(3))['accepted']


def test_owned_state_and_read_properties_cannot_rebase_reference():
    m=np.array([-1.,.1]);x=np.zeros(3);reserve=np.array([.02,.01]);state=SceneStepGuard(['a','b'],m,x,reserve)
    m[:]=99;x[:]=99;reserve[:]=99;state.margins[:]=99;state.controls[:]=99;state.protected_rows[:]=False
    assert state.margins.tolist()==[-1.,.1] and state.controls.tolist()==[0,0,0] and state.protected_rows.tolist()==[False,True]


@pytest.mark.parametrize('fault',['duplicate','nan','reserve','controls'])
def test_invalid_state_rejects(fault):
    args=[['a','b'],[-1.,.1],np.zeros(3),[.02,.01]]
    if fault=='duplicate':args[0]=['a','a']
    elif fault=='nan':args[1]=[float('nan'),.1]
    elif fault=='reserve':args[3]=[-.01,.01]
    else:args[2]=np.ones(3)
    with pytest.raises(ValueError):SceneStepGuard(*args)
