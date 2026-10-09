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


def test_feasible_start_initializes_inner_solver_but_does_not_retain_its_queries(monkeypatch):
    import protected_inequality_step as module
    from types import SimpleNamespace
    starts=[];observations=[]
    def measure(x):return np.array([x[0]-.2,.4-x[0]])
    def derivative(x):return measure(x),np.array([[1.],[-1.]])
    def solver(fun,x0,**kwargs):
        starts.append(x0.copy());fun(x0)
        return SimpleNamespace(x=x0.copy(),success=True,message='fixture')
    monkeypatch.setattr(module,'minimize',solver)
    value,r=fit(measure,derivative,[0.],[-1.],[1.],trust=.3,proposal='nonlinear',proposal_start='linear-feasible',
        proposal_feasible_mask=[True,False],proposal_headroom=[1e-5,0.],proposal_tangent_guard=True,
        observer=lambda label,x,slack,retained:observations.append((label,retained)))
    assert starts[0][0]==pytest.approx(.20001) and value[0]==pytest.approx(.20001)
    assert r['inequalities_satisfied'] and r['proposal_starts'][0]['success'] and not r['proposal_starts'][0]['retained']
    assert r['proposal_queries'] and all(not q['retained'] for q in r['proposal_queries'])
    assert r['trials'][0]['accepted'] and all(not kept for label,kept in observations if 'query' in label)
    assert not r['quality_approved'] and not r['release_approved']


def test_linear_start_with_nonlinear_budget_failure_is_not_promoted(monkeypatch):
    import protected_inequality_step as module
    from types import SimpleNamespace
    def measure(x):return np.array([x[0]-.2,.01-x[0]**2])
    def derivative(x):return measure(x),np.array([[1.],[-2*x[0]]])
    def solver(fun,x0,**kwargs):return SimpleNamespace(x=x0.copy(),success=True,message='fixture')
    monkeypatch.setattr(module,'minimize',solver)
    value,r=fit(measure,derivative,[0.],[-1.],[1.],trust=.3,iterations=1,
        proposal='nonlinear',proposal_start='linear-feasible',proposal_feasible_mask=[True,False],proposal_tangent_guard=True)
    assert not r['trials'][0]['retention_guard_passed'] and not r['trials'][0]['accepted']
    assert 0<value[0]<.2 and measure(value)[1]>=0
    assert r['source_passing_rows_preserved'] and not r['inequalities_satisfied']


def test_unavailable_linear_start_never_enters_solver_or_changes_seed(monkeypatch):
    import protected_inequality_step as module
    def forbidden(*args,**kwargs):raise AssertionError('Infeasible first-order start entered inner solve')
    monkeypatch.setattr(module,'minimize',forbidden)
    def measure(x):return np.array([x[0]-.2,.1-x[0]])
    value,r=fit(measure,lambda x:(measure(x),np.array([[1.],[-1.]])),[0.],[-1.],[1.],trust=.3,
        proposal='nonlinear',proposal_start='linear-feasible',proposal_feasible_mask=[True,False])
    np.testing.assert_array_equal(value,[0.]);assert r['stop']=='linear_start_unavailable'
    assert r['proposal_starts'][0]['status']==2 and not r['proposal_starts'][0]['success']
    assert r['measurement_calls']==1 and not r['trials'] and not r['proposal_queries']
    assert not r['quality_approved']


def test_warm_start_query_budget_preserves_last_retained_point():
    def measure(x):return np.array([x[0]-.2])
    value,r=fit(measure,lambda x:(measure(x),np.ones((1,1))),[0.],[-1.],[1.],trust=.3,maximum_calls=2,
        proposal='nonlinear',proposal_start='linear-feasible',proposal_feasible_mask=[True])
    np.testing.assert_array_equal(value,[0.]);assert r['stop']=='time_or_measurement_budget'
    assert r['proposal_starts'][0]['success'] and r['proposal_queries'] and not r['trials']


