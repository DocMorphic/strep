import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import restore_witness_feasibility as implementation


def sample(x):
    return dict(vectors=np.array([[.05,0.,0.]]),caps=np.array([.1]),scales=np.ones(1),
        margins=np.array([x[1]-.2,.5]),depths=np.array([.02-.01*x[0]]))


def test_surface_repair_accepts_only_original_exact_limits(monkeypatch):
    monkeypatch.setattr(implementation,'direction',lambda *args:(np.array([0.,.1]),dict(status='Solved')))
    point,report=implementation.restore(sample,sample,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1,reserve_floor=.2)
    np.testing.assert_array_equal(point,[.5,.2])
    assert report['numerically_feasible'] and report['final']['minimum_margin']==0
    assert report['mesh_validation_required'] and not report['quality_approved']


def test_internal_step_cannot_trade_motion_failure_for_better_worst_margin(monkeypatch):
    def actual(x):
        value=sample(x)
        if x[0]>.4 and x[1]>=.15:value['vectors'][0,0]=.11
        return value
    monkeypatch.setattr(implementation,'direction',lambda *args:(np.array([0.,.1]),dict(status='Solved')))
    point,report=implementation.restore(actual,actual,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1,iterations=1)
    assert point is None
    assert not report['history'][0]['trials'][0]['eligible']
    assert report['history'][0]['trials'][0]['minimum_margin']>report['seed']['minimum_margin']
    assert implementation.hard_margin(actual(report['final_point']),np.array([0]))>=0


def test_elastic_slack_cannot_relax_vector_or_other_scalar_constraints():
    base=dict(vectors=np.array([[.2,0.,0.]]),caps=np.array([.1]),scales=np.ones(1),
        margins=np.array([-.2,-.01]),depths=np.array([.02]))
    model=dict(point=np.zeros(1),base=base,jacobian=dict(vectors=np.zeros((1,3,1)),margins=np.zeros((2,1)),depths=np.ones((1,1))))
    a,b,record=implementation.assemble(model,.1,.03,np.array([0]),np.array([.02]))
    slack=b-a@np.array([0.,10.]);cone=slack[record['linear_rows']:]
    assert slack[0]>0 and slack[1]<0
    assert cone[0]<np.linalg.norm(cone[1:])
    np.testing.assert_array_equal(b[:2],[-.22,-.01])


def test_reserve_uses_measured_serialization_discrepancy_without_mutating_caps(monkeypatch):
    saved=[]
    def smooth(x):
        value=sample(x);value['margins'][0]+=.03;return value
    def proposal(model,trust,ceiling,rows,reserve,solver):
        saved.append(reserve.copy());return None,dict(status='test')
    monkeypatch.setattr(implementation,'direction',proposal)
    _,report=implementation.restore(sample,smooth,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1,reserve_floor=.01)
    np.testing.assert_allclose(saved[0],[.07],rtol=0,atol=1e-16)
    assert report['stop_reason']=='no_admissible_violation_reduction'


def test_rebased_caps_are_rejected(monkeypatch):
    cap=np.array([.1])
    def actual(x):
        value=sample(x);value['caps']=cap;return value
    monkeypatch.setattr(implementation,'direction',lambda *args:(np.array([0.,.01]),dict(status='Solved')))
    with pytest.raises(ValueError,match='remain fixed'):
        implementation.restore(actual,actual,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1,checkpoint=lambda *args:cap.fill(.2))


def test_starting_motion_failure_is_rejected():
    def actual(x):
        value=sample(x)
        if x[0]>.4:value['vectors'][0,0]=.11
        return value
    with pytest.raises(ValueError,match='non-witness'):
        implementation.restore(actual,actual,[0.,.3],[.5,.1],None,witness_start=0,witness_count=1)


@pytest.mark.parametrize('settings',[dict(witness_start=-1),dict(witness_count=3),dict(iterations=0),dict(reserve_floor=-1)])
def test_invalid_settings(settings):
    options=dict(witness_start=0,witness_count=1);options.update(settings)
    with pytest.raises(ValueError):implementation.restore(sample,sample,[0.,.3],[.5,.1],None,**options)
