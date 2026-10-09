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


@pytest.mark.parametrize('kwargs',[dict(trust=0),dict(iterations=True),dict(maximum_calls=0),dict(seconds=float('inf')),dict(proposal='guess')])
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


def test_nonlinear_proposal_follows_curved_target_boundary_that_stalls_tangent_step():
    radius_squared=.1**2
    def measure(x):return np.array([x[1]-.05,radius_squared-x@x])
    def linearize(x):return measure(x),np.array([[0.,1.],[-2*x[0],-2*x[1]]])
    seed=[.1,0.];bounds=([-1.,-1.],[1.,1.])
    tangent,tangent_report=fit(measure,linearize,seed,*bounds,trust=.1)
    np.testing.assert_array_equal(tangent,seed)
    assert tangent_report['stop']=='no_guarded_improvement'
    value,report=fit(measure,linearize,seed,*bounds,trust=.1,proposal='nonlinear')
    assert np.all(measure(value)>=0) and report['inequalities_satisfied']
    assert report['source_passing_rows_preserved'] and report['proposal_queries']
    assert not any(q['retained'] for q in report['proposal_queries'])
    assert not report['quality_approved'] and not report['release_approved']


def test_nonlinear_query_budget_never_selects_an_unretained_inner_candidate():
    records=[]
    def measure(x):return np.array([x[0]-.5])
    value,report=fit(measure,lambda x:(measure(x),np.ones((1,1))),[0.],[-1.],[1.],trust=.1,
        maximum_calls=2,proposal='nonlinear',observer=lambda label,x,slacks,keep:records.append((label,x.copy(),keep)))
    np.testing.assert_array_equal(value,[0.])
    assert report['stop']=='time_or_measurement_budget' and report['measurement_calls']==2
    assert report['proposal_queries'] and not report['trials']
    assert records[-1][0]=='final' and records[-1][1][0]==0.


def test_nonlinear_query_rejects_derivatives_for_a_different_population():
    def measure(x):return np.array([x[0]-.5,.8-x[0]])
    def linearize(x):
        if x[0]==0:return measure(x),np.array([[1.],[-1.]])
        return np.array([x[0]-.5]),np.ones((1,1))
    with pytest.raises(ValueError,match='Every original nonlinear'):
        fit(measure,linearize,[0.],[-1.],[1.],proposal='nonlinear')


def test_outside_solver_callback_is_bounded_and_recorded_without_relaxing_final_limits(monkeypatch):
    import protected_inequality_step as module
    from types import SimpleNamespace
    measured=[]
    def measure(x):
        assert 0<=x[0]<=.1;measured.append(x.copy());return np.array([x[0]-.05])
    def linearize(x):return measure(x),np.ones((1,1))
    def minimize(fun,x0,**kwargs):
        # Reproduce the unwrapped constraint callback passing beyond its bound.
        kwargs['constraints'][0]['fun'](np.array([.10000000000000002]))
        kwargs['constraints'][0]['jac'](np.array([.10000000000000002]))
        fun(np.array([.10000000000000002]))
        return SimpleNamespace(x=np.array([.10000000000000002]),success=True,message='fixture')
    monkeypatch.setattr(module,'minimize',minimize)
    value,report=fit(measure,linearize,[0.],[0.],[.1],trust=.1,proposal='nonlinear')
    assert value[0]==.1 and report['inequalities_satisfied'] and report['bounded_proposal_queries']
    assert all(record['bounded_controls'][0]==.1 for record in report['bounded_proposal_queries'])
    assert all(x[0]<=.1 for x in measured)


