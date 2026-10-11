"""Candidate-centered surface repairs keep decoded acceptance and original bounds."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_surface_model as surface
from native_scene_norms import NormRows
from test_native_surface_model import report


@pytest.mark.parametrize('fault',['none','native','mesh','contact','caps','scales'])
def test_actual_conic_recenter_uses_decoded_anchor_and_original_acceptance(monkeypatch,fault):
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1))
    anchors=[];guards=[]
    def evaluate(x,label):
        v=float(x[0]);native=.09+v-v*v+(.0003 if v else 0.)-.1
        contact=.1-v;depth=2.-v
        if '-recenter-' in label:
            if fault=='native':native=.001
            if fault=='mesh':depth=2.1
            if fault=='contact':contact=.11
        return dict(native=np.array([native]),worlds=(v,contact),geometry=report(depth=depth),
            scene=None,policy=None,digest=None,surface_contact=dict(surface_contacts_pass=False))
    def model(problem,x,*a,**kw):
        anchors.append(float(x[0]));world=kw['decoded_worlds'];v,contact=world
        native=evaluate(x,'anchor')['native'][0]
        cap=.1;scale=1.
        if v and fault=='caps':cap=.11
        if v and fault=='scales':scale=2.
        system=NormRows([[.1+native,0,0],[-(.1+contact),0,0]],[cap,.1],[scale,1.])
        jac=sparse.csc_matrix([[1-2*v],[0],[0],[1.],[0],[0]])
        return system,jac,None,{}
    monkeypatch.setattr(surface,'model',model)
    contact_model=SimpleNamespace(residual=lambda world:np.array([world[1]]))
    import native_contact_norms
    original=native_contact_norms.protect_rows
    def protect(system,jac,hard,before,**kw):
        result=original(system,jac,hard,before,**kw);guards.append(result[0].caps[hard]);return result
    monkeypatch.setattr(native_contact_norms,'protect_rows',protect)
    if fault in ('caps','scales'):
        with pytest.raises(ValueError,match='original native caps/scales'):
            surface.optimize(problem,evaluate,iterations=1,restoration_steps=2,
                restoration_model='recentered',contact_model=contact_model)
        return
    value,result=surface.optimize(problem,evaluate,iterations=1,restoration_steps=2,
        restoration_model='recentered',contact_model=contact_model)
    history=result['history'][0];repairs=history['restoration_attempts']
    assert repairs and repairs[0]['anchor_label']=='1-0' and anchors[1]>0
    assert evaluate(np.array([anchors[1]]),'anchor')['native'][0]>0
    assert guards==pytest.approx([.2]*len(guards))
    accepted=[p for p in history['probes'] if p['accepted']]
    if fault=='none':
        assert len(accepted)==1 and accepted[0]['kind']=='recentered-restoration'
        assert evaluate(value,'check')['native'][0]<=0 and value[0]>0
    else:
        assert not any(p['accepted'] for p in history['probes'] if p.get('kind')=='recentered-restoration')
    assert all(p['native_pass'] and p['contact_rows_nonregressing'] for p in accepted)
    assert not result['quality_approved'] and not result['release_approved']


def test_rejected_lower_defect_anchor_never_becomes_a_new_acceptance_baseline(monkeypatch):
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1));anchors=[]
    def evaluate(x,label):
        v=x[0];native=-.01 if not v else -.001 if v<=.080001 else .0001 if v<=.090001 else .0002
        return dict(native=np.array([native]),worlds=None,geometry=report(depth=2.-v),scene=None,policy=None,digest=None)
    def model(problem,x,*a,**kw):
        anchors.append(float(x[0]));return NormRows([[.1+evaluate(x,'model')['native'][0],0,0]],[.1],[1.]),sparse.csc_matrix([[1.],[0],[0]]),None,{}
    monkeypatch.setattr(surface,'model',model)
    monkeypatch.setattr(surface,'direction',lambda rows,jac,x,*a,**kw:(np.array([.1 if not x[0] else -.01]),dict(status='test')))
    value,result=surface.optimize(problem,evaluate,iterations=1,restoration_steps=2,restoration_model='recentered')
    assert value[0]==pytest.approx(.08) and anchors==pytest.approx([0.,.1,.09])
    repairs=result['history'][0]['restoration_attempts'];assert len(repairs)==2
    assert repairs[1]['anchor_label']=='1-recenter-0-0'
    assert not repairs[0]['probes'][0]['accepted'] and repairs[1]['probes'][0]['accepted']


def test_recentered_witness_rebuild_keeps_the_accepted_geometry_bound(monkeypatch):
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1));guard_caps=[]
    gaps={0:-.01,1:-.011,2:-.009}
    def evaluate(x,label):
        state=0 if label=='start' else 2 if '-recenter-' in label else 1
        return dict(native=np.array([.1 if state==1 else -1.]),worlds=state,
            geometry=report(depth={0:2.,1:2.2,2:1.8}[state]),scene=None,policy=None,digest=None)
    def model(problem,x,*a,**kw):
        state=kw['decoded_worlds'];rows=NormRows([[1.1 if state==1 else 0.,0,0],[1.-gaps[state],0,0]],
            [1.,.9995],[1.,.005])
        witness=SimpleNamespace(rows=[{}],gaps=lambda world:np.array([gaps[world]]))
        return rows,sparse.csc_matrix((6,1)),witness,dict(conversion=dict(offset_m=[1.]))
    monkeypatch.setattr(surface,'model',model);monkeypatch.setattr(surface,'surface_points',lambda p,w:w)
    def direction(rows,jac,x,*a,**kw):
        assert kw['hard_rows']==2;guard_caps.append(rows.caps[1])
        if x[0]:assert rows.residual()[1]>.19  # Worsening remains a protected defect.
        return np.array([-.005 if x[0] else .01]),dict(status='test')
    monkeypatch.setattr(surface,'direction',direction)
    value,result=surface.optimize(problem,evaluate,iterations=1,restoration_steps=1,restoration_model='recentered')
    np.testing.assert_allclose(guard_caps,[1.01,1.01],atol=1e-14,rtol=0)
    assert value[0]==pytest.approx(.005)
    repair=result['history'][0]['restoration_attempts'][0]
    assert repair['model_identity']['geometry_protection']['original_reference_bound_used']
    assert repair['probes'][0]['accepted']


@pytest.mark.parametrize('options',[dict(restoration_model='unknown'),dict(restoration_model='recentered',restoration_steps=0)])
def test_invalid_recenter_configuration_rejects_before_evaluation(options):
    with pytest.raises(ValueError):surface.optimize(None,lambda *a:pytest.fail('Must not evaluate'),**options)
