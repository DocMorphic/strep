"""Model-free actor-profile propagation and conditioning provenance checks."""
import copy
import shutil
import pytest
from test_scene_generation_guides import compiled, fixture_scene, fixture_plan
import scene_generation as generation
import scene_generation_guides as guides
from action_requests import request_digest
from motion_profile import default_profile, brief, resolved_segments
from strep import ROOT, save, read, sha256


def profiles():
    first=default_profile();first.update(name='Courier',style='Nimble and springy',training='Parkour',state='Alert')
    first['stats'][0]['value']=91;first['stats'][-1]['value']=88
    second=default_profile();second.update(name='Guard',style='Heavy and deliberate',training='Powerlifting',state='Cautious')
    second['stats'][0]['value']=12
    second['stats'].append(dict(id='confidence',label='Confidence',value=95,
        levels=['Timid gestures','Composed gestures','Assured gestures']))
    return first,second


@pytest.fixture
def profiled(compiled):
    folder,scene,plan,_,freeze=compiled
    for name,profile in zip(plan,profiles()):
        plan[name]['motion_profile']=profile
        plan[name]['segments']=[dict(prompt='Vault over a rail.',duration_s=2),
                                dict(prompt='Hand a parcel to a partner.',duration_s=2)]
        plan[name]['seeds']=[17,29]
    batch=generation.requests(scene,plan)
    save(folder/'actor-plan.json',plan);save(folder/'request.json',batch)
    save(folder/'generation-guide-plan.json',guides.audit_plan(scene,plan))
    shutil.copyfile(ROOT/'scripts/motion_profile.py',folder/'source-snapshot/motion_profile.py')
    freeze.update(plan_sha256=sha256(folder/'actor-plan.json'),
        generation_guide_plan_sha256=sha256(folder/'generation-guide-plan.json'),
        profile_compiler_sha256=sha256(ROOT/'scripts/motion_profile.py'),request_sha256=request_digest(batch))
    save(folder/'freeze.json',freeze)
    return folder,scene,plan,batch,freeze


def test_actor_controls_survive_both_modes_without_aliasing(profiled):
    folder,scene,plan,batch,freeze=profiled;original=copy.deepcopy(plan)
    result=guides.validate_prepared_guidance(folder,freeze,batch)
    for i,name in enumerate(plan):
        baseline,guided=batch['requests'][2*i:2*i+2]
        assert baseline['motion_profile']==guided['motion_profile']==plan[name]['motion_profile']
        assert resolved_segments(baseline)==resolved_segments(guided)
        assert [s['duration_s'] for s in resolved_segments(baseline)]==[2,2]
        assert result['motion_profiles'][name]==brief(baseline)
        assert result['motion_profiles'][name]['response_validated'] is False
    assert 'Quick, precise' in resolved_segments(batch['requests'][0])[0]['prompt']
    assert 'Careful, unhurried' in resolved_segments(batch['requests'][2])[0]['prompt']
    assert 'Assured gestures' in resolved_segments(batch['requests'][2])[1]['prompt']
    assert result['motion_profiles']['A']['unmapped_stats']==[dict(id='endurance',label='Endurance',value=88)]
    batch['requests'][0]['motion_profile']['stats'][0]['value']=0
    batch['requests'][0]['segments'][0]['prompt']='Changed'
    assert plan==original and batch['requests'][1]['motion_profile']['stats'][0]['value']==91


def test_mixed_profile_plan_preserves_absence_and_legacy_defaults(profiled):
    folder,scene,plan,batch,freeze=profiled
    del plan['B']['motion_profile']
    batch=generation.requests(scene,plan)
    result=guides.audit_plan(scene,plan)
    assert result['motion_profiles']['B'] is None
    assert all('motion_profile' not in r for r in batch['requests'][2:])
    assert resolved_segments(batch['requests'][2])==plan['B']['segments']
    assert 'motion_profiles' not in guides.audit_plan(scene,fixture_plan())


