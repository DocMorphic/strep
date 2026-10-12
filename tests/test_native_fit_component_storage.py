"""Actual mixed saved-key repair, public fitting and original-bound continuation."""
from pathlib import Path
from types import SimpleNamespace
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_component_storage import fixture
from native_component_storage_repair import ComponentAdjustedEdits
from native_component_storage_continuation import ComponentContinuationEdits,state_for
from native_fit_component_storage import FitComponentStorage
from native_component_storage_search import apply_choice,plan
import native_component_storage_search as searcher
from native_scene_fit import SceneProblem,run
from native_rotation_speed_fit import SpeedLimitedSceneProblem
from strep import save,read,sha256


def test_typed_restore_replace_does_not_touch_another_path():
    row=dict(actor='A',node=0,path='translation',key_index=3,component=1,step=1)
    other=dict(row,path='rotation');seed=[row,other]
    assert apply_choice(seed,dict(row,step=0))==[other]
    assert apply_choice(seed,dict(row,step=-1))==[other,dict(row,step=-1)]
    assert seed==[row,other]
    for step in (True,2):
        with pytest.raises(ValueError):apply_choice(seed,dict(row,step=step))


@pytest.mark.parametrize('metric',[0,1,2,3])
def test_planner_root_translation_covers_positional_but_not_angular_metrics(monkeypatch,metric):
    shapes=[(4,1),(3,1),(4,1),(3,1)];values=[np.zeros(s) for s in shapes];values[metric][1,0]=.1
    rate=SimpleNamespace(dt=.25,tolerance=1e-5,caps=[np.zeros(s) for s in shapes])
    tracks=[dict(node=0,path=p,clock=np.array([0.,.1,.3,.6,.9,1.]),ids=np.array([1,2,3,4])) for p in ('rotation','translation')]
    rig=SimpleNamespace(joints=[0],parents=[-1]);problem=SimpleNamespace(scene=SimpleNamespace(actors={'A':dict(rig=rig)}),
        caps={'A':rate},edits=SimpleNamespace(actors={'A':dict(tracks=tracks)}),rate_ids=np.arange(5),uniform=np.arange(5)*.25)
    monkeypatch.setattr(searcher,'features',lambda *args:None);monkeypatch.setattr(searcher,'measures',lambda *args:values)
    options,failures=plan(problem,{'A':np.zeros((5,1))},[])
    assert failures[0]['node']==0 and {r['path'] for r in options}==({'translation'} if metric<2 else {'rotation'})
    assert {r['component'] for r in options}==(set(range(3)) if metric<2 else set(range(4)))
    assert {r['key_index'] for r in options}<=set(tracks[0]['ids'])
    disabled,_=plan(problem,{'A':np.zeros((5,1))},[],allowed_paths=('rotation',))
    if metric<2:assert disabled==[]


@pytest.mark.parametrize('speed',[False,True])
def test_actual_root_storage_defect_is_repaired_then_reused_with_fresh_checks(tmp_path,speed):
    base,policy,row,*_=fixture(tmp_path);path=tmp_path/'seed.glb';ComponentAdjustedEdits(base,policy,[row]).export('A',base.initial,path)
    state=state_for(base,policy,base.initial,[row],{'A':path});continued=ComponentContinuationEdits(base,policy,state,tmp_path)
    problem=SpeedLimitedSceneProblem(base.scene,continued,rotation_speed_limits={('A',3):0.}) if speed else SceneProblem(base.scene,continued)
    helper=FitComponentStorage(problem,policy,stages=2,probes=8);source=[a.copy() for a in problem.caps['A'].caps]
    first=tmp_path/'first';first.mkdir();native,worlds,edits,report=helper.evaluate(problem.initial,first)
    assert report['status']=='native-repaired' and report['native_failed_before']>0 and report['unrounded_failed']==0
    assert np.all(native<=0) and edits.corrections==[] and not report['geometry_assessed']
    search=read(first/'storage-search/search-result.json');assert search['schema']=='strep-native-component-storage-search-v1'
    assert any(p['choice']['path']=='translation' for stage in search['history'] for p in stage['probes'])
    second=tmp_path/'second';second.mkdir();fresh,fresh_worlds,_,result=helper.evaluate(problem.initial,second)
    assert result['status']=='native-repair-replayed' and len(result['native_probe_receipts_sha256'])==1
    np.testing.assert_array_equal(native,fresh);np.testing.assert_array_equal(worlds['A'],fresh_worlds['A'])
    assert sha256(first/'A.glb')==sha256(second/'A.glb')
    for a,b in zip(source,problem.caps['A'].caps):np.testing.assert_array_equal(a,b)
    if speed:assert problem.last_speed_output_audit['passed']


