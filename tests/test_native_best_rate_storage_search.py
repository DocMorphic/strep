"""Absolute neighboring values, full native evidence and finite support search."""
from pathlib import Path
from types import SimpleNamespace
import copy, sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_best_rate_storage_search as searcher
import native_rate_storage_search as planner
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest
from native_scene_boundary_edit import BoundarySceneEdits
from native_scene_contacts import SceneContacts
from native_scene_fit import SceneProblem
from strep import read,save,sha256
from test_native_rotation_storage_repair import fixture


def test_replacement_and_restore_never_accumulate_or_mutate_seed():
    row=dict(actor='A',node=3,key_index=2,component=3,step=1);seed=[row]
    assert searcher.apply_choice(seed,dict(row,step=0))==[]
    assert searcher.apply_choice(seed,dict(row,step=-1))==[dict(row,step=-1)]
    assert seed==[row] and row['step']==1
    for step in (True,2,-2):
        with pytest.raises(ValueError):searcher.apply_choice(seed,dict(row,step=step))


def test_planner_uses_all_interpolation_support_and_permitted_ancestors(monkeypatch):
    rate=SimpleNamespace(dt=.25,tolerance=1e-5,caps=[np.zeros((4,1)),np.zeros((3,1)),np.zeros((4,1)),np.zeros((3,1))])
    track=dict(node=0,path='rotation',clock=np.array([0.,.1,.3,.6,.9,1.]),ids=np.array([1,2,3,4]))
    rig=SimpleNamespace(joints=np.array([1]),parents=np.array([-1,0]))
    problem=SimpleNamespace(scene=SimpleNamespace(actors={'A':dict(rig=rig),'B':dict(rig=rig)}),caps={'A':rate},
        edits=SimpleNamespace(actors={'A':dict(tracks=[track])}),rate_ids=np.arange(5),uniform=np.arange(5)*.25)
    values=[a.copy() for a in rate.caps];values[3][1,0]=.1
    monkeypatch.setattr(planner,'features',lambda *args:None);monkeypatch.setattr(planner,'measures',lambda *args:values)
    seed=[dict(actor='A',node=0,key_index=3,component=3,step=1)]
    options,failures=searcher.plan(problem,{'A':np.zeros((5,1))},seed)
    assert len(failures)==1 and failures[0]['node']==1 and failures[0]['metric']==3
    assert {r['key_index'] for r in options}=={1,2,3,4}
    assert {r['component'] for r in options}=={0,1,2,3}
    assert {r['step'] for r in options if r['key_index']==3 and r['component']==3}=={0,-1}
    assert {r['step'] for r in options if r['key_index']!=3}=={-1,1}
    assert all(r['node']==0 for r in options)


def test_real_passing_export_is_checked_completely_without_unnecessary_search(tmp_path,monkeypatch):
    base,policy,_=fixture(tmp_path)
    path=tmp_path/'contacts.json';spec=read(path);row=spec['contacts'][0]
    row.update(mode='touch',interval_s=[0.,0.],limits={'position_m':1e-5},
        target=dict(space='world',points_m=base.scene.actor_points('A',base.scene.rows[0]['ids'],np.array([0.]))[0].tolist()))
    save(path,spec);request=copy.deepcopy(base.request);request['permissions']['contacts_sha256']=sha256(path)
    base=BoundarySceneEdits(request,SceneContacts(spec,tmp_path),sha256(path),rotation_storage_policy='source-scale')
    policy['authoring_sha256']=authoring_digest(base);problem=SceneProblem(base.scene,base);seen=[]
    def decode(corrections,label):
        adjusted=StorageAdjustedEdits(base,policy,corrections);path=tmp_path/(label+'.glb');adjusted.export('A',problem.initial,path)
        assert adjusted.audit('A',path,0,value=problem.initial)['passed'];seen.append(label)
        return problem.decoded({'A':path},problem.initial)
    monkeypatch.setattr(searcher,'plan',lambda *args:pytest.fail('already passing should not plan'))
    corrected,report=searcher.search(problem,problem.initial,policy,[],decode)
    assert corrected==[] and report['native_conditions_pass'] and seen==['start']
    assert report['tested_neighbors']==0 and report['history']==[]
    assert not report['geometry_assessed'] and not report['quality_approved'] and not report['release_approved']


