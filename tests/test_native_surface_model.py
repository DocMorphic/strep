"""Original caps, affine integration, and complete decoded acceptance authority."""
from pathlib import Path
import sys
import copy
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_surface_model as surface
from native_scene_fit import SceneProblem
from native_scene_edit import SceneEdits
from native_scene_contacts import SceneContacts
from native_scene_norms import NormRows
from native_scene_conic import direction
from native_surface_lift import lift
from test_native_scene_fit import prepare
from test_native_partner_surface_rows import scene_fixture
from strep import save,sha256,read


def test_extra_geometry_clocks_keep_original_caps_and_constraint_order(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path);problem=SceneProblem(scene,edits)
    original=[v.copy() for v in problem.caps['A'].caps];old=problem.model(problem.initial).copy()
    surface.include_times(problem,[.312345,.789123])
    assert .312345 in problem.times
    for a,b in zip(original,problem.caps['A'].caps):np.testing.assert_array_equal(a,b)
    np.testing.assert_array_equal(problem.model(problem.initial),old)
    with pytest.raises(ValueError):surface.include_times(problem,[float('nan')])
    with pytest.raises(ValueError):surface.include_times(problem,[3.])


def test_full_surface_proxy_combines_original_norms_and_all_witnesses(tmp_path):
    scene,policy,digest=scene_fixture(tmp_path)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)))
    edits=SceneEdits(permissions,scene,digest);problem=SceneProblem(scene,edits);surface.include_times(problem,[0.,1.,2.])
    system,jac,witnesses,report=surface.model(problem,problem.initial,scene,policy,digest,.02)
    hard=len(problem.model(problem.initial))
    np.testing.assert_allclose(system.residual()[:hard],problem.model(problem.initial),atol=1e-9)
    assert len(witnesses.rows)==report['surface_rows'] and len(system.caps)==hard+len(witnesses.rows)
    np.testing.assert_allclose(system.residual()[hard:],(.0005-witnesses.gaps())/.005,atol=1e-10)
    assert jac.shape==(3*len(system.caps),3)
    points=surface.surface_points(problem,problem.worlds(problem.initial))
    np.testing.assert_allclose(points('A',1.),scene.actor_points('A',np.arange(8),[1.])[0],atol=2e-12)
    with pytest.raises(ValueError):points('A',.7654321)


def test_scalar_surface_cones_can_move_without_relaxing_original_cap():
    original=NormRows([[0.,0,0]],[.01],[.01]);derivative=sparse.csr_matrix([[1.],[0.],[0.]])
    extra,j,_=lift([-.005],[[1.]],[0.],[-1.],[1.],.02)
    combined=NormRows(np.r_[original.vectors,extra.vectors],np.r_[original.caps,extra.caps],np.r_[original.scales,extra.scales])
    jac=sparse.vstack([derivative,j]);delta,info=direction(combined,jac,np.zeros(1),-np.ones(1),np.ones(1),.02,hard_rows=1)
    assert delta is not None and delta[0]>.0054 and abs(delta[0])<=.01+1e-9
    assert info['protected_norm_rows']==1
    assert combined.residual(jac,delta)[0]<=1e-7


@pytest.mark.parametrize('changed_caps',[False,True])
def test_decoded_anchor_replaces_proxy_vectors_without_recapping(monkeypatch,changed_caps):
    original=NormRows([[0.,0,0]],[1.],[1.]);anchored=NormRows([[.1,0,0]],[2. if changed_caps else 1.],[1.])
    jac=sparse.csr_matrix([[1.],[0.],[0.]])
    monkeypatch.setattr(surface,'linearize',lambda *a,**kw:(original,jac,{}))
    monkeypatch.setattr(surface,'native_rows',lambda *a:anchored)
    monkeypatch.setattr(surface,'build',lambda *a,**kw:SimpleNamespace(rows=[]))
    problem=SimpleNamespace(edits=SimpleNamespace(controls=lambda x:np.asarray(x)))
    if changed_caps:
        with pytest.raises(ValueError,match='caps'):surface.model(problem,[0.],None,None,None,.02,decoded_worlds={})
    else:
        result,derivative,_,_=surface.model(problem,[0.],None,None,None,.02,decoded_worlds={})
        np.testing.assert_array_equal(result.vectors,anchored.vectors)
        np.testing.assert_array_equal(result.caps,original.caps)
        assert derivative is jac and result.residual()[0]==pytest.approx(-.9)


def report(depth=2.,records=10,inside=5):
    return dict(limits=dict(penetration_m=.005),sampled_conditions_pass=False,samples=[dict(actor_objects=[],degenerate_faces=dict(A=[],B=[]),world_planes=[],actor_pairs=[dict(passed=False,surface=dict(records=[{}]*records,degenerate_faces=[[],[]]),vertex_containment=[dict(available=True,max_depth_m=depth*.005,vertices_over_tolerance=inside)])])])