@pytest.mark.parametrize('speed',[False,True])
def test_public_component_fit_and_continuation_retain_original_caps(tmp_path,speed):
    base,policy,row,contacts,permissions,boundary=fixture(tmp_path)
    path=tmp_path/'seed.glb';ComponentAdjustedEdits(base,policy,[row]).export('A',base.initial,path)
    state=state_for(base,policy,base.initial,[row],{'A':path});state_path=tmp_path/'start.json';save(state_path,state)
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    geometry=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(contacts),
        clock=dict(mode='native-and-frame-populations',times_s=[0.,2.]),limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),
        planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-1.)))
    geometry_path=tmp_path/'geometry.json';save(geometry_path,geometry)
    speed_path=None
    if speed:
        speed_path=tmp_path/'speed.json';save(speed_path,dict(schema='strep-native-rotation-speed-policy-v1',contacts_sha256=sha256(contacts),
            tracks=[dict(actor='A',node=3,maximum_degrees_per_second=0.)]))
    args=dict(iterations=1,trust=.02,proposal_model='surface-vector',geometry_policy=geometry_path,
        boundary_edit=boundary,storage_repair_policy=policy_path,storage_repair_stages=2,storage_repair_probes=8,rotation_speed_policy=speed_path)
    first=tmp_path/'fit';result=run(contacts,permissions,first,storage_continuation=state_path,**args)
    assert result['native_constraints_pass'] and result['sampled_geometry_conditions_pass'] and result['original_selected']
    request=read(first/'request.json');assert 'native_component_storage_repair.py' in request['implementation_sha256']
    final=read(first/'final-storage-continuation.json');assert final['schema']=='strep-native-component-storage-continuation-v1' and final['corrections']==[]
    second=tmp_path/'next';continued=run(contacts,permissions,second,storage_continuation=first/'final-storage-continuation.json',**args)
    assert continued['native_constraints_pass'] and sha256(first/'source-rate-caps.npz')==sha256(second/'source-rate-caps.npz')
    if speed:assert result['rotation_speed_conditions_pass'] and continued['rotation_speed_conditions_pass']


def test_failed_intended_motion_is_not_hidden_by_component_repair(tmp_path):
    base,policy,_,*_=fixture(tmp_path);helper=FitComponentStorage(SceneProblem(base.scene,base),policy,stages=2,probes=8)
    value=base.initial.copy();value[1]=.5;folder=tmp_path/'bad';folder.mkdir()
    _,_,_,report=helper.evaluate(value,folder)
    assert report['status']=='intended-motion-failed' and report['unrounded_failed']>0 and len(report['native_probe_receipts_sha256'])==1


def test_changed_repair_archive_cannot_be_reused(tmp_path):
    base,policy,row,*_=fixture(tmp_path);path=tmp_path/'seed.glb';ComponentAdjustedEdits(base,policy,[row]).export('A',base.initial,path)
    state=state_for(base,policy,base.initial,[row],{'A':path});continued=ComponentContinuationEdits(base,policy,state,tmp_path)
    helper=FitComponentStorage(SceneProblem(base.scene,continued),policy,stages=2,probes=8)
    folder=tmp_path/'first';folder.mkdir();helper.evaluate(helper.problem.initial,folder)
    (folder/'unrounded-observations.npz').write_bytes(b'changed')
    next_folder=tmp_path/'next';next_folder.mkdir()
    with pytest.raises(ValueError,match='repair evidence changed'):helper.evaluate(helper.problem.initial,next_folder)
