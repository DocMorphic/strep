from pathlib import Path
import sys
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from kimodo_scene_retention import MetricRetainedSceneGuide


def values():
    return torch.ones((1,3,2),dtype=torch.float64),torch.ones((1,3),dtype=torch.bool),None,torch.tensor([0])


def test_tradeoff_rejects_every_fixed_ray_and_returns_original_object():
    x,v,m,t=values();calls=[]
    def metrics(q):calls.append(1);return {'contact':q.detach().numpy().copy(),'depth':(2-q).detach().numpy().copy()}
    guide=MetricRetainedSceneGuide(lambda q:q.square().sum(),metrics)
    assert guide.project(x,v,m,t) is x
    r=guide.records[-1];assert r['accepted_steps']==0 and r['energy_proposal_accepted_steps']>0 and r['metric_retention']=='rejected' and len(r['metric_trials'])==3 and len(calls)==4


def test_joint_improvement_is_retained_with_every_metric_row():
    x,v,m,t=values();guide=MetricRetainedSceneGuide(lambda q:q.square().sum(),lambda q:{'contact':q.detach().numpy(),'floor':(q*0).detach().numpy()})
    with torch.inference_mode():out=guide.project(x,v,m,t)
    r=guide.records[-1];assert r['metric_retention']=='accepted' and torch.all(out<x) and r['metric_trials'][-1]['metrics']['complete_metric_rows']==12


def test_disabled_calls_neither_metrics_nor_energy():
    x,v,m,t=values();calls=[];guide=MetricRetainedSceneGuide(lambda q:calls.append(1),lambda q:calls.append(2),step_l2=0)
    assert guide.project(x,v,m,t) is x and not calls


def test_changed_metric_population_stops_instead_of_dropping_a_condition():
    x,v,m,t=values();count=[0]
    def metrics(q):count[0]+=1;return {('original' if count[0]==1 else 'new'):q.detach().numpy()}
    with pytest.raises(ValueError):MetricRetainedSceneGuide(lambda q:q.square().sum(),metrics).project(x,v,m,t)
