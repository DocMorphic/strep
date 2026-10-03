"""Point/held-clock repair cannot trade individual failures for aggregate gain."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows,linearize,rows
import native_scene_conic as conic
from test_native_scene_fit import prepare


def toy(monkeypatch,second=-.4):
    system=NormRows([[0.,0,0],[1.,0,0],[second,0,0]],[1.,.1,.1],[1.,1.,1.])
    jac=np.zeros((3,3,1));jac[1:,0,0]=-1.
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1),protected_rows=1,
        model=lambda x:system.residual(jac,x))
    monkeypatch.setattr(conic,'linearize',lambda *a,**k:(system,sparse.csc_matrix(jac.reshape(9,1)),{}))
    return system,jac,problem


def test_individual_failed_rows_block_a_larger_aggregate_improvement(monkeypatch):
    system,jac,problem=toy(monkeypatch)
    actual=lambda x,label:system.residual(jac,x)
    unguarded,old=conic.optimize(problem,actual,1,1.,protect_source_rows=True)
    assert unguarded[0]>.1 and actual(unguarded,'check')[2]>actual([0.],'start')[2]
    guarded,new=conic.optimize(problem,actual,1,1.,protect_source_rows=True,protect_contact_rows=True)
    np.testing.assert_array_equal(guarded,[0.])
    assert not any(p['accepted'] for p in new['history'][0]['probes'])
    assert new['native_contact_rows_individually_protected']
    assert new['history'][0]['conic_step']['protected_norm_rows']==3


def test_passing_contact_stays_passing_while_failed_contact_improves(monkeypatch):
    system,jac,problem=toy(monkeypatch,second=-.05)
    actual=lambda x,label:system.residual(jac,x)
    value,report=conic.optimize(problem,actual,1,1.,protect_source_rows=True,protect_contact_rows=True)
    after=actual(value,'check');before=actual([0.],'start')
    assert value[0]>.01 and after[1]<before[1] and after[2]<=0
    retained=[p for p in report['history'][0]['probes'] if p['accepted']]
    assert len(retained)==1 and retained[0]['native_contact_rows_nonregressing']


def test_decoded_contact_defect_triggers_restoration_even_when_source_passes(monkeypatch):
    _,_,problem=toy(monkeypatch,second=-.05);observations={}
    def actual(x,label):
        g=np.array([-1.,.9-x[0],x[0]+x[0]**2-.05]);observations[label]=g;return g
    value,report=conic.optimize(problem,actual,1,1.,protect_source_rows=True,protect_contact_rows=True,restoration_steps=3)
    first=report['history'][0]['probes'][0]
    assert first['source_rows_pass'] and not first['native_contact_rows_nonregressing'] and not first['accepted']
    retained=[p for p in report['history'][0]['probes'] if p['accepted']]
    assert len(retained)==1 and retained[0]['kind']=='decoded-restoration'
    assert retained[0]['source_rows_pass'] and retained[0]['native_contact_rows_nonregressing']
    assert actual(value,'check')[2]<=0 and actual(value,'check')[1]<.9


@pytest.mark.parametrize('guard,source,anchor',[(True,False,None),(1,True,None),(False,False,3)])
def test_invalid_guard_configuration_rejects_before_evaluation(guard,source,anchor):
    def unavailable(*args):raise AssertionError('Must reject before outputs')
    with pytest.raises(ValueError):conic.optimize(None,unavailable,1,1.,protect_source_rows=source,protect_contact_rows=guard,anchor_worlds=anchor)


def test_failed_source_is_not_recapped_to_enable_contact_repair(monkeypatch):
    _,_,problem=toy(monkeypatch)
    # Both proxy and decoded observations agree on this unavailable source state.
    failed=NormRows([[2.,0,0],[1.,0,0],[-.4,0,0]],[1.,.1,.1],[1.,1.,1.]);jac=np.zeros((3,3,1))
    monkeypatch.setattr(conic,'linearize',lambda *a,**k:(failed,jac,{}));problem.model=lambda x:failed.residual()
    with pytest.raises(ValueError,match='source conditions must pass'):
        conic.optimize(problem,lambda *args:failed.residual(),1,1.,protect_source_rows=True,protect_contact_rows=True)


@pytest.mark.parametrize('difference_source',['stored','continuous'])
def test_decoded_anchor_changes_only_base_vectors_not_caps_or_proxy_derivatives(tmp_path,difference_source):
    from native_scene_fit import SceneProblem
    _,_,_,_,_,scene,edits=prepare(tmp_path);problem=SceneProblem(scene,edits);value=problem.initial
    original,jac,_=linearize(problem,value,step=.001,difference_source=difference_source)
    decoded=problem.worlds(value);decoded['A'][:,:,0,3]+=.000123
    anchored,other,report=linearize(problem,value,step=.001,difference_source=difference_source,base_worlds=decoded)
    np.testing.assert_array_equal(original.caps,anchored.caps);np.testing.assert_array_equal(original.scales,anchored.scales)
    np.testing.assert_array_equal(jac.toarray(),other.toarray())
    np.testing.assert_allclose(anchored.residual(),problem.constraints(value,decoded),atol=1e-10,rtol=1e-12)
    assert not np.array_equal(original.vectors,anchored.vectors) and report['decoded_base_anchor']


def test_anchor_receives_retained_export_label(monkeypatch):
    system,jac,problem=toy(monkeypatch,second=-.05);calls=[]
    def anchor(x,label):calls.append((x.copy(),label));return {'decoded':'sentinel'}
    def base(p,x,**options):
        assert options['base_worlds']=={'decoded':'sentinel'}
        return NormRows(system.vectors+(jac.reshape(9,1)@x).reshape(3,3),system.caps,system.scales),sparse.csc_matrix(jac.reshape(9,1)),{}
    monkeypatch.setattr(conic,'linearize',base)
    conic.optimize(problem,lambda x,label:system.residual(jac,x),2,1.,protect_source_rows=True,protect_contact_rows=True,anchor_worlds=anchor)
    assert calls[0][1]=='start' and len(calls)==2 and calls[1][1].startswith('1-')
    assert calls[1][0][0]>.01