@pytest.mark.parametrize('kwargs',[dict(proposal_start='guess'),dict(proposal_start=True),dict(proposal_start='linear-feasible')])
def test_invalid_proposal_initialization_never_measures(kwargs):
    def forbidden(x):raise AssertionError('Invalid starting policy reached measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.],[-1.],[1.],**kwargs)


@pytest.mark.parametrize('solution',[[float('nan'),0.],[.3,.3],[.2,0.],[.1,.1]])
def test_claimed_linear_success_must_replay_bounds_and_complete_rows(monkeypatch,solution):
    import protected_inequality_step as module
    from types import SimpleNamespace
    monkeypatch.setattr(module,'linprog',lambda *args,**kwargs:SimpleNamespace(status=0,success=True,message='fixture',x=np.array(solution)))
    def measure(x):return np.array([x[0]-.2,.4-x[0]])
    with pytest.raises(ValueError):fit(measure,lambda x:(measure(x),np.array([[1.],[-1.]])),[0.],[-1.],[1.],trust=.25,
        proposal='nonlinear',proposal_start='linear-feasible',proposal_feasible_mask=[True,False])


def circle_vectors(x):
    return dict(offsets=np.array([[x[0],x[1],0.]]),jacobian=np.array([[[1.,0.],[0.,1.],[0.,0.]]]),
        limits=np.array([.1]),scales=np.array([.1]),rows=np.array([1]),distance=np.array([True]))


def test_geometry_descent_preserves_transverse_distance_and_decreases_merit():
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    value,r=fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],trust=.1,iterations=1,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_tangent_guard=True)
    start=r['proposal_starts'][0]
    assert start['success'] and start['directional_merit']<0 and start['minimum_vector_slack']>=-1e-8
    assert value[1]>.05 and np.all(measure(value)>=0) and r['trials'][-1]['accepted']
    assert r['trials'][-1]['stage']=='geometry-start' and not r['proposal_queries']
    assert not start['retained'] and not r['quality_approved']
    delta=np.asarray(start['delta']);assert np.linalg.norm(np.array([.1,0.])+delta)<=.1+1e-9


def test_worst_first_is_not_dominated_by_many_small_failures():
    def measure(x):return np.r_[x[0]-.8,np.repeat(x[1]-.2,100),1-(x@x)/.1**2]
    def derivative(x):return measure(x),np.vstack([[1.,0.],np.tile([0.,1.],(100,1)),-2*x/.1**2])
    def vectors(x):return dict(offsets=np.array([[x[0],x[1],0.]]),jacobian=np.array([[[1.,0.],[0.,1.],[0.,0.]]]),
        limits=np.array([.1]),scales=np.array([1.]),rows=np.array([101]),distance=np.array([False]))
    options=dict(iterations=1,trust=.1,proposal='nonlinear',proposal_start='geometry-descent',vectorize=vectors,proposal_tangent_guard=True)
    old,a=fit(measure,derivative,[0.,0.],[-1.,-1.],[1.,1.],**options)
    focused,b=fit(measure,derivative,[0.,0.],[-1.,-1.],[1.,1.],proposal_priority='worst-first',**options)
    assert old[0]<.01 and focused[0]>.09 and focused[0]>10*old[0]
    assert b['final_score'][0]<a['final_score'][0] and b['final_score'][1]<b['initial_score'][1]
    assert b['trials'][-1]['accepted'] and b['trials'][-1]['stage']=='geometry-start'
    start=b['proposal_starts'][0];delta=np.array(start['delta']);primary=np.array(start['primary_proposals'][-1]['controls_delta'])
    assert start['priority']=='worst-first' and start['directional_merit']<0 and not start['retained']
    assert start['predicted_worst']<=start['primary_epigraph']+start['epigraph_tie_tolerance']+1e-8
    assert np.max(-measure(np.zeros(2))-derivative(np.zeros(2))[1]@primary)<=start['primary_epigraph']+1e-8
    assert np.linalg.norm(delta)<=.1 and b['source_passing_rows_preserved'] and not b['quality_approved']


def test_false_priority_epigraph_never_reaches_nonlinear_retention(monkeypatch):
    import protected_inequality_step as module
    real=module.linprog;calls=[]
    def lie(*args,**kwargs):
        result=real(*args,**kwargs);calls.append(result)
        if len(calls)==2:result.x[-1]=-1.
        return result
    monkeypatch.setattr(module,'linprog',lie)
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    with pytest.raises(ValueError,match='epigraph'):fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_priority='worst-first')


