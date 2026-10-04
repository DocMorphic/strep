"""Actual quaternion-key neighborhoods and complete decoded acceptance guards."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from native_scene_edit import SceneEdits
from native_scene_serialized_ray import probe_fractions
from native_scene_norms import NormRows
from native_scene_conic import optimize
from native_scene_fit import run
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import sha256


def signature(edits,x):
    return b''.join(np.asarray(edits.values(n,x)[e['node'],e['path']],np.float32).tobytes()
        for n,a in edits.actors.items() for e in a['tracks'])


@pytest.mark.parametrize('rotation,policy',[(False,'unit'),(True,'unit'),(True,'source-scale')])
def test_measured_ray_states_match_full_actual_glb_keys(tmp_path,rotation,policy):
    source,spec,c,p,permissions,scene,old=prepare(tmp_path,rotation=rotation)
    edits=SceneEdits(p,scene,sha256(c),rotation_storage_policy=policy)
    x=edits.initial.copy();x[1::3]=.02;delta=edits.initial.copy();delta[::3]=.03;delta[2::3]=-.01
    probes,info=probe_fractions(edits,x,delta,maximum_probes=8,start_fraction=.25)
    assert len(probes)==8 and not info['interval_certified'] and not info['exhaustive']
    assert len(info['complete_track_population'])==1 and info['signature_queries']<=2+108*8
    for i,probe in enumerate(probes):
        f=probe['fraction'];assert 0<=probe['different_lower_probe']<f<=probe['matched_upper_probe']<=.25
        value=x+f*delta;stored=signature(edits,value)
        assert stored==signature(edits,x+probe['matched_lower_probe']*delta)
        assert stored==signature(edits,x+probe['matched_upper_probe']*delta)
        assert stored!=signature(edits,x+probe['different_lower_probe']*delta)
        path=tmp_path/(str(i)+'.glb');edits.export('A',value,path)
        reader=NativeSupportSampler(RigAsset.load(path).document,RigAsset.load(path).binary,0)
        expected=edits.values('A',value)
        for node,channel,clock,values,mode in reader.channels:
            if (node,channel) in expected:np.testing.assert_array_equal(values,expected[node,channel].astype(np.float32))
        assert edits.audit('A',path,0)['passed']
    assert sha256(source)==spec['actors']['A']['sha256']


@pytest.mark.parametrize('fault',['zero-fraction','negative-fraction','bool-fraction','budget','bool-budget','origin-box','endpoint-box','nan'])
def test_invalid_ray_inputs_do_not_query_outside_boxes(tmp_path,fault):
    _,_,_,_,_,_,edits=prepare(tmp_path,rotation=True)
    x=edits.initial.copy();delta=x.copy();delta[0]=.03;args={}
    if fault=='zero-fraction':args['start_fraction']=0
    if fault=='negative-fraction':args['start_fraction']=-1
    if fault=='bool-fraction':args['start_fraction']=True
    if fault=='budget':args['maximum_probes']=513
    if fault=='bool-budget':args['maximum_probes']=True
    if fault=='origin-box':x[0]=2.
    if fault=='endpoint-box':delta[0]=2.
    if fault=='nan':delta[0]=float('nan')
    with pytest.raises(ValueError):probe_fractions(edits,x,delta,**args)


def test_unchanged_direction_reports_original_keys_without_inventing_probes(tmp_path):
    _,_,_,_,_,_,edits=prepare(tmp_path,rotation=True)
    probes,info=probe_fractions(edits,edits.initial,edits.initial)
    assert probes==[] and info['reached_original_keys'] and info['signature_queries']==2


@pytest.mark.parametrize('fault',['nan','population'])
def test_changed_or_nonfinite_key_population_rejects(tmp_path,monkeypatch,fault):
    _,_,_,_,_,_,edits=prepare(tmp_path,rotation=True);original=edits.values;count=0
    def changed(*args,**kwargs):
        nonlocal count
        count+=1;v=original(*args,**kwargs);key=next(iter(v))
        if count>1:
            if fault=='nan':v[key][0,0]=float('nan')
            else:v[key]=v[key][:-1]
        return v
    monkeypatch.setattr(edits,'values',changed);delta=edits.initial.copy();delta[0]=.03
    with pytest.raises(ValueError):probe_fractions(edits,edits.initial,delta)


@pytest.mark.parametrize('fault',['none','source','contact','restoration-anchor'])
def test_ray_candidates_still_obey_all_decoded_source_and_contact_rows(monkeypatch,fault):
    import native_scene_conic as conic
    import native_scene_serialized_ray as ray
    system=NormRows([[.09,0,0],[-.2,0,0]],[.1,.1],[1.,1.]);jac=np.zeros((2,3,1));jac[1,0,0]=1.
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1),protected_rows=1,edits=object(),
        model=lambda x:system.residual(jac,x),worlds=lambda x,**k:x,
        constraints=lambda x,w:system.residual(jac,x))
    monkeypatch.setattr(conic,'linearize',lambda *a,**k:(system,sparse.csc_matrix(jac.reshape(6,1)),dict()))
    directions=0
    def direction(*args,**kwargs):
        nonlocal directions
        directions+=1;return np.array([.02 if directions>1 else .01]),dict()
    monkeypatch.setattr(conic,'direction',direction)
    calls=[]
    def fractions(edits,origin,delta,**kwargs):
        calls.append(kwargs);assert delta[0]==.01 and kwargs['start_fraction']==1.
        return [dict(fraction=.8,matched_lower_probe=.799,matched_upper_probe=.801,different_lower_probe=.798)],dict(visited_probes=1)
    monkeypatch.setattr(ray,'probe_fractions',fractions)
    def actual(x,label):
        g=problem.model(x)
        if x[0]>.009 or fault=='source' and x[0]>0:g[0]=1e-6
        if fault=='contact' and '-ray-' in label:g[1]=.2
        return g
    value,result=optimize(problem,actual,1,.02,protect_source_rows=True,protect_contact_rows=True,
        serialized_ray_probes=4,restoration_steps=1 if fault=='restoration-anchor' else 0)
    assert len(calls)==1
    records=[p for p in result['history'][0]['probes'] if p.get('kind')=='serialized-key-ray']
    assert len(records)==1
    if fault in ('none','restoration-anchor'):
        assert value[0]==.008 and records[0]['accepted'] and records[0]['source_rows_pass'] and records[0]['native_contact_rows_nonregressing']
    else:
        assert not records[0]['accepted']
    assert result['history'][0]['serialized_ray']['anchor_label']=='1-0'


@pytest.mark.parametrize('mode,budget',[('scalar',1),('vector',1),('surface-vector',1),('storage-vector',True),('storage-vector',-1),('storage-vector',513)])
def test_invalid_fit_ray_configuration_rejects_before_output(tmp_path,mode,budget):
    _,_,c,_,p,_,_=prepare(tmp_path);out=tmp_path/'invalid'
    with pytest.raises(ValueError):run(c,p,out,proposal_model=mode,serialized_ray_probes=budget)
    assert not out.exists()
