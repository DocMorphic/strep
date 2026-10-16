from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_scene_conic_sum import direction


def solve(vectors,caps,jac,*,hard=0,scales=None,trust=1.,value=None):
    n=np.asarray(jac).shape[-1];value=np.zeros(n) if value is None else value
    rows=NormRows(vectors,caps,np.ones(len(caps)) if scales is None else scales)
    delta,info=direction(rows,sparse.csc_matrix(np.asarray(jac).reshape(-1,n)),value,-np.ones(n),np.ones(n),trust,hard_rows=hard)
    return rows,delta,info


def test_aggregate_can_improve_many_rows_while_worst_row_is_invariant():
    rows,delta,info=solve([[10,0,0],[2,0,0],[2,0,0]],[0,0,0],[[[0],[0],[0]],[[-1],[0],[0]],[[-1],[0],[0]]])
    assert delta[0]>.999999 and info['fixed_soft_positive_sum']==10
    assert info['scalar_soft_rows']==2 and info['vector_soft_rows']==0
    assert np.maximum(rows.residual(),0).sum()>info['affine_positive_soft_sum']+1.99


def test_hard_vector_norm_preserves_perpendicular_components():
    rows,delta,info=solve([[0,.8,0],[2,0,0]],[1,0],[[[1],[0],[0]],[[-1],[0],[0]]],hard=1)
    assert .59999<delta[0]<.60001 and rows.residual(sparse.csr_matrix([[1],[0],[0],[-1],[0],[0]]),delta)[0]<1e-8
    assert info['affine_hard_rows_pass']


def test_scalar_negative_side_uses_absolute_norm_and_positive_hinge():
    _,delta,info=solve([[-2,0,0]],[0],[[[1],[0],[0]]])
    assert delta[0]>.99999 and .99999<info['affine_positive_soft_sum']<1.00001


def test_vector_soft_rows_retain_full_soc():
    _,delta,info=solve([[0,2,0]],[0],[[[0],[-1],[0]]])
    assert delta[0]>.99999 and info['vector_soft_rows']==1 and info['scalar_soft_rows']==0


def test_fixed_protected_conflict_never_returns_direction():
    _,delta,info=solve([[2,0,0],[2,0,0]],[1,0],[[[0],[0],[0]],[[-1],[0],[0]]],hard=1)
    assert delta is None and info['status']=='FixedProtectedConflict'


def test_box_clipped_controls_and_row_units_are_preserved():
    _,delta,info=solve([[2,0,0]],[0],[[[-2],[0],[0]]],scales=[.01],trust=.5,value=np.array([.9]))
    assert .09999<delta[0]<=.10000000001 and info['maximum_control_step']<=.10000000001


def test_no_active_soft_rows_uses_minimum_norm_feasible_step():
    _,delta,info=solve([[0,0,0]],[1],[[[1],[0],[0]]],hard=1)
    assert abs(delta[0])<1e-8 and info['responsive_soft_rows']==0


@pytest.mark.parametrize('fault',['shape','nan','budget','hard','trust'])
def test_invalid_or_overbudget_population_rejects(fault):
    rows=NormRows([[2,0,0],[2,0,0]],[0,0],[1,1]);jac=sparse.csc_matrix([[-1],[0],[0],[-1],[0],[0]],dtype=float)
    kwargs=dict(hard_rows=0,maximum_soft_rows=100000);trust=1.
    if fault=='shape':jac=jac[:3]
    elif fault=='nan':jac.data[0]=np.nan
    elif fault=='budget':kwargs['maximum_soft_rows']=1
    elif fault=='hard':kwargs['hard_rows']=True
    else:trust=True
    with pytest.raises(ValueError):direction(rows,jac,np.zeros(1),-np.ones(1),np.ones(1),trust,**kwargs)


