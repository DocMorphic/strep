import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import iterated_witness_repair as implementation
from hand_norm_proposal import measurement


def sample(x):
    return dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.array([x[1]-.2,.5]),depths=np.array([.02-.01*x[0]]))


def result(point,history=None):
    return None,dict(final_point=np.asarray(point).tolist(),final=measurement(sample(point)),history=[] if history is None else history)


def test_next_linearization_starts_at_exact_ray_result(monkeypatch):
    starts=[]
    def local(exact,smooth,original,seed,*args,**kwargs):
        starts.append(seed.copy())
        if len(starts)==1:return result(seed,[dict(proposal=dict(delta=[0.,.1]))])
        return result([.5,.2])
    monkeypatch.setattr(implementation,'restore',local)
    monkeypatch.setattr(implementation,'scan',lambda *args,**kwargs:result([.5,.15]))
    point,report=implementation.solve(sample,sample,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1)
    np.testing.assert_array_equal(starts,[[.5,.1],[.5,.15]])
    np.testing.assert_array_equal(point,[.5,.2])
    assert report['numerically_feasible'] and len(report['history'])==2 and not report['quality_approved']


def test_no_improvement_stops_without_repeating_same_proposal(monkeypatch):
    calls=[]
    def local(*args,**kwargs):calls.append(1);return result([.5,.1],[dict(proposal={})])
    monkeypatch.setattr(implementation,'restore',local)
    point,report=implementation.solve(sample,sample,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1)
    assert point is None and len(calls)==1 and report['stop_reason']=='no_admissible_progress'


def test_orchestrator_checks_motion_after_each_stage(monkeypatch):
    def actual(x):
        value=sample(x)
        if x[0]>.4 and x[1]>=.2:value['vectors'][0,0]=1.001
        return value
    monkeypatch.setattr(implementation,'restore',lambda *args,**kwargs:result([.5,.2]))
    point,report=implementation.solve(actual,actual,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1)
    assert point is None and not report['history'][0]['internal_step']


def test_caps_cannot_be_rebased_between_iterations(monkeypatch):
    cap=np.ones(1)
    def actual(x):
        value=sample(x);value['caps']=cap;return value
    def local(*args,**kwargs):cap.fill(2.);return result([.5,.15])
    monkeypatch.setattr(implementation,'restore',local)
    with pytest.raises(ValueError,match='across iterations'):
        implementation.solve(actual,actual,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1)


@pytest.mark.parametrize('options',[dict(iterations=0),dict(divisions=7),dict(trust=0)])
def test_invalid_budget(options):
    with pytest.raises(ValueError):implementation.solve(sample,sample,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1,**options)
