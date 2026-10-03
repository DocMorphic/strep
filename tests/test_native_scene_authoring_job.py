"""Explicitly mocked orchestration, not actual engine/model execution."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_scene_authoring_job as job
from strep import read,save,sha256
from test_native_object_hold_fit import fixture
from test_native_scene_geometry import policy


def authored(tmp_path,edit=False):
    source,path,spec,scene,request=fixture(tmp_path)
    pp=tmp_path/'policy.json';save(pp,policy(path));engine=tmp_path/'fixture-engine';engine.write_bytes(b'fake engine, never executed')
    rp=tmp_path/'edit.json';save(rp,request);recipe=tmp_path/'recipe.json'
    job.plan(path,pp,engine,recipe,rp if edit else None)
    return recipe,source,path,pp,engine,rp


def mocked(monkeypatch,output,*,combined_pass=True,fit_pass=True,fault=None):
    calls=[];monkeypatch.setattr(job,'worker_busy',lambda:False)
    def call(name,folder,result):
        folder.mkdir(parents=True);calls.append(name)
        if fault==name:raise ValueError('deliberate fixture failure: '+name)
        save(folder/'result.json',result);return result
    def contacts(path,folder):return call('source-contacts',folder,dict(schema='strep-native-scene-contact-audit-v1',spec_sha256=sha256(path),passed=False))
    def fit(path,request,policy,folder):
        result=call('object-edit',folder,dict(status='complete',actor_bytes_unchanged=True,sampled_constraints_pass=fit_pass))
        save(folder/'proposal-contacts.json',read(path));save(folder/'geometry-policy.json',read(policy))
        result['proposal_contacts_sha256']=sha256(folder/'proposal-contacts.json');save(folder/'result.json',result);return result
    def asset(path,folder):return call('objects-source',folder,dict(status='complete'))
    def prepare(path,policy,asset,folder):
        result=call('objects-common',folder,dict(status='complete'));save(folder/'common-policy.json',read(policy));return result
    def objects(asset,folder,engine):return call('objects-engine',folder,dict(status='complete'))
    def actors(path,folder,**kwargs):
        assert kwargs['geometry_policy']==output/'objects-common/common-policy.json'
        assert kwargs['playback_mode']=='native-authoring'
        return call('actors-engine',folder,dict(status='complete'))
    def combined(path,policy,actors,objects,folder):
        assert policy==output/'objects-common/common-policy.json'
        return call('combined-engine',folder,dict(status='complete',samples=3,all_sampled_conditions_pass=combined_pass))
    def replay(path,policy,actors,objects,combined,folder):
        return call('replay',folder,dict(status='complete',recorded_sampled_conditions_pass=combined_pass,
            combined_files_sha256={str(combined/'result.json'):sha256(combined/'result.json')}))
    for name,function in dict(contact_run=contacts,fit_run=fit,asset_run=asset,clock_prepare=prepare,
        object_run=objects,actor_run=actors,combined_run=combined,replay_run=replay).items():monkeypatch.setattr(job,name,function)
    return calls


@pytest.mark.parametrize('edit,combined_pass,fit_pass',[(False,True,True),(False,False,True),(True,True,True),(True,False,True),(True,True,False)])
def test_full_sequence_keeps_numerical_failures_and_original_selection(tmp_path,monkeypatch,edit,combined_pass,fit_pass):
    recipe,*inputs=authored(tmp_path,edit);out=tmp_path/'job';before={p:sha256(p) for p in [recipe]+inputs}
    calls=mocked(monkeypatch,out,combined_pass=combined_pass,fit_pass=fit_pass);result=job.run(recipe,out)
    expected=['source-contacts']+(['object-edit'] if edit else [])+['objects-source','objects-common','objects-engine','actors-engine','combined-engine','replay']
    assert calls==expected==[s['id'] for s in result['stages']]
    assert result['sampled_conditions_pass']==(combined_pass and (not edit or fit_pass))
    assert result['source_contact_conditions_pass'] is False and result['object_edit_requested']==edit
    assert result['object_edit_conditions_pass']==(fit_pass if edit else None)
    assert result['original_selected'] and not result['studio_selection_changed']
    for key in ('quality_approved','training_admitted','release_approved','gpu_render_checked','physics_verified','real_time_playback_verified','human_review_submitted'):
        assert result[key] is False
    assert before=={p:sha256(p) for p in before}
    assert not any(sha256(out/e['path'])==sha256(inputs[3]) for e in result['source_snapshots'].values())
    assert all(sha256(out/s['id']/'result.json')==s['result_sha256'] for s in result['stages'])
    assert all(sha256(p)==h for p,h in result['derived_inputs_sha256'].items())
    assert read(out/'pipeline.json')['status']=='complete'
    assert Path(result['artifacts']['active_contacts'])==(out/'object-edit/proposal-contacts.json' if edit else inputs[1])
    with pytest.raises(ValueError,match='Fresh'):job.run(recipe,out)


@pytest.mark.parametrize('stage',['source-contacts','object-edit','objects-source','objects-common','objects-engine','actors-engine','combined-engine','replay'])
def test_terminal_execution_failures_keep_partial_outputs_and_do_not_restart(tmp_path,monkeypatch,stage):
    recipe,*_=authored(tmp_path,True);out=tmp_path/'job';calls=mocked(monkeypatch,out,fault=stage)
    with pytest.raises(ValueError,match='deliberate fixture failure'):job.run(recipe,out)
    pipeline=read(out/'pipeline.json');assert pipeline['status']=='failed' and pipeline['original_selected']
    assert calls[-1]==stage and calls.count(stage)==1 and (out/stage).is_dir()
    assert [s['id'] for s in pipeline['completed_stages']]==calls[:-1]
    assert not pipeline['quality_approved'] and not pipeline['release_approved']


@pytest.mark.parametrize('name',['contacts','geometry_policy','engine','object_edit','actor'])
def test_changed_input_rejects_before_job_output(tmp_path,monkeypatch,name):
    recipe,source,*_=authored(tmp_path,True);value=read(recipe)
    path=source if name=='actor' else Path(value[name]['path']);path.write_bytes(path.read_bytes()+b'\n')
    mocked(monkeypatch,tmp_path/'job')
    with pytest.raises(ValueError):job.run(recipe,tmp_path/'job')
    assert not (tmp_path/'job').exists()


@pytest.mark.parametrize('fault',['unknown','extra','missing','missing-sha','bad-sha','boolean-path','extra-binding'])
def test_strict_recipe_contract_rejects(tmp_path,fault):
    recipe,*_=authored(tmp_path);value=read(recipe)
    if fault=='unknown':value['schema']='other'
    elif fault=='extra':value['automatic_quality_approval']=True
    elif fault=='missing':value.pop('geometry_policy')
    elif fault=='missing-sha':value['engine'].pop('sha256')
    elif fault=='bad-sha':value['engine']['sha256']='wrong'
    elif fault=='boolean-path':value['engine']['path']=True
    else:value['engine']['guess']=True
    save(recipe,value)
    with pytest.raises(ValueError):job.validated(recipe)


def test_busy_worker_rejects_without_output_or_stage(tmp_path,monkeypatch):
    recipe,*_=authored(tmp_path);out=tmp_path/'job';mocked(monkeypatch,out)
    monkeypatch.setattr(job,'worker_busy',lambda:True)
    with pytest.raises(ValueError,match='worker is active'):job.run(recipe,out)
    assert not out.exists()


@pytest.mark.parametrize('fault',['input','archive','snapshot','saved-result','replay-binding','replay-decision','between-stage-worker'])
def test_mid_job_changes_fail_with_evidence_retained(tmp_path,monkeypatch,fault):
    recipe,_,path,*_=authored(tmp_path);out=tmp_path/'job';calls=mocked(monkeypatch,out)
    original=job.contact_run
    def tampered(path,folder):
        result=original(path,folder)
        if fault=='input':path.write_bytes(path.read_bytes()+b'\n')
        elif fault=='archive':(out/'implementation/native_scene_authoring_job.py').write_bytes(b'changed')
        elif fault=='snapshot':next((out/'input').iterdir()).write_bytes(b'changed')
        elif fault=='saved-result':save(folder/'result.json',dict(status='complete',passed=True))
        elif fault=='between-stage-worker':monkeypatch.setattr(job,'worker_busy',lambda:True)
        return result
    monkeypatch.setattr(job,'contact_run',tampered)
    if fault in ('replay-binding','replay-decision'):
        original_replay=job.replay_run
        def bad_replay(*args):
            result=original_replay(*args)
            if fault=='replay-binding':result['combined_files_sha256'][str(out/'combined-engine/result.json')]='0'*64
            else:result['recorded_sampled_conditions_pass']=False
            save(args[-1]/'result.json',result);return result
        monkeypatch.setattr(job,'replay_run',bad_replay)
    with pytest.raises(ValueError):job.run(recipe,out)
    assert read(out/'pipeline.json')['status']=='failed' and (out/'source-contacts/result.json').exists()
    assert not (out/'result.json').exists()


def test_plan_never_overwrites_an_existing_recipe(tmp_path):
    recipe,_,path,pp,engine,_=authored(tmp_path);before=sha256(recipe)
    with pytest.raises(ValueError,match='Fresh'):job.plan(path,pp,engine,recipe)
    assert sha256(recipe)==before


def test_invalid_edit_is_not_silently_dropped_from_plan(tmp_path):
    recipe,_,path,pp,engine,rp=authored(tmp_path);value=read(rp);value['maximum_translation_m']=True;save(rp,value)
    output=tmp_path/'new.json'
    with pytest.raises(ValueError):job.plan(path,pp,engine,output,rp)
    assert not output.exists()


def test_snapshot_failure_keeps_failed_startup_record(tmp_path,monkeypatch):
    recipe,*_=authored(tmp_path);out=tmp_path/'job';calls=mocked(monkeypatch,out)
    original=job.shutil.copyfile
    def bad_copy(source,dest):
        result=original(source,dest)
        if Path(dest).parent.name=='input':Path(dest).write_bytes(b'changed fixture snapshot')
        return result
    monkeypatch.setattr(job.shutil,'copyfile',bad_copy)
    with pytest.raises(ValueError,match='snapshot changed'):job.run(recipe,out)
    assert calls==[] and read(out/'pipeline.json')['status']=='failed'
    assert read(out/'pipeline.json')['completed_stages']==[]


def test_nonterminal_stage_is_never_promoted(tmp_path,monkeypatch):
    recipe,*_=authored(tmp_path);out=tmp_path/'job';calls=mocked(monkeypatch,out)
    def pending(path,folder):
        folder.mkdir();result=dict(status='processing',passed=False);save(folder/'result.json',result);return result
    monkeypatch.setattr(job,'contact_run',pending)
    with pytest.raises(ValueError,match='Nonterminal'):job.run(recipe,out)
    assert calls==[] and read(out/'pipeline.json')['status']=='failed'
    assert read(out/'source-contacts/result.json')['status']=='processing'


def test_all_real_numeric_components_with_only_engine_execution_mocked(tmp_path,monkeypatch):
    from test_native_object_scene_engine import producers
    path,pp,_,_=producers(tmp_path,monkeypatch)
    recipe=tmp_path/'authoring.json';job.plan(path,pp,tmp_path/'fixture-engine',recipe)
    # producers patches subprocess.run only, and isolates the synthetic worker lock.
    # Contact, saved GLB export, common clocks, imported skin reconstruction,
    # complete geometry and replay execute their real Python implementations.
    out=tmp_path/'job';result=job.run(recipe,out)
    assert result['sampled_conditions_pass'] and result['source_contact_conditions_pass']
    assert result['samples']==read(out/'combined-engine/result.json')['samples']
    assert read(out/'objects-engine/result.json')['modes']=={'default-import':False,'native-authoring':True}
    assert read(out/'replay/result.json')['all_replayed_observations_exact']
    assert not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('fault',['previous-stage','proposal','proposal-receipt'])
def test_completed_stage_and_derived_edit_bindings_cannot_drift(tmp_path,monkeypatch,fault):
    recipe,*_=authored(tmp_path,True);out=tmp_path/'job';mocked(monkeypatch,out)
    if fault=='proposal-receipt':
        original=job.fit_run
        def bad_fit(*args):
            result=original(*args);result['proposal_contacts_sha256']='0'*64;save(args[-1]/'result.json',result);return result
        monkeypatch.setattr(job,'fit_run',bad_fit)
    else:
        original=job.asset_run
        def bad_asset(path,folder):
            result=original(path,folder)
            changed=out/'source-contacts/result.json' if fault=='previous-stage' else path
            changed.write_bytes(changed.read_bytes()+b'\n');return result
        monkeypatch.setattr(job,'asset_run',bad_asset)
    with pytest.raises(ValueError):job.run(recipe,out)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()
