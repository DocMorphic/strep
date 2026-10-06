"""Absolute neighboring values, full native evidence and finite support search."""
from pathlib import Path
from types import SimpleNamespace
import copy, sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_rotation_storage_search as searcher
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
    monkeypatch.setattr(searcher,'features',lambda *args:None);monkeypatch.setattr(searcher,'measures',lambda *args:values)
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


def test_real_contact_failure_without_angular_support_stays_rejected(tmp_path):
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