def test_priority_budget_expiry_keeps_checked_start_and_never_promotes_primary_lp():
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    value,r=fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],trust=.1,maximum_calls=2,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_priority='worst-first',proposal_tangent_guard=True)
    assert r['stop']=='time_or_measurement_budget' and r['trials'][-1]['accepted']
    np.testing.assert_array_equal(value,r['trials'][-1]['controls'])
    assert not r['proposal_starts'][0]['retained'] and not r['proposal_queries'] and np.all(measure(value)>=0)


def test_no_worst_progress_is_a_search_failure_not_nonlinear_infeasibility():
    def measure(x):return np.array([-.5,x[0]-.1,1-x[0]**2])
    def derivative(x):return measure(x),np.array([[0.],[1.],[-2*x[0]]])
    def vectors(x):return dict(offsets=np.array([[x[0],0.,0.]]),jacobian=np.array([[[1.],[0.],[0.]]]),
        limits=np.array([1.]),scales=np.array([1.]),rows=np.array([2]),distance=np.array([False]))
    value,r=fit(measure,derivative,[0.],[-1.],[1.],proposal='nonlinear',proposal_start='geometry-descent',
        vectorize=vectors,proposal_priority='worst-first')
    np.testing.assert_array_equal(value,[0.])
    assert r['proposal_starts'][0]['status']=='no_checked_worst_descent' and not r['trials']
    assert not r['quality_approved']


@pytest.mark.parametrize('kwargs',[dict(proposal_priority='guess'),dict(proposal_priority=True),dict(proposal_priority='worst-first')])
def test_invalid_priority_rejected_before_measurement(kwargs):
    def forbidden(x):raise AssertionError('Invalid priority reached measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.],[-1.],[1.],**kwargs)


@pytest.mark.parametrize('damage',['nonfinite','rows','width','scale','source'])
def test_geometry_start_rejects_missing_or_changed_vector_population(damage):
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    def vectors(x):
        v=circle_vectors(x)
        if damage=='nonfinite':v['jacobian'][0,0,0]=float('nan')
        if damage=='rows':v['rows']=np.array([2])
        if damage=='width':v['jacobian']=np.zeros((1,3,1))
        if damage=='scale':v['scales'][0]=0
        if damage=='source':v['offsets'][0,0]=.09
        return v
    with pytest.raises((ValueError,AssertionError)):fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=vectors)


def test_geometry_budget_expiry_keeps_only_fully_replayed_accepted_start():
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    value,r=fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],trust=.1,maximum_calls=2,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_tangent_guard=True)
    assert r['stop']=='time_or_measurement_budget' and r['proposal_starts'][0]['success']
    assert r['trials'][-1]['accepted'] and r['trials'][-1]['stage']=='geometry-start'
    np.testing.assert_array_equal(value,r['trials'][-1]['controls'])
    assert np.all(measure(value)>=0) and not r['proposal_queries']


def test_geometry_budget_expiry_never_selects_failed_nonlinear_start():
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x+np.array([x[1]**2,0.])))/.1])
    def derivative(x):
        vector=x+np.array([x[1]**2,0.]);j=np.array([[1.,2*x[1]],[0.,1.]])
        return measure(x),np.array([[0.,1.],-vector@j/(.1*np.linalg.norm(vector))])
    value,r=fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],trust=.1,maximum_calls=2,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_tangent_guard=True)
    np.testing.assert_array_equal(value,[.1,0.])
    assert r['stop']=='time_or_measurement_budget' and r['proposal_starts'][0]['success']
    assert len(r['trials'])==1 and not r['trials'][0]['accepted'] and not r['proposal_queries']


