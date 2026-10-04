"""Candidate-centered decoded restoration keeps the original acceptance rows."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_contact_norms import protect_rows
from native_scene_conic import optimize,direction


def reference_model():
    system=NormRows([[.09,0,0],[-.2,0,0]],[.1,.1],[1.,1.])
    jac=sparse.csc_matrix(np.array([[1.],[0],[0],[1.],[0],[0]]))
    return system,jac


def test_recentered_contact_protection_uses_original_decoded_reference():
    system,jac=reference_model();before=system.residual()[1:]
    reference=NormRows(system.vectors[1:],system.caps[1:],system.scales[1:])
    candidate=NormRows([[.1002,0,0],[-.23,0,0]],[.1,.1],[1.,1.])
    protected,derivative,record=protect_rows(candidate,jac,1,before,reference=reference)
    assert protected.caps[1]==.2 and protected.caps[2]==.1
    assert protected.residual()[1]>.0299  # Candidate worsening remains a failure.
    np.testing.assert_array_equal(candidate.caps,[.1,.1])
    np.testing.assert_array_equal(protected.vectors[1],protected.vectors[2])
    assert record['hard_rows']==2 and derivative.shape==(9,1)
    _,same,_=protect_rows(system,jac,1,before)
    explicit,other,_=protect_rows(system,jac,1,before,reference=reference)
    legacy,legacy_jac,_=protect_rows(system,jac,1,before)
    for key in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(explicit,key),getattr(legacy,key))
    np.testing.assert_array_equal(other.toarray(),legacy_jac.toarray())


@pytest.mark.parametrize('fault',['count','caps','scales','baseline','type'])
def test_changed_reference_is_rejected(fault):
    system,jac=reference_model();before=system.residual()[1:]
    ref=NormRows(system.vectors[1:].copy(),system.caps[1:].copy(),system.scales[1:].copy())
    if fault=='count':ref=system
    if fault=='caps':ref.caps[0]+=.001
    if fault=='scales':ref.scales[0]*=2
    if fault=='baseline':ref.vectors[0,0]-=.01
    if fault=='type':ref=object()
    with pytest.raises((ValueError,AssertionError)):protect_rows(system,jac,1,before,reference=ref)


@pytest.mark.parametrize('fault',['none','source','contact'])
def test_actual_conic_recenter_requires_decoded_source_and_original_contacts(monkeypatch,fault):
    import native_scene_conic as conic
    source_cap=.1;offset=.0003;calls=[]
    def actual(x,label):
        v=x[0];source=.09+v-v*v+(offset if v else 0.)
        g=np.array([source-source_cap,.2-v-.1])
        if '-recenter-' in label:
            if fault=='source':g[0]=.001
            if fault=='contact':g[1]=.11
        return g
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1),protected_rows=1,
        model=lambda x:actual(x,'model'))
    def anchor(x,label):calls.append((x.copy(),label));return actual(x,label)
    def linearize(problem,x,**kw):
        g=kw['base_worlds'];vectors=np.array([[.1+g[0],0,0],[-(.1+g[1]),0,0]])
        jac=sparse.csc_matrix(np.array([[1-2*x[0]],[0],[0],[1.],[0],[0]]))
        return NormRows(vectors,[.1,.1],[1.,1.]),jac,dict(test_continuous_derivative=True)
    monkeypatch.setattr(conic,'linearize',linearize)
    value,result=optimize(problem,actual,1,.02,protect_source_rows=True,protect_contact_rows=True,
        anchor_worlds=anchor,restoration_steps=2,restoration_model='recentered')
    history=result['history'][0];repairs=history['decoded_restorations']
    assert repairs and repairs[0]['model']=='recentered' and repairs[0]['anchor_label']=='1-0'
    assert calls[1][0][0]>0 and actual(calls[1][0],'1-0')[0]>0
    accepted=[p for p in history['probes'] if p['accepted']]
    if fault=='none':
        assert len(accepted)==1 and accepted[0]['kind']=='recentered-restoration'
        assert accepted[0]['source_rows_pass'] and accepted[0]['native_contact_rows_nonregressing']
        assert actual(value,'check')[0]<=0 and actual(value,'check')[1]<actual(np.zeros(1),'check')[1]
    else:
        assert not any(p['accepted'] for p in history['probes'] if p.get('kind')=='recentered-restoration')
    assert all(p['source_rows_pass'] and p['native_contact_rows_nonregressing'] for p in accepted)


def test_next_recenter_anchor_is_an_exported_lower_defect_not_a_new_contact_baseline(monkeypatch):
    import native_scene_conic as conic
    def actual(x,label):
        v=x[0];source=-.01 if not v else -.001 if v<=.080001 else .0001 if v<=.090001 else .0002
        return np.array([source,.2-v])
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1),protected_rows=1,
        model=lambda x:actual(x,'model'))
    anchors=[];original_caps=[]
    def anchor(x,label):anchors.append((float(x[0]),label));return actual(x,label)
    def model(problem,x,**kwargs):
        g=kwargs['base_worlds'];return NormRows([[.1+g[0],0,0],[-(.1+g[1]),0,0]],
            [.1,.1],[1.,1.]),sparse.csc_matrix([[1.],[0],[0],[1.],[0],[0]]),dict()
    monkeypatch.setattr(conic,'linearize',model)
    def proposed(system,jac,x,*args,**kwargs):
        original_caps.append(float(system.caps[1]));return np.array([.1 if x[0]==0 else -.01]),dict(status='test-direction')
    monkeypatch.setattr(conic,'direction',proposed)
    value,result=optimize(problem,actual,1,.02,protect_source_rows=True,protect_contact_rows=True,
        anchor_worlds=anchor,restoration_steps=2,restoration_model='recentered')
    assert value[0]==pytest.approx(.08)
    assert anchors[1]==(.1,'1-0') and anchors[2][0]==pytest.approx(.09)
    assert anchors[2][1]=='1-recenter-0-0' and original_caps==pytest.approx([.3,.3,.3])
    repairs=result['history'][0]['decoded_restorations']
    assert len(repairs)==2 and repairs[1]['anchor_label']=='1-recenter-0-0'
    assert not repairs[0]['probes'][0]['accepted'] and repairs[1]['probes'][0]['accepted']


@pytest.mark.parametrize('steps,anchor,protected',[(0,True,True),(True,True,True),(5,True,True),(1,False,True),(1,True,False)])
def test_invalid_optimizer_configuration_fails_before_evaluation(steps,anchor,protected):
    with pytest.raises(ValueError):optimize(object(),lambda *args:pytest.fail('Evaluation must not run'),1,.02,
        restoration_model='recentered',restoration_steps=steps,protect_source_rows=protected,
        anchor_worlds=(lambda *a:None) if anchor else None)


@pytest.mark.parametrize('mode,steps,model',[('scalar',1,'recentered'),('vector',1,'recentered'),
    ('surface-vector',1,'recentered'),('storage-vector',0,'recentered'),('storage-vector',1,'unknown')])
def test_invalid_fit_configuration_fails_before_output(tmp_path,mode,steps,model):
    from native_scene_fit import run
    output=tmp_path/'invalid'
    with pytest.raises(ValueError):run(tmp_path/'missing-c',tmp_path/'missing-p',output,
        proposal_model=mode,restoration_steps=steps,restoration_model=model)
    assert not output.exists()


def test_native_export_resume_keeps_original_caps_and_records_explicit_model(tmp_path):
    from test_native_scene_fit import prepare
    from native_scene_fit import run
    from strep import read,sha256
    _,_,c,_,p,_,_=prepare(tmp_path,rotation=True)
    prior=tmp_path/'prior';run(c,p,prior,iterations=1,proposal_model='storage-vector')
    current=tmp_path/'recentered';result=run(c,p,current,iterations=1,proposal_model='storage-vector',
        restoration_model='recentered',restoration_steps=1,resume_from=prior)
    assert result['restoration_model']==read(current/'request.json')['restoration_model']=='recentered'
    assert result['optimization']['restoration_model']=='recentered'
    assert sha256(prior/'probes/final/A.glb')==sha256(current/'probes/start/A.glb')
    with np.load(prior/'source-rate-caps.npz') as a,np.load(current/'source-rate-caps.npz') as b:
        assert a.files==b.files
        for key in a.files:assert a[key].dtype==b[key].dtype and np.array_equal(a[key],b[key])
