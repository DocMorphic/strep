"""Decoded defects tighten affine source caps without relaxing acceptance."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_scene_restore import tighten
from native_scene_conic import optimize


def model():
    system=NormRows([[.09,0,0],[-.2,0,0]],[.1,.1],[.1,.1])
    jac=np.zeros((2,3,1));jac[:,0,0]=1
    return system,jac


def test_measured_defect_changes_proposal_only_and_accumulates():
    system,jac=model();caps=system.caps.copy();vectors=system.vectors.copy()
    changed,reserve,info=tighten(system,jac,[.01],[.004,.7],1)
    np.testing.assert_array_equal(system.caps,caps);np.testing.assert_array_equal(system.vectors,vectors)
    assert reserve[0]==pytest.approx(.0008) and reserve[1]==0
    assert changed.caps[0]<caps[0] and changed.caps[1]==caps[1]
    assert info['original_caps_unchanged'] and info['contact_caps_unchanged']
    again,new,info=tighten(system,jac,[.01],[.002,.6],1,reserve)
    assert new[0]>reserve[0] and again.caps[0]<changed.caps[0]


@pytest.mark.parametrize('fault',['prefix-zero','prefix-bool','prefix-large','population','nan','negative','contact-reserve'])
def test_invalid_observations_and_reserves_reject(fault):
    system,jac=model();prefix=1;actual=[.004,.7];reserve=None
    if fault=='prefix-zero':prefix=0
    if fault=='prefix-bool':prefix=True
    if fault=='prefix-large':prefix=3
    if fault=='population':actual=[.004]
    if fault=='nan':actual=[float('nan'),.7]
    if fault=='negative':reserve=[-.1,0]
    if fault=='contact-reserve':reserve=[0,.1]
    with pytest.raises(ValueError):tighten(system,jac,[.01],actual,prefix,reserve)


def test_passing_source_rows_are_not_tightened_for_contact_failure():
    system,jac=model();actual=system.residual();actual[1]=5;changed,reserve,info=tighten(system,jac,[0],actual,1)
    np.testing.assert_array_equal(changed.caps,system.caps)
    assert np.count_nonzero(reserve)==0 and info['failed_protected_rows']==0


def test_passing_underpredicted_source_rows_also_receive_proposal_margin():
    system,jac=model();changed,reserve,info=tighten(system,jac,[0],[-.05,5],1)
    assert info['failed_protected_rows']==0 and info['underpredicted_protected_rows']==1
    assert reserve[0]>0 and reserve[1]==0 and changed.caps[0]<system.caps[0]


def test_restoration_accepts_only_redecoded_protected_step(monkeypatch):
    import native_scene_conic as conic
    system=NormRows([[0,0,0],[-.195,0,0]],[.1,.1],[1,1]);jac=np.zeros((2,3,1));jac[:,0,0]=1
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1),protected_rows=1,
        model=lambda x:system.residual(jac,x))
    monkeypatch.setattr(conic,'linearize',lambda *a,**k:(system,jac,dict(test_model=True)))
    evaluations={}
    def actual(x,label):
        g=np.array([x[0]+x[0]**2-.1,abs(x[0]-.195)-.1]);evaluations[label]=g;return g
    value,report=optimize(problem,actual,1,1.,protect_source_rows=True,restoration_steps=3)
    assert evaluations['1-0'][0]>0
    accepted=[p for p in report['history'][0]['probes'] if p['accepted']]
    assert len(accepted)==1 and accepted[0]['kind']=='decoded-restoration'
    assert accepted[0]['source_rows_pass'] and actual(value,'check')[0]<=0
    assert report['final_merit'][0]>0  # Still an incompatible contact request.


@pytest.mark.parametrize('mode,steps',[('scalar',1),('vector',1),('storage-vector',True),('storage-vector',-1),('storage-vector',5)])
def test_restoration_configuration_fails_before_outputs(tmp_path,mode,steps):
    from test_native_scene_fit import prepare
    from native_scene_fit import run
    _,_,contacts,_,permissions,_,_=prepare(tmp_path);output=tmp_path/'job'
    with pytest.raises(ValueError):run(contacts,permissions,output,proposal_model=mode,restoration_steps=steps)
    assert not output.exists()
