import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import waypoint_projection
from sampled_motion_caps import SampledMotionCaps,features


class Model:
    rig=SimpleNamespace(joints=[0])
    def evaluate(self,parameters):
        world=np.tile(np.eye(4),(len(parameters),1,1,1));world[:,0,0,3]=parameters[:,0]
        return world,0.


@pytest.mark.parametrize('method',['COBYLA','SLSQP'])
@pytest.mark.parametrize('start',['source','target'])
def test_reported_optimizer_success_does_not_accept_infeasible_controls(monkeypatch,method,start):
    model=Model();native=np.arange(5.);target=np.zeros((5,3));target[1:-1,0]=.06
    caps=SampledMotionCaps(features(model.evaluate(np.zeros_like(target))[0],[0]),native,[0,2,4])
    def fake_minimize(fun,x0,**kwargs):
        x=(target[1:-1]/[.06,30,30]).ravel()
        np.testing.assert_array_equal(x0,np.zeros_like(x) if start=='source' else x)
        return SimpleNamespace(x=x,fun=fun(x),success=True,status=0,message='Synthetic success',nfev=1)
    monkeypatch.setattr(waypoint_projection,'minimize',fake_minimize)
    best,result,records=waypoint_projection.project([model],caps,native,target,[.8,300,300],max_evaluations=10,method=method,start=start)
    assert result['success'] and result['returned_minimum_margin']<0
    assert best['feasible'] and not np.any(best['parameters']) and not records[1]['feasible']


@pytest.mark.parametrize('method',['COBYLA','SLSQP'])
def test_feasible_target_is_kept_even_if_optimizer_stops_at_evaluation_limit(method):
    model=Model();native=np.arange(5.);target=np.zeros((5,3));target[1:-1,0]=.02
    caps=SampledMotionCaps(features(model.evaluate(np.zeros_like(target))[0],[0]),native,[0,2,4],tolerance=.1)
    best,result,records=waypoint_projection.project([model],caps,native,target,[.8,300,300],max_evaluations=5,method=method)
    assert best['feasible'] and best['objective']==0
    np.testing.assert_array_equal(best['parameters'],target)
