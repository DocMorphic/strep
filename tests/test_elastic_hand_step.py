import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from elastic_hand_step import solve


def test_restoration_improves_infeasible_surface_without_relaxing_motion_limit():
    def objective(x):
        gap=.05*x[0]-.02
        return .5*(gap*100)**2,np.array([gap*500])
    def inequalities(x):return np.array([.05*x[0]-.02,.02-x[0]]),np.array([[.05],[-1.]])
    result=solve(objective,inequalities,np.array([0.]),np.array([-.05]),np.array([.05]),1)
    assert .01999<result.x[0]<=.020001
    assert inequalities(result.x)[0][1]>=-1e-7
    assert -.020<inequalities(result.x)[0][0]<0
    assert result.restoration_slack_m>.0189
    assert inequalities(result.x)[0][0]+result.restoration_slack_m>=-1e-7


def test_feasible_motion_does_not_require_final_slack():
    def objective(x):return .5*(x[0]-.01)**2*100,np.array([(x[0]-.01)*100])
    def inequalities(x):return np.array([x[0]]),np.ones((1,1))
    result=solve(objective,inequalities,np.array([0.]),np.array([-.05]),np.array([.05]),1)
    assert abs(result.x[0]-.01)<1e-5
    assert result.restoration_slack_m<1e-7
