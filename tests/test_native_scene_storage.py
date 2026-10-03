"""Stored translation neighborhoods and unchanged decoded acceptance authority."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from native_scene_storage import fractions,line_data
from native_scene_fit import SceneProblem,run
from native_scene_norms import linearize,rows
from native_support_feasibility import merit
from strep import sha256
from native_scene_conic import direction
from native_scene_norms import NormRows


def test_neighbor_search_finds_serialized_rate_safe_triangle(tmp_path):
    source,_,_,_,_,scene,edits=prepare(tmp_path);problem=SceneProblem(scene,edits)
    delta=edits.initial.copy();delta.reshape(-1,3)[:,1]=np.array([.5,1,.5])*.002/.02
    candidates,info=fractions(edits,edits.initial,delta,maximum_cells=64)
    assert info['visited_cells']==64 and not info['reached_zero']
    assert all(0<=c['lower_fraction']<c['fraction']<c['upper_fraction']<=1 for c in candidates)
    assert all(b['upper_fraction']<=a['lower_fraction']+1e-12 for a,b in zip(candidates,candidates[1:]))
    initial=tmp_path/'ordinary.glb';edits.export('A',delta,initial)
    first,_=problem.decoded({'A':initial},delta);assert merit(first)[0]>0
    for index,c in enumerate(candidates):
        x=c['fraction']*delta;path=tmp_path/(str(index)+'.glb');edits.export('A',x,path)
        decoded,_=problem.decoded({'A':path},x)
        if merit(decoded)[0]==0:
            assert edits.audit('A',path,0)['passed'];break
    else:pytest.fail('No feasible serialized candidate in the declared neighborhood')
    assert sha256(source)==scene.inputs[str(source.resolve())]


def test_continuous_differences_keep_actual_base_and_ordered_caps(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path);problem=SceneProblem(scene,edits)
    x=edits.initial.copy();x.reshape(-1,3)[:,1]=.0123
    actual=rows(problem,x);base,jac,info=linearize(problem,x,step=.001,difference_source='continuous')
    np.testing.assert_array_equal(base.vectors,actual.vectors)
    np.testing.assert_allclose(base.residual(),problem.model(x),atol=1e-9,rtol=1e-12)
    smooth=rows(problem,x,problem.worlds(x,quantized=False))
    h=info['actual_steps'][1];other=x.copy();other[1]+=h;changed=rows(problem,other,problem.worlds(other,quantized=False))
    np.testing.assert_allclose(jac[:,1].toarray().ravel(),((changed.vectors-smooth.vectors)/h).ravel(),atol=1e-10)
    assert info['difference_source']=='continuous'
    assert len(problem.model(x))>problem.protected_rows>0


@pytest.mark.parametrize('fault',['rotation','zero','budget','bool','fraction','negative'])
def test_storage_unavailable_and_bad_configuration(tmp_path,fault):
    _,_,_,_,_,_,edits=prepare(tmp_path,rotation=fault=='rotation')
    d=edits.initial.copy();d[1]=.01
    options={}
    if fault=='zero':d[:]=0
    if fault=='budget':options['maximum_cells']=513
    if fault=='bool':options['maximum_cells']=True
    if fault=='fraction':options['start_fraction']=0
    if fault=='negative':options['start_fraction']=-1
    with pytest.raises(ValueError):fractions(edits,edits.initial,d,**options)


def test_negative_direction_and_nonzero_origin_match_actual_stored_values(tmp_path):
    _,_,_,_,_,_,edits=prepare(tmp_path);x=edits.initial.copy();x[1::3]=.05
    d=-x*.5;cells,_=fractions(edits,x,d,maximum_cells=8)
    base,slope=line_data(edits,x,d)
    for c in cells:
        lo=base+slope*((3*c['lower_fraction']+c['upper_fraction'])/4)
        hi=base+slope*((c['lower_fraction']+3*c['upper_fraction'])/4)
        np.testing.assert_array_equal(lo.astype(np.float32),hi.astype(np.float32))


@pytest.mark.parametrize('mode,cells',[('vector',2),('scalar',2),('storage-vector',False),('storage-vector',0)])
def test_cli_storage_configuration_rejected_before_outputs(tmp_path,mode,cells):
    _,_,contacts,_,permissions,_,_=prepare(tmp_path)
    output=tmp_path/'job'
    with pytest.raises(ValueError):run(contacts,permissions,output,proposal_model=mode,storage_cells=cells)
    assert not output.exists()


def test_hard_source_rows_cannot_trade_rate_violation_for_contact_gain():
    # x <= .1 is a protected motion bound; contact wants x >= .9.
    system=NormRows([[0,0,0],[-1,0,0]],[.1,.1],[1,1])
    jac=np.zeros((2,3,1));jac[:,0,0]=1
    soft,_=direction(system,jac,[0],[-1],[1],1.)
    hard,info=direction(system,jac,[0],[-1],[1],1.,hard_rows=1)
    assert soft[0]>.4 and hard[0]<=.10000001
    assert info['protected_norm_rows']==1
    fixed=NormRows([[.2,0,0],[-1,0,0]],[.1,.1],[1,1]);jac[0]=0
    step,info=direction(fixed,jac,[0],[-1],[1],1.,hard_rows=1)
    assert step is None and info['status']=='FixedProtectedConflict'


def test_storage_solver_runs_serialized_checks_and_preserves_original(tmp_path):
    source,_,contacts,_,permissions,scene,_=prepare(tmp_path)
    output=tmp_path/'job';r=run(contacts,permissions,output,proposal_model='storage-vector',iterations=8,storage_cells=64)
    assert r['original_selected'] and not r['release_approved']
    assert r['optimization']['protect_source_rows'] and r['optimization']['difference_source']=='continuous'
    assert r['storage_cells']==64 and r['optimization']['history']
    for h in r['optimization']['history']:
        assert all(p['source_rows_pass'] for p in h['probes'] if p['accepted'])
    # Native success is checked separately against decoded scene contacts; it
    # cannot be inferred merely from a conic status or a selected control step.
    from strep import read
    report=read(output/'contact-audit/result.json')
    assert r['native_constraints_pass']==(r['optimization']['final_merit'][0]==0 and report['passed'] and all(a['passed'] for a in r['edits'].values()))
    assert sha256(source)==scene.inputs[str(source.resolve())]
