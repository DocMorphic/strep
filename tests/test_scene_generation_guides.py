"""Model-free request, contact-clock and immutable-planning regressions."""
import copy
import json
import shutil
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import scene_generation as generation
import scene_generation_guides as guide_module
from generation_constraints import validate_guides
from scene_generation_guides import plan_frames, guides_from_plan, audit_plan, validate_prepared_guidance, preview
from strep import ROOT, sha256, save


def fixture_scene():
    return dict(frame_count=120, actors={name:dict(motion=f'{name}.npz', source_sha256='a'*64,
                transform=dict(translation_m=[0,0,0], rotation_xyzw=[0,0,0,1])) for name in ['A','B']},
                contacts=[dict(id='touch',actor='A',effector=dict(joint='RightHand'),start_frame=0,end_frame=119,
                               target=dict(space='actor',actor='B',joint='LeftHand'))])


def fixture_plan():
    return {n:dict(segments=[dict(prompt='A person vaults then hands a parcel to a partner.', duration_s=4)],
                   seeds=[17], guide_plan=dict(mode='sparse', maximum_frames=19)) for n in ['A','B']}


def test_sustained_partner_intent_keeps_full_clock_and_sparse_both_actor_guides():
    scene=fixture_scene();original=copy.deepcopy(scene)
    for actor,joint in [('A','RightHand'),('B','LeftHand')]:
        record=plan_frames(scene,actor,dict(mode='sparse'))
        assert record['complete_target_frames']==list(range(120)) and len(record['selected_frames'])==19
        assert record['selected_frames'][0]==0 and record['selected_frames'][-1]==119
        guides=guides_from_plan(scene,actor,record);validate_guides(guides,120)
        assert guides[0]['joint_names']==[joint]
        assert guides[0]['source_frames']==record['selected_frames']==guides[0]['frame_indices']
    assert scene==original


def test_contact_boundaries_and_effector_changes_cannot_be_thinned():
    scene=fixture_scene();scene['contacts'].append(dict(id='grasp',actor='A',effector=dict(joint='LeftHand'),
        start_frame=30,end_frame=60,target=dict(space='object',object='parcel')))
    with pytest.raises(ValueError,match='boundaries'):plan_frames(scene,'A',dict(mode='sparse',maximum_frames=5))
    record=plan_frames(scene,'A',dict(mode='sparse',maximum_frames=6))
    assert record['selected_frames']==record['mandatory_frames']==[0,29,30,60,61,119]
    guides=guides_from_plan(scene,'A',record);validate_guides(guides,120)
    assert {tuple(g['joint_names']):g['frame_indices'] for g in guides}=={
        ('RightHand',):[0,29,61,119],('LeftHand','RightHand'):[30,60]}


def test_disconnected_events_exceeding_budget_reject_without_dropping_contacts():
    scene=fixture_scene();scene['contacts']=[dict(scene['contacts'][0],id=str(f),start_frame=f,end_frame=f) for f in range(20)]
    original=copy.deepcopy(scene)
    with pytest.raises(ValueError,match='boundaries'):plan_frames(scene,'A',dict(mode='sparse'))
    assert scene==original


@pytest.mark.parametrize('options',[
    {},{'mode':'dense'},{'mode':'sparse','maximum_frames':20},{'mode':'sparse','maximum_frames':True},
    {'mode':'sparse','extra':1},{'mode':'sparse','frame_indices':[119,0]},
    {'mode':'sparse','frame_indices':[0,0,119]},{'mode':'sparse','frame_indices':[0]},
    {'mode':'sparse','frame_indices':[False,119]},{'mode':'sparse','frame_indices':[0,120]},
    {'mode':'sparse','frame_indices':None}])
def test_invalid_or_event_losing_sparse_plan_rejected(options):
    with pytest.raises(ValueError):plan_frames(fixture_scene(),'A',options)


def test_historical_dense_and_explicit_manual_sparse_are_distinct():
    scene=fixture_scene();dense=plan_frames(scene,'A');sparse=plan_frames(scene,'A',dict(mode='sparse',frame_indices=[0,60,119]))
    assert dense['selected_frames']==list(range(120)) and not dense['within_sparse_recommendation']
    assert sparse['selected_frames']==[0,60,119] and sparse['complete_target_frames']==dense['complete_target_frames']
    assert sparse['quality_approved'] is False and sparse['release_approved'] is False


@pytest.fixture
def compiled(tmp_path,monkeypatch):
    scene=fixture_scene();plan=fixture_plan()
    for actor,entry in scene['actors'].items():
        p=tmp_path/entry['motion'];p.write_bytes(b'fixture only; no model/rig imported');entry['source_sha256']=sha256(p)
    monkeypatch.setattr(generation,'ROOT',tmp_path)
    calls=[]
    def compile_without_model(request):
        validate_guides(request.get('generation_constraints',[]),120);calls.append(copy.deepcopy(request))
    monkeypatch.setattr(generation,'compile_guides',compile_without_model)
    batch=generation.requests(scene,plan)
    assert len(calls)==4 and len(batch['requests'])==4
    assert all('guide_plan' not in r for r in batch['requests'])
    folder=tmp_path/'prepared';folder.mkdir();(folder/'source-snapshot').mkdir()
    save(folder/'authored-scene.json',scene);save(folder/'actor-plan.json',plan)
    save(folder/'generation-guide-plan.json',audit_plan(scene,plan))
    shutil.copyfile(ROOT/'scripts/scene_generation_guides.py',folder/'source-snapshot/scene_generation_guides.py')
    freeze=dict(scene_sha256=sha256(folder/'authored-scene.json'),plan_sha256=sha256(folder/'actor-plan.json'),
                generation_guide_plan_sha256=sha256(folder/'generation-guide-plan.json'),
                guide_planner_sha256=sha256(ROOT/'scripts/scene_generation_guides.py'),actor_order=list(plan))
    return folder,scene,plan,batch,freeze


