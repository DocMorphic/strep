from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import conic_buffer_schedule as scheduled
from reconstruct_descent import reconstruct


class Problem:
    frames=np.array([0]);free=np.array([0]);initial=np.zeros((1,1))
    def values(self,x):return np.asarray(x).reshape(1,1)
    def evaluate(self,x):return ((1-x[0])**2,None,np.array([.08-x[0]]),None,None,self.values(x))
    def geometric_guard(self,values):return True


def test_fallback_is_bounded_and_reconstruction_binds_buffers(monkeypatch):
    calls=[]
    def direction(p,x,trust,buffers):
        calls.append(buffers.copy());record=dict(trust=trust,proposal_buffers=buffers,predicted_objective_change=-.1)
        return (None if buffers['support_speed']==1. else np.array([.05])),record
    monkeypatch.setattr(scheduled,'direction',direction)
    schedule=[dict(buffer_scale=scale,trust=.1) for scale in [1.,.1,0.]]
    p=Problem();result,solver=scheduled.solve(p,1,[.1],None,dict(support_speed=1.),schedule)
    assert len(calls)==2 and result[0,0]==.05
    request=dict(steps=1,trusts=[.1],proposal_schedule=schedule,proposal_buffers=dict(support_speed=1.))
    np.testing.assert_array_equal(reconstruct(p.initial,solver,request,p.frames,p.free),result)
    wrong=copy.deepcopy(solver);wrong['history'][0]['attempts'][1]['proposal_buffers']['support_speed']=0.
    with pytest.raises(ValueError,match='buffers'):reconstruct(p.initial,wrong,request,p.frames,p.free)


def test_zero_buffer_does_not_relax_actual_acceptance(monkeypatch):
    def direction(p,x,trust,buffers):
        return np.array([.1]),dict(trust=trust,proposal_buffers=buffers,predicted_objective_change=-.1)
    monkeypatch.setattr(scheduled,'direction',direction)
    result,solver=scheduled.solve(Problem(),1,[.1],None,dict(support_speed=1.),[dict(buffer_scale=0.,trust=.1)])
    trials=solver['history'][0]['attempts'][0]['trials']
    assert trials[0]['minimum_constraint']<0 and not trials[0]['accepted']
    assert trials[1]['accepted'] and result[0,0]==.05
