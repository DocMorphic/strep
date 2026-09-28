import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import coupled_support_block as original
import support_backtracking_fallback as fallback


class Problem:
    initial=np.zeros((1,1));frames=np.array([0])
    def pair(self,x):
        c=original.Constraints(1);c.lower(.1-x,np.array([[-1.]]),'height')
        return float((1-x[0])**2),np.array([-2.]),c,self.values(x)
    def values(self,x):return np.asarray(x).reshape(1,1)
    def midpoint_guard(self,values):return True,0.


def test_later_original_trust_setting_keeps_priority(monkeypatch):
    def direction(p,x,trust):return np.array([1. if trust==.005 else .09]),dict(predicted_change=-1.,trust=trust)
    monkeypatch.setattr(original,'direction',direction);monkeypatch.setattr(fallback,'direction',direction)
    legacy,_=original.solve(Problem(),steps=1)
    interleaved,_=original.solve(Problem(),steps=1,fractions=original_fractions())
    selected,log=fallback.solve(Problem(),steps=1)
    assert legacy[0,0]==selected[0,0]==.09
    assert interleaved[0,0]==.0625
    assert all(t['phase']=='original' for a in log['history'][0]['attempts'] for t in a['trials'])


def original_fractions():return [2.**-n for n in range(11)]


def test_fallback_reuses_direction_only_after_original_failure(monkeypatch):
    calls=[]
    def direction(p,x,trust):calls.append(trust);return np.ones(1),dict(predicted_change=-1.,trust=trust)
    monkeypatch.setattr(fallback,'direction',direction)
    values,log=fallback.solve(Problem(),steps=1,trusts=(.005,.001))
    assert calls==[.005,.001] and values[0,0]==.0625
    assert log['history'][0]['attempts'][0]['trials'][-1]['phase']=='fallback'
    assert len(log['history'][0]['attempts'][1]['trials'])==4


def test_fallback_still_rejects_midpoint_failure(monkeypatch):
    monkeypatch.setattr(fallback,'direction',lambda *a:(np.ones(1),dict(predicted_change=-1.)))
    problem=Problem();problem.midpoint_guard=lambda v:(False,.01)
    values,log=fallback.solve(problem,steps=1,trusts=(.005,))
    assert values[0,0]==0 and not log['history'][0]['accepted']