def test_complete_geometry_score_never_exchanges_depth_regression_for_fewer_crossings():
    start=surface.geometry_score(report());assert start.tolist()==[2.,10.,5.,1.]
    assert not surface.improved(start,surface.geometry_score(report(depth=2.1,records=0,inside=0)))
    assert surface.improved(start,surface.geometry_score(report(depth=1.9)))
    assert surface.improved(start,surface.geometry_score(report(records=9)))
    bad=report();bad['samples'][0]['actor_pairs'][0]['vertex_containment'][0]['available']=False
    with pytest.raises(ValueError):surface.geometry_score(bad)
    bad=report();bad['samples'][0]['degenerate_faces']['A']=[0]
    with pytest.raises(ValueError):surface.geometry_score(bad)


@pytest.mark.parametrize('unsafe',[True,False])
def test_actual_native_and_full_geometry_both_decide_acceptance(monkeypatch,unsafe):
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1))
    system=NormRows([[0.,0,0]],[1.],[1.]);jac=sparse.csr_matrix((3,1))
    monkeypatch.setattr(surface,'model',lambda *a,**kw:(system,jac,None,{}))
    calls=[]
    def step(*a,**kw):
        assert kw['hard_rows']==1;return np.array([.01]),dict(status='Solved')
    monkeypatch.setattr(surface,'direction',step)
    def evaluate(x,label):
        calls.append(label);initial=label=='start'
        return dict(native=np.array([-1. if initial or not unsafe else .01]),geometry=report(depth=2. if initial else 1.),scene=None,policy=None,digest=None,worlds=None)
    value,result=surface.optimize(problem,evaluate,iterations=1,restoration_steps=0)
    if unsafe:
        np.testing.assert_array_equal(value,[0.]);assert len(calls)==11
        assert not any(p['accepted'] for p in result['history'][0]['probes'])
    else:
        np.testing.assert_allclose(value,[.01]);assert len(calls)==2
        assert result['history'][0]['probes'][0]['accepted']
    assert not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('bad',[dict(iterations=True),dict(trust=.1),dict(step=0.),dict(restoration_steps=5)])
def test_invalid_settings_reject_before_evaluation(bad):
    with pytest.raises(ValueError):surface.optimize(None,lambda *a:pytest.fail('must not evaluate'),**bad)


def test_infeasible_or_nonfinite_native_start_cannot_be_recapped():
    problem=SimpleNamespace(initial=np.zeros(1))
    for native in ([.01],[float('nan')]):
        with pytest.raises(ValueError):surface.optimize(problem,lambda *a:dict(native=np.asarray(native)))


def test_surface_fit_requires_policy_and_rejects_infeasible_original_start(tmp_path):
    from native_scene_fit import run
    from test_native_scene_geometry import policy
    _,_,contacts,_,permissions,_,_=prepare(tmp_path)
    with pytest.raises(ValueError,match='policy'):run(contacts,permissions,tmp_path/'no-policy',proposal_model='surface-vector')
    assert not (tmp_path/'no-policy').exists()
    path=tmp_path/'policy.json';save(path,policy(contacts))
    with pytest.raises(ValueError,match='feasible'):run(contacts,permissions,tmp_path/'failed',proposal_model='surface-vector',geometry_policy=path)
    assert read(tmp_path/'failed/pipeline.json')['status']=='failed'
    assert not (tmp_path/'failed/result.json').exists()
    assert (tmp_path/'failed/probes/start/geometry.json').exists()


def test_surface_fit_retains_exact_original_epoch_and_full_probe_geometry(tmp_path):
    from native_scene_fit import run
    scene,p,digest=scene_fixture(tmp_path);spec=read(tmp_path/'contacts.json')
    row=spec['contacts'][0];row.update(mode='touch',interval_s=[1.,1.],limits=dict(position_m=.03))
    row['target']=dict(space='world',points_m=[scene.actor_points('A',np.array([0]),[1.])[0,0].tolist()])
    contacts=tmp_path/'contacts.json';save(contacts,spec);digest=sha256(contacts);p['contacts_sha256']=digest
    policy=tmp_path/'policy.json';save(policy,p)
    permission=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)))
    permissions=tmp_path/'permissions.json';save(permissions,permission)
    out=tmp_path/'job';result=run(contacts,permissions,out,proposal_model='surface-vector',geometry_policy=policy,iterations=1,restoration_steps=1)
    assert result['native_constraints_pass'] and result['original_selected'] and not result['release_approved']
    assert result['optimization']['all_original_norms_protected']
    for probe in result['probes']:
        if probe['label']!='final':
            assert (out/'probes'/probe['label']/'geometry.json').exists()
            assert read(out/'probes'/probe['label']/'policy.json')['contacts_sha256']==sha256(out/'probes'/probe['label']/'contacts.json')
    request=read(out/'request.json')
    for name,actor in spec['actors'].items():assert sha256(out/request['actor_snapshots'][name]['path'])==actor['sha256']
    assert result['sampled_geometry_conditions_pass'] is False
