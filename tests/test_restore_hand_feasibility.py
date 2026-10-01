import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import restore_hand_feasibility as implementation


def smooth(x):
    return dict(vectors=np.array([[x[1],0.,0.]]),caps=np.array([.1]),scales=np.ones(1),margins=np.ones(1),depths=np.array([.02-.01*x[0]]))


def exact(x):
    value=smooth(x);value['vectors'][0,0]=np.round(x[1],2);return value


def test_restoration_can_recover_a_quantized_feasible_improvement(monkeypatch):
    monkeypatch.setattr(implementation,'direction',lambda *args:(np.array([0.,-.1]),dict(status='Solved')))
    point,report=implementation.restore(exact,smooth,[0.,0.],[.5,.2],None,iterations=2,trust=.1)
    np.testing.assert_array_equal(point,[.5,.1])
    assert report['numerically_feasible'] and report['final']['minimum_margin']==0
    assert not report['accepted_for_publication'] and report['mesh_validation_required']


def test_feasibility_cannot_be_bought_by_losing_original_objective_improvement(monkeypatch):
    monkeypatch.setattr(implementation,'direction',lambda *args:(np.array([-.5,-.1]),dict(status='Solved')))
    point,report=implementation.restore(exact,smooth,[0.,0.],[.5,.2],None,iterations=1,trust=.5)
    assert point is None and not report['numerically_feasible']
    assert not report['history'][0]['trials'][0]['eligible']
    assert report['final']['witness_peak_m']<report['original']['witness_peak_m']


def test_no_violation_reduction_does_not_accept_solver_slack(monkeypatch):
    monkeypatch.setattr(implementation,'direction',lambda *args:(np.zeros(2),dict(status='Solved',proposal_slack=.1)))
    point,report=implementation.restore(exact,smooth,[0.,0.],[.5,.2],None)
    assert point is None and report['stop_reason']=='no_violation_reduction'
    assert len(report['history'])==1


def test_original_caps_cannot_be_changed_during_restoration(monkeypatch):
    cap=np.array([.1])
    def sample(x):
        value=smooth(x);value['caps']=cap;return value
    monkeypatch.setattr(implementation,'direction',lambda *args:(np.array([0.,-.01]),dict(status='Solved')))
    with pytest.raises(ValueError,match='remain fixed'):
        implementation.restore(sample,sample,[0.,0.],[.5,.2],None,checkpoint=lambda *args:cap.fill(.3))


def test_elastic_slack_relaxes_only_proposal_feasibility_not_objective_or_bounds():
    base=dict(vectors=np.array([[.2,0.,0.]]),caps=np.array([.1]),scales=np.ones(1),margins=np.array([-.03]),depths=np.array([.02]))
    model=dict(point=np.zeros(1),base=base,jacobian=dict(vectors=np.array([[[1.],[0.],[0.]]]),margins=np.array([[.1]]),depths=np.array([[1.]])))
    a,b,record=implementation.assemble(model,.1,.03)
    slack=b-a@np.array([0.,.1]);cone=slack[record['linear_rows']:]
    assert np.min(slack[:record['linear_rows']])>=0
    assert cone[0]==pytest.approx(np.linalg.norm(cone[1:]))
    for elastic in [0.,10.]:
        wrong=b-a@np.array([1.,elastic])
        assert wrong[3]<0  # Fixed collision-objective ceiling remains violated.
    assert (b-a@np.array([2.,10.]))[1]<0  # Control bounds also stay hard.


def test_affine_safe_objective_rows_may_be_omitted_without_changing_real_caps():
    base=dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.ones(1),depths=np.array([.001,.014]))
    model=dict(point=np.zeros(1),base=base,jacobian=dict(vectors=np.zeros((1,3,1)),margins=np.zeros((1,1)),depths=np.array([[.001],[.02]])))
    _,_,report=implementation.assemble(model,.1,.015)
    assert report['retained_depth_rows']==[1]
    for corner in [-.1,.1]:assert base['depths'][0]+model['jacobian']['depths'][0,0]*corner<.015


@pytest.mark.parametrize('options',[dict(iterations=0),dict(trust=0),dict(step=float('nan'))])
def test_invalid_search_budgets(options):
    with pytest.raises(ValueError):implementation.restore(exact,smooth,[0.,0.],[.5,.2],None,**options)