def precision(monkeypatch,points,statuses=None):
    import native_scene_conic_sum as module
    from types import SimpleNamespace
    actual=module.solver_module();calls=[];statuses=statuses or ['Solved']*len(points)
    def solver(p,q,a,b,cones,settings):
        index=len(calls);calls.append(dict(p=p.copy(),q=q.copy(),a=a.copy(),b=b.copy(),tol=settings.tol_feas,max_iter=settings.max_iter,time_limit=settings.time_limit))
        return SimpleNamespace(solve=lambda:SimpleNamespace(status=statuses[index],iterations=3,x=points[index]))
    fake=SimpleNamespace(DefaultSettings=actual.DefaultSettings,DefaultSolver=solver,NonnegativeConeT=actual.NonnegativeConeT,SecondOrderConeT=actual.SecondOrderConeT,__version__=actual.__version__)
    monkeypatch.setattr(module,'solver_module',lambda:fake)
    rows,delta,info=solve([[0,.8,0],[2,0,0]],[1,0],[[[1],[0],[0]],[[-1],[0],[0]]],hard=1)
    return rows,delta,info,calls


def test_precision_retry_measures_full_hard_norm_and_keeps_same_problem(monkeypatch):
    rows,delta,info,calls=precision(monkeypatch,[[.60001,1.4],[.599999999,1.4]])
    assert len(calls)==2 and calls[0]['tol']==1e-9 and calls[1]['tol']==1e-11
    for key in ('p','a'):assert (calls[0][key]!=calls[1][key]).nnz==0
    for key in ('q','b'):np.testing.assert_array_equal(calls[0][key],calls[1][key])
    assert all(v['max_iter']==100 and v['time_limit']==30 for v in calls)
    assert info['affine_hard_rows_pass'] and not info['returned_for_diagnostics_only']
    assert [v['selected'] for v in info['attempts']]==[False,True]
    assert info['attempts'][0]['affine_failed_hard_rows']==1 and info['attempts'][0]['delta']==[.60001]
    assert delta[0]<.6 and info['hard_postcheck_tolerance']==1e-8
    np.testing.assert_array_equal(rows.caps,[1,0])


def test_two_failed_numerical_attempts_remain_diagnostic(monkeypatch):
    _,delta,info,calls=precision(monkeypatch,[[.60001,1.4],[.60002,1.4]])
    assert len(calls)==2 and delta[0]>.6 and not info['affine_hard_rows_pass'] and info['returned_for_diagnostics_only']
    assert all(not v['selected'] and len(v['delta'])==1 for v in info['attempts'])


@pytest.mark.parametrize('failure',['status','invalid'])
def test_failed_precision_retry_cannot_adopt_the_first_failed_point(monkeypatch,failure):
    points=[[.60001,1.4],[.5,1.5] if failure=='status' else [2.,1.5]]
    statuses=['Solved','MaxIterations'] if failure=='status' else None
    _,delta,info,calls=precision(monkeypatch,points,statuses)
    assert len(calls)==2 and delta[0]==.60001 and info['returned_for_diagnostics_only'] and not info['affine_hard_rows_pass']
    assert not any(v['selected'] for v in info['attempts'])
    if failure=='status':
        assert info['attempts'][1]['delta']==[.5] and info['attempts'][1]['affine_hard_rows_pass']


def test_already_feasible_point_does_not_trigger_another_solve(monkeypatch):
    _,delta,info,calls=precision(monkeypatch,[[.5,1.5]])
    assert len(calls)==1 and delta[0]==.5 and info['affine_hard_rows_pass'] and not info['precision_retry_performed']


def test_first_failed_status_retains_finite_point_without_returning_it(monkeypatch):
    _,delta,info,calls=precision(monkeypatch,[[.5,1.5]],['NumericalError'])
    assert delta is None and len(calls)==1 and info['returned_phase'] is None
    assert info['attempts'][0]['delta']==[.5] and info['attempts'][0]['affine_hard_rows_pass']
    assert not info['attempts'][0]['selected']