def test_request_pipeline_and_saved_plan_preserve_full_intent(compiled):
    folder,scene,plan,batch,freeze=compiled
    result=validate_prepared_guidance(folder,freeze,batch)
    assert result==audit_plan(scene,plan) and result['full_scene_evaluation_unchanged']
    assert all(len(a['selected_frames'])==19 and len(a['complete_target_frames'])==120 for a in result['actors'].values())
    assert batch['requests'][0]['segments']==plan['A']['segments']
    assert batch['requests'][1]['generation_constraints'][0]['joint_names']==['RightHand']
    assert batch['requests'][3]['generation_constraints'][0]['joint_names']==['LeftHand']


@pytest.mark.parametrize('defect',['binding','rebound_population','request_frames','request_actor','effectors','snapshot','missing','seeds','scene'])
def test_pre_inference_check_rejects_changed_or_dropped_plan(compiled,defect):
    folder,scene,plan,batch,freeze=compiled
    if defect=='binding':freeze.pop('generation_guide_plan_sha256')
    if defect=='rebound_population':
        record=json.loads((folder/'generation-guide-plan.json').read_text());record['actors']['A']['complete_target_frames']=[0,119]
        save(folder/'generation-guide-plan.json',record);freeze['generation_guide_plan_sha256']=sha256(folder/'generation-guide-plan.json')
    if defect=='request_frames':batch['requests'][1]['generation_constraints'][0]['frame_indices']=[0,119]
    if defect=='request_actor':batch['requests'].pop()
    if defect=='effectors':batch['requests'][1]['generation_constraints'][0]['joint_names']=['LeftHand']
    if defect=='snapshot':(folder/'source-snapshot/scene_generation_guides.py').write_text('changed')
    if defect=='missing':(folder/'generation-guide-plan.json').unlink()
    if defect=='seeds':batch['requests'][1]['seeds']=[18]
    if defect=='scene':scene['contacts'][0]['end_frame']=110;save(folder/'authored-scene.json',scene)
    with pytest.raises(ValueError):validate_prepared_guidance(folder,freeze,batch)


def test_legacy_batch_does_not_need_new_artifacts(tmp_path):
    assert validate_prepared_guidance(tmp_path,{},dict(requests=[])) is None


def test_new_plan_cannot_drop_complete_reference_preflight(compiled):
    folder,scene,plan,batch,freeze=compiled;save(folder/'freeze.json',freeze)
    from scene_target_preflight import validate_preflight
    with pytest.raises(ValueError,match='preflight binding'):validate_preflight(folder,batch)


def test_preview_is_offline_and_retains_existing_output(tmp_path):
    source=tmp_path/'scene.json';plan=tmp_path/'plan.json';output=tmp_path/'preview.json'
    save(source,dict(scene=fixture_scene()));save(plan,fixture_plan())
    result=preview(source,plan,output);original=output.read_bytes()
    assert result['source_pose_geometry_checked'] is False and result['generated_motion_checked'] is False
    assert result['plan']['actors']['A']['complete_target_frames']==list(range(120))
    assert len(result['plan']['actors']['B']['selected_frames'])==19
    with pytest.raises(ValueError,match='previous'):preview(source,plan,output)
    assert output.read_bytes()==original


@pytest.mark.parametrize('defect',['null_options','missing_actor','duration','unknown_option','invalid_seed'])
def test_invalid_preview_schedule_rejected_before_creating_output(tmp_path,defect):
    value=fixture_plan()
    if defect=='null_options':value['A']['guide_plan']=None
    if defect=='missing_actor':del value['B']
    if defect=='duration':value['A']['segments'][0]['duration_s']=3
    if defect=='unknown_option':value['A']['other']=1
    if defect=='invalid_seed':value['A']['seeds']=[True]
    source=tmp_path/'scene.json';plan=tmp_path/'plan.json';output=tmp_path/'preview.json'
    save(source,fixture_scene());save(plan,value)
    with pytest.raises(ValueError):preview(source,plan,output)
    assert not output.exists()


def test_preview_rejects_inputs_changed_after_read_instead_of_binding_different_bytes(tmp_path,monkeypatch):
    source=tmp_path/'scene.json';plan=tmp_path/'plan.json';output=tmp_path/'preview.json'
    save(source,fixture_scene());save(plan,fixture_plan());original_read=guide_module.read
    def racing_read(path):
        value=original_read(path)
        if Path(path)==source:
            changed=copy.deepcopy(value);changed['contacts'][0]['end_frame']=110;save(source,changed)
        return value
    monkeypatch.setattr(guide_module,'read',racing_read)
    with pytest.raises(ValueError,match='inputs changed'):preview(source,plan,output)
    assert not output.exists()