def test_real_contact_failure_without_rate_support_stays_rejected(tmp_path):
    base,policy,_=fixture(tmp_path);problem=SceneProblem(base.scene,base)
    def decode(corrections,label):
        path=tmp_path/(label+'.glb');StorageAdjustedEdits(base,policy,corrections).export('A',problem.initial,path)
        return problem.decoded({'A':path},problem.initial)
    corrected,report=searcher.search(problem,problem.initial,policy,[],decode)
    assert corrected==[] and not report['native_conditions_pass'] and report['tested_neighbors']==0
    assert report['history'][0]['planned_options']==0 and report['history'][0]['original_rate_failures']==[]


@pytest.mark.parametrize('fault',['missing-actor','missing-time','nonfinite','false-residual','changed-cap'])
def test_incomplete_or_rebased_native_evidence_rejects(tmp_path,fault):
    base,policy,_=fixture(tmp_path);problem=SceneProblem(base.scene,base)
    def decode(corrections,label):
        adjusted=StorageAdjustedEdits(base,policy,corrections);path=tmp_path/(label+'.glb');adjusted.export('A',problem.initial,path)
        residual,worlds=problem.decoded({'A':path},problem.initial)
        if fault=='missing-actor':worlds.pop('A')
        elif fault=='missing-time':worlds['A']=worlds['A'][:-1]
        elif fault=='nonfinite':worlds['A'][0,0,0,0]=np.nan
        elif fault=='false-residual':residual=np.zeros_like(residual)
        else:problem.caps['A'].caps[0]+=1.;residual=problem.constraints(problem.initial,worlds)
        return residual,worlds
    with pytest.raises(ValueError):searcher.search(problem,problem.initial,policy,[],decode)


@pytest.mark.parametrize('settings',[dict(stages=True),dict(stages=0),dict(stages=9),dict(probes_per_stage=True),dict(probes_per_stage=0),dict(probes_per_stage=65)])
def test_invalid_budgets_reject_before_decode(settings):
    with pytest.raises(ValueError):searcher.search(None,None,None,None,lambda *args:pytest.fail('decode'),**settings)


def test_outside_boxes_rejects_before_decode(tmp_path):
    base,policy,_=fixture(tmp_path);problem=SceneProblem(base.scene,base)
    with pytest.raises(ValueError,match='control boxes'):
        searcher.search(problem,np.full(problem.size,1.01),policy,[],lambda *args:pytest.fail('decode'))


@pytest.mark.parametrize('metric,frame',[(m,f) for m in range(4) for f in range(4 if m in (0,2) else 3)])
def test_all_rate_stencils_and_strict_position_ancestors(monkeypatch,metric,frame):
    clocks=np.array([0.,.1,.25,.3,.5,.6,.75,.9,1.])
    tracks=[dict(node=n,path='rotation',clock=clocks.copy(),ids=np.arange(len(clocks))) for n in (0,1,2,3)]
    rig=SimpleNamespace(joints=np.array([2]),parents=np.array([-1,0,1,-1]))
    caps=[np.zeros((4,1)),np.zeros((3,1)),np.zeros((4,1)),np.zeros((3,1))]
    values=[v.copy() for v in caps];values[metric][frame,0]=.1
    rate=SimpleNamespace(dt=.25,tolerance=1e-5,caps=caps)
    problem=SimpleNamespace(scene=SimpleNamespace(actors={'A':dict(rig=rig)}),caps={'A':rate},
        edits=SimpleNamespace(actors={'A':dict(tracks=tracks)}),rate_ids=np.arange(5),uniform=np.arange(5)*.25)
    monkeypatch.setattr(planner,'features',lambda *args:None);monkeypatch.setattr(planner,'measures',lambda *args:values)
    options,failures=searcher.plan(problem,{'A':np.zeros((len(problem.rate_ids),1))},[])
    nodes={0,1} if metric<2 else {0,1,2};order=(1,2,1,2)[metric]
    ids={int(np.where(clocks==t)[0][0]) for t in problem.uniform[frame:frame+order+1]}
    expected={(n,k,c,s) for n in nodes for k in ids for c in range(4) for s in (-1,1)}
    assert {(o['node'],o['key_index'],o['component'],o['step']) for o in options}==expected
    assert len(options)==len(expected) and len(failures)==1 and failures[0]['metric']==metric


