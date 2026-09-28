from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from feasible_descent import direction,solve


def test_direction_preserves_active_linear_constraint_and_absolute_box():
    delta,record=direction(np.array([0.,.95]),np.array([-1.,-2.]),np.array([0.]),np.array([[-1.,0.]]),np.ones(2),.1,0.)
    assert record['success'] and delta[0]<=1e-10 and .95+delta[1]<=1.+1e-10
    assert record['predicted_objective_change']<0


def test_nonfinite_and_fixed_violated_rows_rejected():
    args=[np.zeros(1),np.ones(1),np.array([-1.]),np.zeros((1,1)),np.ones(1),.1]
    assert direction(*args)[0] is None
    args[1][0]=np.nan
    with pytest.raises(ValueError):direction(*args)


class Toy:
    initial=np.zeros((1,1));frames=np.array([0]);free=np.array([0])
    class Fitter:bounds=np.array([2.])
    fitter=Fitter()
    def values(self,x):return np.asarray(x).reshape(1,1)
    def evaluate(self,x):
        t=x[0]
        return ((t-1)**2,np.array([2*(t-1)]),np.array([.25-t*t]),np.array([[-2*t]]),None,self.values(x))
    def geometric_guard(self,values):return True


def test_nonlinear_guard_rejects_full_lp_step_but_accepts_feasible_backtrack():
    values,proof=solve(Toy(),steps=1,trusts=(1.,),margin=0.)
    assert values[0,0]==.5
    trials=proof['history'][0]['attempts'][0]['trials']
    assert not trials[0]['accepted'] and trials[1]['accepted'] and proof['minimum_constraint']>=-1e-8
