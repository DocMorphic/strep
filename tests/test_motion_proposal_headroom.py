import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import motion_proposal_headroom as implementation


def fixture():
    base=dict(vectors=np.array([[.8,0.,0.],[.5,0.,0.]]),caps=np.ones(2),scales=np.ones(2),margins=np.ones(2),depths=np.ones(1))
    row=dict(index=0,cap=1.,scale=1.,curvature_vector_error=.01,serialization_change_error=.02,norms=dict(serialized=1.1))
    return dict(base=base,point=np.zeros(1)),dict(method='motion_proposal_error_decomposition_v1',trials=[dict(rows=[row])])


def test_proposal_tightening_does_not_change_real_caps():
    model,diagnostic=fixture();proposal,record=implementation.tighten(model,diagnostic)
    np.testing.assert_array_equal(model['base']['caps'],[1.,1.])
    np.testing.assert_allclose(proposal['base']['caps'],[1.-.06-1e-9,1.])
    assert not record['certified_error_bound'] and not record['acceptance_caps_changed']


def test_wrong_reference_cap_rejected():
    model,diagnostic=fixture();diagnostic['trials'][0]['rows'][0]['cap']=2.
    with pytest.raises(ValueError,match='original motion'):implementation.tighten(model,diagnostic)


def test_duplicate_motion_rows_rejected():
    model,diagnostic=fixture();diagnostic['trials'][0]['rows']*=2
    with pytest.raises(ValueError,match='Unique'):implementation.tighten(model,diagnostic)


def test_headroom_larger_than_cap_rejected():
    model,diagnostic=fixture();diagnostic['trials'][0]['rows'][0]['serialization_change_error']=1.
    with pytest.raises(ValueError,match='exceeds'):implementation.tighten(model,diagnostic)


def test_exact_replay_keeps_untightened_caps(monkeypatch):
    model,diagnostic=fixture()
    def exact(x):return dict(model['base'],depths=np.array([1.-.1*x[0]]))
    model['point']=np.array([.5]);model['base']=exact(model['point'])
    def direction(proposal,*args):
        assert proposal['base']['caps'][0]<1.
        return np.array([.1]),dict(status='test')
    def scan(fn,*args,**kwargs):
        np.testing.assert_array_equal(fn([.6])['caps'],[1.,1.])
        return None,dict(final_point=[.5],quality_approved=False)
    monkeypatch.setattr(implementation,'direction',direction);monkeypatch.setattr(implementation,'scan',scan)
    _,report=implementation.solve(exact,[0.],[.5],model,diagnostic,None,witness_start=0,witness_count=1,witness_reserve=[0.])
    assert not report['quality_approved']
