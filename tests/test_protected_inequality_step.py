import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from protected_inequality_step import fit,retain,score


def test_feasible_rows_and_every_original_failed_row_are_protected():
    assert retain([.01,-.1,-.2],[0.,-.09,-.19])
    assert not retain([.01,-.1,-.2],[-1e-12,0.,0.])
    assert not retain([.01,-.1,-.2],[.01,-.11,-.1])
    assert not retain([.01,-.1,-.2],[.01,-.1,-.2])
    assert retain([-1e-15],[0.])


def test_bounded_linear_restoration_has_complete_independent_replay():
    calls=[]
    def measure(x):calls.append(x.copy());return np.array([x[0]-.2,.4-x[0]])
    def linearize(x):return measure(x),np.array([[1.],[-1.]])
    value,result=fit(measure,linearize,[0.],[-1.],[1.],trust=.1,iterations=10)
    assert .2<=value[0]<=.4 and result['inequalities_satisfied']
    assert result['source_rows_preserved'] and result['stop']=='inequalities_satisfied'
    assert len(calls)>1 and not result['quality_approved'] and not result['release_approved']


def test_nonlinear_replay_rejects_false_linear_solver_pass_and_retains_seed():
    def measure(x):return np.array([-1-x[0]**2])
    # A deliberately wrong derivative proposes improvement; actual replay must
    # reject every nonzero proposal despite successful linear subproblem status.
    def linearize(x):return measure(x),np.ones((1,1))
    value,result=fit(measure,linearize,[0.],[-1.],[1.],trust=.1)
    np.testing.assert_array_equal(value,[0])
    assert result['stop']=='no_guarded_improvement' and result['source_rows_preserved']
    assert len(result['trials'])==8 and not any(t['accepted'] for t in result['trials'])


def test_measurement_budget_returns_only_last_accepted_point():
    def measure(x):return np.array([x[0]-.5])
    value,result=fit(measure,lambda x:(measure(x),np.ones((1,1))),[0.],[-1.],[1.],trust=.1,maximum_calls=2)
    assert value[0]==pytest.approx(.1)
    assert result['stop']=='time_or_measurement_budget' and result['measurement_calls']==2
    assert result['final_score'][0]==pytest.approx(.4)


@pytest.mark.parametrize('bad',[np.array([np.nan]),np.array([]),np.ones((2,2))])
def test_score_rejects_incomplete_or_nonfinite_populations(bad):
    with pytest.raises(ValueError):score(bad)


@pytest.mark.parametrize('kwargs',[dict(trust=0),dict(iterations=True),dict(maximum_calls=0),dict(seconds=float('inf'))])
def test_invalid_step_budgets_do_not_run_measurement(kwargs):
    def forbidden(x):raise AssertionError('Invalid budgets must not call measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.],[-1.],[1.],**kwargs)


def test_changed_derivative_population_is_rejected():
    with pytest.raises(ValueError):
        fit(lambda x:np.array([-1.,.1]),lambda x:(np.array([-1.]),np.ones((1,1))),[0.],[-1.],[1.])


def test_merit_tradeoffs_preserve_passes_and_explicit_hard_budget_rows():
    before=[.01,-.1,-.2];after=[.01,-.11,-.1]
    assert retain(before,after,failure_policy='merit',tradeoff_mask=[False,True,True])
    assert not retain(before,after,failure_policy='merit',tradeoff_mask=[False,False,True])
    assert not retain(before,[-1e-12,-.08,-.1],failure_policy='merit')
    assert not retain([-.2,-.1],[-.21,0],failure_policy='merit')


def test_merit_restoration_can_escape_rowwise_stall_without_losing_budget_pass():
    def measure(x):return np.array([x[0]-.2,-.1-.05*x[0],.1-x[0]])
    def linearize(x):return measure(x),np.array([[1.],[-.05],[-1.]])
    rowwise,row_report=fit(measure,linearize,[0.],[-1.],[1.],trust=.1)
    np.testing.assert_array_equal(rowwise,[0.]);assert row_report['stop']=='no_guarded_improvement'
    value,report=fit(measure,linearize,[0.],[-1.],[1.],trust=.1,failure_policy='merit',tradeoff_mask=[True,True,False])
    assert 0<value[0]<=.1
    assert report['source_passing_rows_preserved'] and report['nontradeoff_rows_preserved']
    assert not report['source_rows_preserved'] and not report['inequalities_satisfied']
    assert report['final_score'][0]<report['initial_score'][0] and report['final_score'][1]<report['initial_score'][1]


@pytest.mark.parametrize('mask',[[1,0],[True],[[True,False]]])
def test_tradeoff_mask_must_declare_each_original_row(mask):
    with pytest.raises(ValueError):retain([-.2,-.1],[-.1,-.1],failure_policy='merit',tradeoff_mask=mask)