def test_body_search_margin_preserves_curved_nonlinear_row_without_relaxing_retention():
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x+np.array([x[1]**2,0.])))/.1])
    def derivative(x):
        vector=x+np.array([x[1]**2,0.]);j=np.array([[1.,2*x[1]],[0.,1.]])
        return measure(x),np.array([[0.,1.],-vector@j/(.1*np.linalg.norm(vector))])
    value,r=fit(measure,derivative,[.1,0.],[-1.,-1.],[1.,1.],trust=.1,iterations=1,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_tangent_guard=True,
        proposal_headroom=[0.,1e-3])
    assert value[1]>0 and r['trials'][-1]['accepted'] and r['trials'][-1]['stage']=='geometry-start'
    assert r['trials'][-1]['fraction']<1 and measure(value)[1]>=0 and not r['proposal_queries']
    assert not r['trials'][0]['accepted'] and not r['trials'][0]['retention_guard_passed']
    assert r['proposal_starts'][0]['caps'][1]==1e-3 and r['proposal_linearizations'][0]['preservation_caps'][1]==0
    assert r['source_passing_rows_preserved'] and not r['quality_approved']


@pytest.mark.parametrize('kwargs',[dict(proposal_start='geometry-descent',proposal='nonlinear'),
    dict(vectorize=circle_vectors),dict(proposal_start='geometry-descent',proposal='nonlinear',vectorize=True)])
