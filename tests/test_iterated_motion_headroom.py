import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import iterated_motion_headroom as implementation


def sample(x):
    return dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.array([x[1]-.2,.5]),depths=np.array([.02-.01*x[0]]))


def stub_model(monkeypatch):
    monkeypatch.setattr(implementation,'linearize',lambda exact,smooth,point,*args:dict(base=exact(point),point=point.copy()))


def report(point):return None,dict(final_point=point,proposal={},trials=[])


def test_continuation_uses_exact_previous_internal_state(monkeypatch):
    stub_model(monkeypatch);starts=[]
    def repair(exact,original,start,*args,**kwargs):
        starts.append(start.copy());return report([.5,.15] if len(starts)==1 else [.5,.2])
    monkeypatch.setattr(implementation,'repair',repair)
    point,result=implementation.solve(sample,sample,[0.,.3],[.5,.1],{},None,witness_start=0,witness_count=1)
    np.testing.assert_array_equal(starts,[[.5,.1],[.5,.15]])
    np.testing.assert_array_equal(point,[.5,.2]);assert result['numerically_feasible'] and not result['quality_approved']


def test_stalled_proposal_stops_without_repeating(monkeypatch):
    stub_model(monkeypatch);calls=[]
    def repair(*args,**kwargs):calls.append(1);return report([.5,.1])
    monkeypatch.setattr(implementation,'repair',repair)
    point,result=implementation.solve(sample,sample,[0.,.3],[.5,.1],{},None,witness_start=0,witness_count=1)
    assert point is None and len(calls)==1 and result['stop_reason']=='no_admissible_progress'


def test_motion_failure_cannot_advance_internal_state(monkeypatch):
    stub_model(monkeypatch)
    def actual(x):
        value=sample(x)
        if x[0]>.4 and x[1]>=.2:value['vectors'][0,0]=1.01
        return value
    monkeypatch.setattr(implementation,'repair',lambda *args,**kwargs:report([.5,.2]))
    point,result=implementation.solve(actual,actual,[0.,.3],[.5,.1],{},None,witness_start=0,witness_count=1)
    assert point is None and not result['history'][0]['internal_step']


def test_caps_cannot_change_between_iterations(monkeypatch):
    stub_model(monkeypatch);cap=np.ones(1)
    def actual(x):return dict(sample(x),caps=cap)
    def repair(*args,**kwargs):cap.fill(2.);return report([.5,.15])
    monkeypatch.setattr(implementation,'repair',repair)
    with pytest.raises(ValueError,match='stay fixed'):
        implementation.solve(actual,actual,[0.,.3],[.5,.1],{},None,witness_start=0,witness_count=1)


@pytest.mark.parametrize('iterations',[0,13,True])
def test_iteration_budget_is_explicit(iterations):
    with pytest.raises(ValueError):
        implementation.solve(sample,sample,[0.,.3],[.5,.1],{},None,witness_start=0,witness_count=1,iterations=iterations)