@pytest.mark.parametrize('mode',['dense','sparse'])
@pytest.mark.parametrize('target',['object','partner'])
def test_profiles_keep_object_and_partner_contact_clocks(mode,target):
    scene=fixture_scene();plan=fixture_plan()
    if target=='object':
        scene['actors'].pop('B');plan.pop('B')
        scene['contacts'][0]['target']=dict(space='object',object='parcel')
    for name in plan:
        plan[name]['motion_profile']=profiles()[0]
        if mode=='dense':plan[name].pop('guide_plan')
    report=guides.audit_plan(scene,plan)
    for name in plan:
        assert report['actors'][name]['complete_target_frames']==list(range(120))
        assert len(report['actors'][name]['selected_frames'])==(120 if mode=='dense' else 19)
        assert report['motion_profiles'][name]['segments'][0]['original_prompt']==plan[name]['segments'][0]['prompt']
    assert report['quality_approved'] is report['release_approved'] is False


@pytest.mark.parametrize('defect',['null','value','rules','long_description'])
def test_invalid_profile_fails_before_request_compilation(compiled,monkeypatch,defect):
    _,scene,plan,_,_=compiled;plan['A']['motion_profile']=profiles()[0]
    if defect=='null':plan['A']['motion_profile']=None
    if defect=='value':plan['A']['motion_profile']['stats'][0]['value']=True
    if defect=='rules':plan['A']['motion_profile']['stats'][0]['levels']=['one']
    if defect=='long_description':plan['A']['segments'][0]['prompt']='x'*1000
    def unexpected_compile(_):raise AssertionError('Invalid profile reached pose compiler')
    monkeypatch.setattr(generation,'compile_guides',unexpected_compile)
    with pytest.raises(ValueError):generation.requests(scene,plan)


@pytest.mark.parametrize('defect',['dropped','swapped','mutated','added_to_absent'])
def test_request_profile_population_cannot_be_changed(profiled,defect):
    folder,scene,plan,batch,freeze=profiled
    if defect=='dropped':del batch['requests'][1]['motion_profile']
    if defect=='swapped':batch['requests'][1]['motion_profile']=copy.deepcopy(plan['B']['motion_profile'])
    if defect=='mutated':batch['requests'][1]['motion_profile']['stats'][-1]['value']=89
    if defect=='added_to_absent':
        del plan['B']['motion_profile'];save(folder/'actor-plan.json',plan)
        freeze['plan_sha256']=sha256(folder/'actor-plan.json')
        save(folder/'generation-guide-plan.json',guides.audit_plan(scene,plan))
        freeze['generation_guide_plan_sha256']=sha256(folder/'generation-guide-plan.json')
    with pytest.raises(ValueError,match='actor motion profile'):guides.validate_prepared_guidance(folder,freeze,batch)


@pytest.mark.parametrize('defect',['binding','snapshot_missing','snapshot_changed','hash_rebound','brief_rebound'])
def test_profile_compiler_and_exact_resolved_wording_are_bound(profiled,defect):
    folder,scene,plan,batch,freeze=profiled;snapshot=folder/'source-snapshot/motion_profile.py'
    if defect=='binding':freeze.pop('profile_compiler_sha256')
    if defect=='snapshot_missing':snapshot.unlink()
    if defect=='snapshot_changed':snapshot.write_text('changed',encoding='utf-8')
    if defect=='hash_rebound':
        snapshot.write_text('changed',encoding='utf-8');freeze['profile_compiler_sha256']=sha256(snapshot)
    if defect=='brief_rebound':
        report=read(folder/'generation-guide-plan.json')
        report['motion_profiles']['A']['segments'][0]['conditioning_prompt']='Unrelated motion'
        save(folder/'generation-guide-plan.json',report)
        freeze['generation_guide_plan_sha256']=sha256(folder/'generation-guide-plan.json')
    with pytest.raises(ValueError):guides.validate_prepared_guidance(folder,freeze,batch)


