import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import coupled_support_block as module


class NarrowProblem:
    initial=np.zeros((1,1))
    frames=np.array([0])
    def pair(self,x):
        rows=module.Constraints(1)
        rows.lower(.1-x,np.array([[-1.]]),'contact')
        return float((1-x[0])**2),np.array([-2.]),rows,self.values(x)
    def values(self,x):return np.asarray(x).reshape(1,1)
    def midpoint_guard(self,values):return True,0.


def test_shorter_search_finds_feasible_step_without_relaxing_bound(monkeypatch):
    monkeypatch.setattr(module,'direction',lambda *args:(np.array([1.]),dict(predicted_change=-2.)))
    old,old_log=module.solve(NarrowProblem(),steps=1,trusts=(.005,))
    new,new_log=module.solve(NarrowProblem(),steps=1,trusts=(.005,),fractions=[2.**-n for n in range(11)])
    assert old[0,0]==0 and not old_log['history'][0]['accepted']
    assert new[0,0]==.0625 and new_log['history'][0]['accepted']
    assert new_log['history'][0]['attempts'][0]['trials'][-1]['margins']['contact']>=0


def test_short_steps_cannot_bypass_midpoint_guard(monkeypatch):
    monkeypatch.setattr(module,'direction',lambda *args:(np.array([1.]),dict(predicted_change=-2.)))
    problem=NarrowProblem();problem.midpoint_guard=lambda values:(False,.01)
    values,log=module.solve(problem,steps=1,trusts=(.005,),fractions=[2.**-n for n in range(11)])
    assert values[0,0]==0 and not log['history'][0]['accepted']


@pytest.mark.parametrize('fractions',[[],[.5],[1.,0.],[1.,.5,.5],[1.,float('nan')],[1.,2.],[2.**-n for n in range(12)]])
def test_invalid_search_protocol_is_rejected(fractions):
    with pytest.raises(ValueError):module.solve(NarrowProblem(),fractions=fractions)
