"""Analytic curvature, bounded stencils and decoded continuation authority."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows,linearize
from test_native_scene_fit import prepare
from native_scene_fit import run,SceneProblem
from native_scene_resume import ResumeState
from strep import read,sha256


def curve(monkeypatch,*,point=.3):
    import native_scene_norms as norms
    queried=[]
    def worlds(x,*,quantized=True):
        queried.append((float(x[0]),quantized));return np.asarray(x).copy()
    def rows(problem,value,worlds=None):
        x=float(value[0]);return NormRows([[np.cos(x),np.sin(x),x**3]],[1.],[.5])
    monkeypatch.setattr(norms,'rows',rows)
    problem=SimpleNamespace(edits=SimpleNamespace(controls=lambda x:np.asarray(x,float)),
        worlds=worlds,lower=np.array([-1.]),upper=np.array([1.]))
    return problem,np.array([point]),queried


def test_symmetric_curve_derivative_reduces_one_sided_curvature_bias(monkeypatch):
    problem,x,queries=curve(monkeypatch);h=.05
    a,forward,old=linearize(problem,x,step=h,difference_source='continuous')
    b,central,new=linearize(problem,x,step=h,difference_source='continuous',difference_scheme='central')
    exact=np.array([-np.sin(x[0]),np.cos(x[0]),3*x[0]**2])
    df=forward.toarray().ravel();dc=central.toarray().ravel()
    assert np.linalg.norm(dc-exact)<np.linalg.norm(df-exact)/10
    np.testing.assert_allclose(dc[:2],exact[:2]*np.sin(h)/h,atol=2e-15,rtol=0)
    assert dc[2]==pytest.approx(exact[2]+h*h,abs=1e-15)
    np.testing.assert_array_equal(a.vectors,b.vectors);np.testing.assert_array_equal(a.caps,b.caps)
    assert new['central_difference_columns']==1 and new['column_proxy_evaluations']==2
    assert new['actual_difference_offsets']==[[h,-h]]
    assert old['one_sided_difference_columns']==1 and old['column_proxy_evaluations']==1
    assert all(not q for _,q in queries)


@pytest.mark.parametrize('point',[-1.,-.99,.99,1.])
def test_box_boundary_stencil_falls_toward_available_room(monkeypatch,point):
    problem,x,queries=curve(monkeypatch,point=point)
    _,jac,info=linearize(problem,x,step=.05,difference_source='continuous',difference_scheme='central')
    assert info['central_difference_columns']==0 and info['one_sided_difference_columns']==1
    assert len(info['actual_difference_offsets'][0])==1
    h=info['actual_difference_offsets'][0][0]
    assert np.sign(h)==-np.sign(point) and abs(h)==.05
    assert all(-1<=v<=1 for v,_ in queries) and np.isfinite(jac.data).all()


def test_decoded_anchor_preserves_rows_but_not_finite_difference_origin(monkeypatch):
    import native_scene_norms as norms
    problem,x,queries=curve(monkeypatch);original=norms.rows
    def shifted(problem,value,worlds=None):
        result=original(problem,value,worlds)
        if isinstance(worlds,str):result.vectors+=100.
        return result
    monkeypatch.setattr(norms,'rows',shifted)
    plain,jac,a=linearize(problem,x,step=.05,difference_source='continuous',difference_scheme='central')
    anchored,other,b=linearize(problem,x,step=.05,difference_source='continuous',difference_scheme='central',base_worlds='decoded')
    np.testing.assert_array_equal(jac.toarray(),other.toarray())
    np.testing.assert_array_equal(anchored.vectors,plain.vectors+100.)
    np.testing.assert_array_equal(anchored.caps,plain.caps)
    assert b['decoded_base_anchor'] and not a['decoded_base_anchor']


@pytest.mark.parametrize('fault',['schema','negative-sample-cap','negative-sample-nan','resource'])
def test_invalid_or_partial_symmetric_samples_do_not_drop_rows(monkeypatch,fault):
    import native_scene_norms as norms
    problem,x,queries=curve(monkeypatch);original=norms.rows
    def corrupted(problem,value,worlds=None):
        result=original(problem,value,worlds)
        if value[0]<x[0]:
            if fault=='negative-sample-cap':result.caps+=1.
            if fault=='negative-sample-nan':result.vectors[:]=float('nan')
        return result
    monkeypatch.setattr(norms,'rows',corrupted)
    with pytest.raises(ValueError):linearize(problem,x,step=.05,difference_source='continuous',
        difference_scheme='hidden-stencil' if fault=='schema' else 'central',maximum_elements=1 if fault=='resource' else 60_000_000)


def test_supplied_rotation_skin_uses_complete_unchanged_vector_populations(tmp_path):
    source,spec,c,p,permissions,scene,edits=prepare(tmp_path,rotation=True);problem=SceneProblem(scene,edits)
    x=problem.initial.copy();x.reshape(-1,3)[:,0]=.05
    base,jac,info=linearize(problem,x,step=.001,difference_source='continuous',difference_scheme='central')
    from native_scene_norms import rows
    epsilon=1e-6;plus=x.copy();minus=x.copy();plus[0]+=epsilon;minus[0]-=epsilon
    oracle=(rows(problem,plus,problem.worlds(plus,quantized=False)).vectors
        -rows(problem,minus,problem.worlds(minus,quantized=False)).vectors)/(2*epsilon)
    np.testing.assert_allclose(jac[:,0].toarray().ravel(),oracle.ravel(),atol=2e-6,rtol=2e-6)
    assert info['central_difference_columns']==problem.size and info['column_proxy_evaluations']==2*problem.size
    assert len(base.caps)==len(problem.model(x)) and sha256(source)==spec['actors']['A']['sha256']


def test_actual_central_fit_and_resume_preserve_original_caps_and_exports(tmp_path):
    source,spec,c,p,permissions,scene,edits=prepare(tmp_path)
    original=sha256(source);prior=tmp_path/'prior'
    a=run(c,permissions,prior,iterations=1,proposal_model='storage-vector',restoration_steps=3)
    out=tmp_path/'central';b=run(c,permissions,out,iterations=1,proposal_model='storage-vector',restoration_steps=3,
        vector_difference_scheme='central',resume_from=prior)
    assert sha256(source)==original and b['original_selected'] and not b['release_approved']
    assert sha256(out/'probes/start/A.glb')==sha256(prior/'probes/final/A.glb')
    assert read(out/'request.json')['vector_difference_scheme']==b['vector_difference_scheme']=='central'
    assert b['optimization']['difference_scheme']=='central'
    assert b['completed_primary_iterations']==len(a['optimization']['history'])+len(b['optimization']['history'])
    with np.load(prior/'source-rate-caps.npz') as before,np.load(out/'source-rate-caps.npz') as after:
        assert set(before.files)==set(after.files)
        for key in before.files:
            assert before[key].dtype==after[key].dtype;np.testing.assert_array_equal(before[key],after[key])
    for history in b['optimization']['history']:
        difference=history['differences'];assert difference['central_difference_columns']==edits.size
        assert difference['column_proxy_evaluations']==2*edits.size
        assert all(p['source_rows_pass'] and p['native_contact_rows_nonregressing'] for p in history['probes'] if p['accepted'])
    # The final decoded protected prefix remains the authority, not the stencil.
    resumed=ResumeState(out,sha256(c),sha256(permissions),edits)
    residual,_=SceneProblem(scene,edits).decoded(dict(A=out/'probes/final/A.glb'),resumed.controls)
    assert np.all(residual[:SceneProblem(scene,edits).protected_rows]<=0)


@pytest.mark.parametrize('mode,scheme',[('scalar','central'),('surface-vector','central'),('vector','auto'),('storage-vector',True)])
def test_invalid_fit_stencil_choice_rejects_before_creating_output(tmp_path,mode,scheme):
    _,_,c,_,p,_,_=prepare(tmp_path);out=tmp_path/'bad'
    with pytest.raises(ValueError):run(c,p,out,proposal_model=mode,vector_difference_scheme=scheme)
    assert not out.exists()
