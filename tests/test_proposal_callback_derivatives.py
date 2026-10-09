"""Optimizer callback contract and budget/retention regressions."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import protected_inequality_step as module


def problem():
    calls=[]
    def measure(x):return np.array([x[0]-.2,.1-x[0]])
    def pair(x):calls.append(x.copy());return measure(x),np.array([[1.],[-1.]])
    return measure,pair,calls


def test_value_callbacks_measure_all_rows_without_derivatives_and_gradient_callbacks_share_cache(monkeypatch):
    measure,pair,calls=problem()
    def solver(fun,x0,**kwargs):
        for value in [.04,.03]:
            point=np.array([value]);actual=fun(point)
            assert isinstance(actual,float)
            np.testing.assert_array_equal(kwargs['constraints'][0]['fun'](point),measure(point)-np.array([-.2,0.]))
            assert len(calls)==1
        point=np.array([.03]);expected=2*(np.array([[1.],[-1.]]).T@np.minimum(measure(point)-1e-6,0)+1e-8*point)
        np.testing.assert_array_equal(kwargs['jac'](point),expected)
        assert len(calls)==2
        np.testing.assert_array_equal(kwargs['constraints'][0]['jac'](point),np.array([[1.],[-1.]]))
        assert len(calls)==2
        return SimpleNamespace(x=point,success=True,message='fixture')
    monkeypatch.setattr(module,'minimize',solver)
    value,report=module.fit(measure,pair,[0.],[-1.],[1.],iterations=1,trust=.1,proposal='nonlinear')
    np.testing.assert_array_equal(value,[.03])
    assert report['source_rows_preserved'] and report['trials'][0]['accepted']
    assert len(report['proposal_queries'])==2 and all(not q['retained'] for q in report['proposal_queries'])


def test_value_and_gradient_callbacks_use_same_clipped_controls(monkeypatch):
    measure,pair,calls=problem()
    def solver(fun,x0,**kwargs):
        point=np.array([.10000000000000002]);fun(point)
        assert len(calls)==1
        kwargs['jac'](point);kwargs['constraints'][0]['jac'](point)
        assert len(calls)==2 and calls[-1][0]==.1
        return SimpleNamespace(x=point,success=True,message='fixture')
    monkeypatch.setattr(module,'minimize',solver)
    value,report=module.fit(measure,pair,[0.],[0.],[.1],iterations=1,trust=.1,proposal='nonlinear')
    np.testing.assert_array_equal(value,[.1]);assert report['bounded_proposal_queries']
    assert report['source_rows_preserved'] and not report['quality_approved']


@pytest.mark.parametrize('fault',['missing','nonfinite','different_values'])
def test_requested_derivatives_still_require_full_matching_population(monkeypatch,fault):
    measure,good,calls=problem()
    def pair(x):
        if x[0]==0:return good(x)
        if fault=='missing':return measure(x)[:1],np.ones((1,1))
        if fault=='nonfinite':return measure(x),np.full((2,1),np.nan)
        return measure(x)+1.,np.array([[1.],[-1.]])
    def solver(fun,x0,**kwargs):
        point=np.array([.04]);assert isinstance(fun(point),float)
        assert len(calls)==1
        kwargs['jac'](point)
        raise AssertionError('Invalid derivative reached retention')
    monkeypatch.setattr(module,'minimize',solver)
    with pytest.raises(AssertionError if fault=='different_values' else ValueError):
        module.fit(measure,pair,[0.],[-1.],[1.],iterations=1,trust=.1,proposal='nonlinear')


@pytest.mark.parametrize('fault',['missing','nonfinite'])
def test_value_callbacks_reject_incomplete_or_nonfinite_population_before_jacobian(monkeypatch,fault):
    measure,pair,calls=problem()
    def bad(x):
        if x[0]==0:return measure(x)
        return measure(x)[:1] if fault=='missing' else np.array([np.nan,0.])
    def solver(fun,x0,**kwargs):
        fun(np.array([.04]));raise AssertionError('Invalid values reached derivative request')
    monkeypatch.setattr(module,'minimize',solver)
    with pytest.raises(ValueError):module.fit(bad,pair,[0.],[-1.],[1.],iterations=1,trust=.1,proposal='nonlinear')
    assert len(calls)==1


def test_call_budget_between_value_and_gradient_never_promotes_unretained_query(monkeypatch):
    measure,pair,calls=problem();observations=[]
    def solver(fun,x0,**kwargs):
        point=np.array([.04]);fun(point);kwargs['jac'](point)
        raise AssertionError('Expired query reached solver completion')
    monkeypatch.setattr(module,'minimize',solver)
    value,report=module.fit(measure,pair,[0.],[-1.],[1.],iterations=1,trust=.1,maximum_calls=2,
        proposal='nonlinear',observer=lambda name,x,slack,keep:observations.append((name,x.copy(),keep)))
    np.testing.assert_array_equal(value,[0.])
    assert len(calls)==1 and report['measurement_calls']==2 and report['stop']=='time_or_measurement_budget'
    assert len(report['proposal_queries'])==1 and not report['trials']
    assert observations[-1][0]=='final' and observations[-1][1][0]==0.


def test_time_budget_between_value_and_gradient_preserves_last_retained_point(monkeypatch):
    measure,pair,calls=problem();clock=[0.]
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    def solver(fun,x0,**kwargs):
        point=np.array([.04]);fun(point);clock[0]=2.;kwargs['jac'](point)
        raise AssertionError('Expired query reached solver completion')
    monkeypatch.setattr(module,'minimize',solver)
    value,report=module.fit(measure,pair,[0.],[-1.],[1.],iterations=1,trust=.1,seconds=1.,proposal='nonlinear')
    np.testing.assert_array_equal(value,[0.])
    assert len(calls)==1 and report['stop']=='time_or_measurement_budget'
    assert len(report['proposal_queries'])==1 and not report['proposal_queries'][0]['retained']


def test_cached_values_are_detached_from_reused_measurement_storage(monkeypatch):
    shared=np.zeros(2)
    def measure(x):
        shared[:]=[x[0]-.2,.1-x[0]];return shared
    def pair(x):
        result=measure(x)
        if x[0]!=0:result+=1.
        return result,np.array([[1.],[-1.]])
    def solver(fun,x0,**kwargs):
        point=np.array([.04]);fun(point);kwargs['jac'](point)
        raise AssertionError('Changed linearized values reached retention')
    monkeypatch.setattr(module,'minimize',solver)
    with pytest.raises(AssertionError):
        module.fit(measure,pair,[0.],[-1.],[1.],iterations=1,trust=.1,proposal='nonlinear')