def test_prepare_writes_profile_snapshot_and_matched_requests(profiled,monkeypatch,tmp_path):
    folder,scene,plan,batch,freeze=profiled;source=tmp_path/'source.json';actor_plan=tmp_path/'actors.json'
    save(source,scene);save(actor_plan,plan)
    monkeypatch.setattr(generation,'ROOT',ROOT)  # Method snapshot paths; poses are substituted below.
    monkeypatch.setattr(generation,'requests',lambda *_:batch)
    monkeypatch.setattr(generation.np,'load',lambda *a,**k:{})
    monkeypatch.setattr(generation,'evaluate',lambda *_:dict(contacts=[]))
    monkeypatch.setattr(generation,'orientation',lambda *_:dict(contacts=[]))
    def fake_preflight(_scene,output,**kwargs):
        output.mkdir();save(output/'audit.json',dict(reference_screens_passed=True))
        return dict(reference_screens_passed=True)
    monkeypatch.setattr(generation,'write_preflight',fake_preflight)
    output=tmp_path/'new-preparation';generation.prepare(source,actor_plan,output)
    bound=read(output/'freeze.json')
    assert sha256(output/'source-snapshot/motion_profile.py')==bound['profile_compiler_sha256']
    assert guides.validate_prepared_guidance(output,bound,read(output/'request.json'))==guides.audit_plan(scene,plan)


def test_profile_metadata_preview_binds_compiler_without_pose_loading(profiled,tmp_path):
    folder,scene,plan,batch,freeze=profiled
    result=guides.preview(folder/'authored-scene.json',folder/'actor-plan.json',tmp_path/'preview.json')
    assert result['plan']['motion_profiles']==guides.audit_plan(scene,plan)['motion_profiles']
    assert result['inputs_sha256'][str((ROOT/'scripts/motion_profile.py').resolve())]==sha256(ROOT/'scripts/motion_profile.py')
    assert result['source_pose_geometry_checked'] is result['generated_motion_checked'] is False


def record_for(request,digest,seed=17):
    record=dict(status='generated',request=copy.deepcopy(request),seed=seed,request_sha256=digest)
    if 'motion_profile' in request:record['motion_brief']=brief(request)
    return record


@pytest.mark.parametrize('defect',['actor','seed','boolean_seed','batch','failed','missing_brief','wording','unmapped','extra_brief'])
def test_exported_take_must_match_actor_seed_and_conditioning(profiled,defect):
    _,_,_,batch,freeze=profiled;request=batch['requests'][0];digest=freeze['request_sha256'];record=record_for(request,digest)
    assert guides.validate_take_record(request,17,digest,record)==brief(request)
    if defect=='actor':record['request']=copy.deepcopy(batch['requests'][2])
    if defect=='seed':record['seed']=29
    if defect=='boolean_seed':record['seed']=True
    if defect=='batch':record['request_sha256']='0'*64
    if defect=='failed':record['status']='failed'
    if defect=='missing_brief':del record['motion_brief']
    if defect=='wording':record['motion_brief']['segments'][0]['conditioning_prompt']='Wrong motion'
    if defect=='unmapped':record['motion_brief']['unmapped_stats'][0]['value']=89
    if defect=='extra_brief':
        request=copy.deepcopy(request);del request['motion_profile'];record['request']=request
    with pytest.raises(ValueError):guides.validate_take_record(request,17,digest,record)


def test_unprofiled_take_remains_valid():
    request=dict(id='actor-0-baseline',label='A',**guides.actor_request_fields(fixture_plan()['A']))
    assert guides.validate_take_record(request,17,'digest',record_for(request,'digest')) is None


def test_scene_build_rejects_wrong_actor_before_reading_assets(profiled,monkeypatch):
    folder,scene,plan,batch,freeze=profiled;save(folder/'pipeline.json',dict(status='complete'))
    take=folder/'takes/actor-0-baseline-seed-17';take.mkdir(parents=True)
    save(take/'generation-record.json',record_for(batch['requests'][2],freeze['request_sha256']))
    monkeypatch.setattr(generation,'validate_preflight',lambda *_:None)
    def unexpected_load(*a,**k):raise AssertionError('Mismatched actor reached pose loading')
    monkeypatch.setattr(generation.np,'load',unexpected_load)
    with pytest.raises(ValueError,match='actor request'):generation.build(folder)