def test_explicit_proposal_can_restore_failed_point_with_search_headroom_and_original_retention():
    def measure(x):return np.array([x[1]-.2,.01-x[0]])
    def derivative(x):return measure(x),np.array([[0.,1.],[-1.,0.]])
    value,r=fit(measure,derivative,[.02,0.],[-1.,-1.],[1.,1.],trust=.1,
        failure_policy='merit',tradeoff_mask=[True,False],proposal='nonlinear',
        proposal_feasible_mask=[False,True],proposal_headroom=[0.,1e-5])
    assert np.all(measure(value)>=0) and measure(value)[1]>=1e-5-1e-12
    assert r['inequalities_satisfied'] and r['nontradeoff_rows_preserved']
    assert r['proposal_feasible_mask']==[False,True] and r['proposal_headroom_normalized']==[0.,1e-5]
    assert not r['quality_approved'] and not r['release_approved']


@pytest.mark.parametrize('kwargs',[dict(proposal_feasible_mask=[True]),dict(proposal_feasible_mask=[1,0]),
    dict(proposal_headroom=[0.]),dict(proposal_headroom=[0.,float('nan')]),
    dict(proposal_headroom=[0.,-.1]),dict(proposal_headroom=[0.,.1])])
def test_proposal_targets_require_complete_masks_and_bounded_finite_headroom(kwargs):
    def measure(x):return np.array([x[0]-.2,.3-x[0]])
    with pytest.raises(ValueError,match='Complete Boolean proposal'):
        fit(measure,lambda x:(measure(x),np.array([[1.],[-1.]])),[0.],[-1.],[1.],**kwargs)


def test_tangent_guard_rejects_a_finite_feasible_endpoint_with_bad_initial_budget_direction(monkeypatch):
    import protected_inequality_step as module
    from types import SimpleNamespace
    def measure(x):return np.array([x[0]-1,x[0]*(x[0]-.3)+x[1],.25-x[0],.08-x[1]])
    def derivative(x):return measure(x),np.array([[1.,0.],[2*x[0]-.3,1.],[-1.,0.],[0.,-1.]])
    def forced(fun,x0,**kwargs):return SimpleNamespace(x=np.array([.25,.0126]),success=True,message='fixture')
    monkeypatch.setattr(module,'minimize',forced)
    seed=[0.,0.];kwargs=dict(trust=.3,iterations=1,proposal='nonlinear',failure_policy='merit',tradeoff_mask=[True,False,False,False])
    plain,r0=fit(measure,derivative,seed,[-1.,-1.],[1.,1.],**kwargs)
    assert plain[0]==.25 and r0['trials'][0]['accepted']
    value,r=fit(measure,derivative,seed,[-1.,-1.],[1.,1.],proposal_tangent_guard=True,**kwargs)
    np.testing.assert_array_equal(value,seed)
    full=r['trials'][0]
    assert full['retention_guard_passed'] and not full['tangent_guard_passed'] and not full['accepted']
    assert full['tangent_minimum_slack']==pytest.approx(-.0624)
    assert r['proposal_linearizations'][0]['protected_rows']==[1,2,3]
    assert r['source_passing_rows_preserved'] and not r['quality_approved']


def test_real_tangent_proposal_moves_without_initial_protected_budget_regression():
    def measure(x):return np.array([x[0]-1,x[0]*(x[0]-.3)+x[1],.25-x[0],.08-x[1]])
    def derivative(x):return measure(x),np.array([[1.,0.],[2*x[0]-.3,1.],[-1.,0.],[0.,-1.]])
    value,r=fit(measure,derivative,[0.,0.],[-1.,-1.],[1.,1.],trust=.3,iterations=1,
        proposal='nonlinear',failure_policy='merit',tradeoff_mask=[True,False,False,False],proposal_tangent_guard=True)
    assert value[0]>0 and value[1]-.3*value[0]>=0
    assert r['trials'][-1]['accepted'] and r['trials'][-1]['tangent_guard_passed']
    assert r['source_passing_rows_preserved'] and r['nontradeoff_rows_preserved']
    assert not r['quality_approved'] and not r['release_approved']


@pytest.mark.parametrize('kwargs',[dict(proposal_tangent_guard=1),dict(proposal_tangent_guard=True,proposal='linear')])
def test_invalid_tangent_guard_never_measures(kwargs):
    def forbidden(x):raise AssertionError('Invalid tangent request reached measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.],[-1.],[1.],**kwargs)