def test_shared_stencils_deduplicate_and_preserve_absolute_seed(monkeypatch):
    clock=np.array([0.,.5,1.]);track=dict(node=0,path='rotation',clock=clock,ids=np.arange(3))
    rig=SimpleNamespace(joints=np.array([1]),parents=np.array([-1,0]))
    caps=[np.zeros((2,1)),np.zeros((1,1)),np.zeros((2,1)),np.zeros((1,1))]
    values=[np.full_like(v,.1) for v in caps]
    problem=SimpleNamespace(scene=SimpleNamespace(actors={'A':dict(rig=rig)}),caps={'A':SimpleNamespace(dt=.5,tolerance=0,caps=caps)},
        edits=SimpleNamespace(actors={'A':dict(tracks=[track])}),rate_ids=np.arange(3),uniform=clock)
    monkeypatch.setattr(planner,'features',lambda *args:None);monkeypatch.setattr(planner,'measures',lambda *args:values)
    seed=[dict(actor='A',node=0,key_index=1,component=2,step=-1)];before=copy.deepcopy(seed)
    options,failures=searcher.plan(problem,{'A':np.zeros((len(problem.rate_ids),1))},seed)
    assert len(options)==24 and len(failures)==6 and seed==before
    assert {o['step'] for o in options if o['key_index']==1 and o['component']==2}=={0,1}
    assert len({tuple(o.values()) for o in options})==len(options)


def synthetic_search(monkeypatch,scores,budget=3):
    # Selector-only synthetic rows; actual native GLB evidence is tested above.
    edits=SimpleNamespace(actors={'A':None},controls=lambda v:np.asarray(v,float))
    problem=SimpleNamespace(edits=edits,scene=SimpleNamespace(actors={'A':dict(rig=SimpleNamespace(parents=[-1]))}),
        lower=np.array([-1.]),upper=np.array([1.]),times=np.array([0.]))
    problem.constraints=lambda value,worlds:worlds['A'][0,0,0,:len(scores[0])].copy()
    def rows(problem,value,worlds=None):
        residual=np.asarray(scores[0]) if worlds is None else problem.constraints(value,worlds)
        return SimpleNamespace(caps=np.zeros(len(residual)),scales=np.ones(len(residual)),residual=lambda:residual)
    monkeypatch.setattr(searcher,'rows',rows)
    monkeypatch.setattr(searcher,'StorageAdjustedEdits',lambda *args:SimpleNamespace(actors=['A'],values=lambda *args:None))
    choices=[dict(actor='A',node=0,key_index=i,component=0,step=1) for i in range(len(scores)-1)]
    monkeypatch.setattr(searcher,'plan',lambda *args:(choices,[]));seen=[];references=[]
    def decode(corrections,label):
        index=0 if label=='start' else corrections[-1]['key_index']+1
        world=np.zeros((1,1,4,4));world[0,0,0,:len(scores[0])]=scores[index];seen.append(index)
        return problem.constraints(np.array([0.]),{'A':world}),{'A':world}
    result=searcher.search(problem,np.array([0.]),{},[],decode,stages=1,probes_per_stage=budget)
    return result,seen


@pytest.mark.parametrize('scores,expected',[
    ([[10.],[9.],[2.],[4.]],1),
    ([[10.],[2.],[2.],[4.]],0),
    ([[10.,0.],[5.,3.],[5.,1.],[8.,0.]],1),
    ([[10.],[11.],[10.],[12.]],None)])
def test_best_eligible_neighbor_and_stable_ties(monkeypatch,scores,expected):
    (corrections,report),seen=synthetic_search(monkeypatch,scores)
    assert seen==[0,1,2,3] and report['tested_neighbors']==3
    if expected is None:assert corrections==[] and report['final_label']=='start'
    else:assert corrections[-1]['key_index']==expected and report['final_label']==f'storage-0-{expected}'
    assert not report['quality_approved'] and not report['geometry_assessed']


def test_best_is_limited_to_explicit_probed_budget(monkeypatch):
    (corrections,report),seen=synthetic_search(monkeypatch,[[10.],[9.],[2.],[1.]],2)
    assert seen==[0,1,2] and corrections[-1]['key_index']==1 and report['tested_neighbors']==2


def test_native_pass_ends_search_without_unneeded_queries(monkeypatch):
    (corrections,report),seen=synthetic_search(monkeypatch,[[10.],[9.],[-1.],[-2.]])
    assert seen==[0,1,2] and corrections[-1]['key_index']==1 and report['native_conditions_pass']
    assert not report['quality_approved'] and not report['release_approved']
