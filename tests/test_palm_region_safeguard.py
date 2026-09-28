import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import paired_palm_region as region


def harness(monkeypatch,depth):
    fitter=SimpleNamespace(bounds=np.ones(1),actors=[],event=0,
        objective_pair=lambda x:(x-1,np.ones((1,1))))
    monkeypatch.setattr(region,'correspondences',lambda actors,frame,x,faces,margin:([dict(points=[])],[dict(max_depth_m=depth(float(x[0])))]))
    monkeypatch.setattr(region,'contact_records',lambda *_:([],[]))
    class Frozen:
        def __init__(self,*_):self.records=[]
        def contact(self,x):return np.empty(0),np.empty((0,len(x)))
    monkeypatch.setattr(region,'CorrespondenceEvaluator',Frozen)
    monkeypatch.setattr(region,'minimize',lambda *_,**kw:SimpleNamespace(x=np.ones(1),success=True,message='Unconstrained proposal',nit=1))
    return region.refine(fitter,np.zeros(1),None,iterations=1,safeguard=True)


def test_backtracking_rejects_new_collision_then_accepts_feasible_descent(monkeypatch):
    x,history=harness(monkeypatch,lambda x:max(0.,x-.035))
    assert abs(x[0]-np.radians(5)/4)<1e-12
    trials=history[-1]['step_trials']
    assert [t['accepted'] for t in trials]==[False,False,True]
    assert [t['alpha'] for t in trials]==[1,.5,.25]
    assert history[-1]['collision'][0]['max_depth_m']==0


def test_all_collision_trials_rejected_preserves_feasible_input(monkeypatch):
    x,history=harness(monkeypatch,lambda x:1. if x>0 else 0.)
    assert x[0]==0
    assert len(history[-1]['step_trials'])==8
    assert not any(t['accepted'] for t in history[-1]['step_trials'])