def test_vector_initializer_contract_rejected_before_measurement(kwargs):
    def forbidden(x):raise AssertionError('Invalid geometry request reached measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.,0.],[-1.,-1.],[1.,1.],**kwargs)


def test_margin_fallback_escapes_search_conflict_with_unchanged_physical_gates(tmp_path):
    from pose_proposal_archive import ProposalArchive,load_record
    from protected_inequality_step import margin_start_attempts
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    options=dict(iterations=1,trust=.1,proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,
        proposal_tangent_guard=True,proposal_headroom=[0.,1e-3],proposal_priority='worst-first')
    old,a=fit(measure,derivative,[.1,0.],[.09995,-1.],[1.,1.],**options)
    output=tmp_path/'study';output.mkdir()
    value,b=fit(measure,derivative,[.1,0.],[.09995,-1.],[1.,1.],proposal_margin_fallback=True,record_store=ProposalArchive(output),**options)
    assert a['stop']=='linear_start_unavailable' and not a['trials']
    np.testing.assert_array_equal(old,[.1,0.])
    assert value[1]>0 and b['trials'][-1]['accepted'] and measure(value)[1]>=0
    assert b['source_passing_rows_preserved'] and b['nontradeoff_rows_preserved'] and not b['quality_approved']
    start,_=load_record(output,b['proposal_starts'][0]);attempts=margin_start_attempts(start)
    assert [attempt['margin_factor'] for attempt in attempts]==[1.,.25]
    assert not attempts[0]['success'] and attempts[1]['success'] and not start['retained']
    assert start['margin_fallback_max_seconds']<=20 and start['margin_floor_caps']==[-.05,0.]
    assert start['caps'][1]==.00025 and b['proposal_headroom_normalized']==[0.,.001]
    assert b['proposal_linearizations'][0]['kind']=='linearization'


def test_margin_fallback_never_removes_declared_point_feasibility():
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    value,r=fit(measure,derivative,[.1,0.],[.09995,-1.],[1.,1.],iterations=1,trust=.1,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_tangent_guard=True,
        proposal_headroom=[1e-5,1e-3],proposal_feasible_mask=[True,False],proposal_priority='worst-first',proposal_margin_fallback=True)
    np.testing.assert_array_equal(value,[.1,0.]);assert not r['trials'] and r['stop']=='linear_start_unavailable'
    start=r['proposal_starts'][0]
    assert start['margin_floor_caps'][0]==0 and start['caps'][0]==0
    assert [attempt['margin_factor'] for attempt in start['margin_fallback_attempts']]+[start['margin_factor']]==[1.,.25,.0625,0.]


def test_margin_fallback_keeps_original_budget_and_never_promotes_unmeasured_start():
    def measure(x):return np.array([x[1]-.05,(.1-np.linalg.norm(x))/.1])
    def derivative(x):return measure(x),np.array([[0.,1.],-x/(.1*np.linalg.norm(x))])
    value,r=fit(measure,derivative,[.1,0.],[.09995,-1.],[1.,1.],iterations=1,trust=.1,maximum_calls=1,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=circle_vectors,proposal_tangent_guard=True,
        proposal_headroom=[0.,1e-3],proposal_priority='worst-first',proposal_margin_fallback=True)
    np.testing.assert_array_equal(value,[.1,0.]);assert r['stop']=='time_or_measurement_budget' and not r['proposal_starts']


@pytest.mark.parametrize('kwargs',[dict(proposal_margin_fallback=1),dict(proposal_margin_fallback=True)])
def test_invalid_margin_fallback_rejected_before_measurement(kwargs):
    def forbidden(x):raise AssertionError('Invalid fallback reached measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.],[-1.],[1.],**kwargs)


def curved_surface(x):return np.array([x[1]-.05,.1-x[0]-x[1]**2])


def curved_surface_pair(x):return curved_surface(x),np.array([[0.,1.],[-1.,-2*x[1]]])


def curved_surface_vectors(x):
    return dict(offsets=np.array([[x[0]+x[1]**2,0.,0.]]),jacobian=np.array([[[1.,2*x[1]],[0.,0.],[0.,0.]]]),
        limits=np.array([.1]),scales=np.array([1.]),rows=np.array([1]),distance=np.array([True]))


def test_trial_correction_repairs_curvature_without_losing_original_surface_constraint(tmp_path):
    from pose_proposal_archive import ProposalArchive,load_record
    options=dict(iterations=1,trust=.1,solve_iterations=1,proposal='nonlinear',proposal_start='geometry-descent',
        vectorize=curved_surface_vectors,proposal_tangent_guard=True)
    old,a=fit(curved_surface,curved_surface_pair,[.1,0.],[-1.,-1.],[1.,1.],**options)
    output=tmp_path/'study';output.mkdir()
    value,b=fit(curved_surface,curved_surface_pair,[.1,0.],[-1.,-1.],[1.,1.],proposal_trial_correction=True,record_store=ProposalArchive(output),**options)
    assert value[1]>.02 and b['trials'][-1]['stage']=='geometry-start-correction' and b['trials'][-1]['accepted']
    assert curved_surface(value)[1]>=0 and b['source_passing_rows_preserved'] and b['nontradeoff_rows_preserved']
    assert b['final_score'][1]<a['final_score'][1] and not b['proposal_queries']
    correction,_=load_record(output,b['proposal_corrections'][0])
    assert correction['success'] and not correction['retained'] and correction['attempt']==1
    assert correction['correction_limit_normalized']==.025 and len(correction['jacobian'])==2
    assert b['trials'][-1]['parent_trial']==correction['parent_trial'] and not b['quality_approved']


def test_correction_call_budget_does_not_promote_rejected_parent_or_unmeasured_proposal():
    value,r=fit(curved_surface,curved_surface_pair,[.1,0.],[-1.,-1.],[1.,1.],iterations=1,trust=.1,maximum_calls=4,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=curved_surface_vectors,
        proposal_tangent_guard=True,proposal_trial_correction=True)
    np.testing.assert_array_equal(value,[.1,0.]);assert not r['proposal_corrections'] and r['stop']=='time_or_measurement_budget'
    assert len(r['trials'])==3 and not any(t['accepted'] for t in r['trials'])


def test_invalid_candidate_derivative_never_reaches_correction_lp():
    def broken(x):
        if x[1]>0:return curved_surface(x),np.zeros((1,2))
        return curved_surface_pair(x)
    with pytest.raises(ValueError,match='correction derivatives'):fit(curved_surface,broken,[.1,0.],[-1.,-1.],[1.,1.],iterations=1,trust=.1,
        proposal='nonlinear',proposal_start='geometry-descent',vectorize=curved_surface_vectors,
        proposal_tangent_guard=True,proposal_trial_correction=True)


@pytest.mark.parametrize('kwargs',[dict(proposal_trial_correction=1),dict(proposal_trial_correction=True)])
def test_invalid_trial_correction_rejected_before_measurement(kwargs):
    def forbidden(x):raise AssertionError('Invalid correction reached measurement')
    with pytest.raises(ValueError):fit(forbidden,forbidden,[0.],[-1.],[1.],**kwargs)
