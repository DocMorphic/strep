"""Public explicit-source restoration, complete replay and verified continuation."""
import numpy as np
import pytest
from test_native_affine_key_pose import affine_setup
from native_key_interval_restoration import run,validate,SCHEMA
from audit_native_key_restoration import run as replay
from native_key_continuation_job import run as continue_job,SCHEMA as CONTINUE
from audit_native_key_continuation_job import run as replay_job
from strep import read,save,sha256


def recipe():
    return dict(schema=SCHEMA,seed={k:dict(path=k+'.json',sha256='a'*64) for k in ('contacts','geometry','request','controls')},
        active_keys=[3,4],iterations=1,trust=.01,difference_step=.001,backoffs=2,maximum_seconds=300.)


@pytest.mark.parametrize('fault',['both','neither','missing','extra','path','digest','hex'])
def test_exactly_one_complete_typed_source_form_required(fault):
    value=recipe()
    if fault=='both':value['producer']=dict(path='old',result_sha256='a'*64,request_sha256='b'*64)
    elif fault=='neither':value.pop('seed')
    elif fault=='missing':value['seed'].pop('controls')
    elif fault=='extra':value['seed']['new_caps']=dict(path='caps.json',sha256='a'*64)
    elif fault=='path':value['seed']['contacts']['path']=False
    elif fault=='digest':value['seed']['controls']['sha256']=False
    else:value['seed']['controls']['sha256']='z'*64
    with pytest.raises(ValueError):validate(value)


@pytest.fixture(scope='module')
def completed(tmp_path_factory):
    folder=tmp_path_factory.mktemp('seed-restoration');_,scene,contacts,policy,authoring=affine_setup(folder)
    paths=dict(contacts=contacts,geometry=folder/'geometry.json',request=folder/'authoring.json',controls=folder/'controls.npz')
    save(paths['geometry'],policy);save(paths['request'],authoring)
    clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(3,'rotation'))
    np.savez_compressed(paths['controls'],times_s=clock,controls=np.zeros((len(clock),1,3)))
    declaration=recipe();declaration['seed']={k:dict(path=p.name,sha256=sha256(p)) for k,p in paths.items()}
    path=folder/'recipe.json';save(path,declaration);output=folder/'job';run(path,output)
    proof=folder/'proof';replay(output,proof,sha256(output/'result.json'),sha256(output/'request.json'))
    return output,proof/'result.json',path


def test_seeded_command_and_auditor_keep_full_native_controls_and_original_caps(completed):
    output,proof,path=completed;result=read(output/'result.json');checked=read(proof)
    assert result['sampled_conditions_pass'] and result['history']==[] and result['all_original_caps_preserved']
    assert checked['retention_history_replayed'] and not checked['optimizer_executed']
    assert not result['quality_approved'] and not result['training_admitted'] and not result['release_approved']
    with np.load(output/'key-controls.npz') as data:
        assert set(data.files)=={'times_s','controls'} and not np.any(data['controls'])
    with np.load(output/'probes/final/observations.npz') as data:
        assert np.array_equal(data['source_world'],data['candidate_world'])


def test_seeded_parent_can_continue_with_complete_fresh_lineage(completed,tmp_path):
    producer,proof,_=completed
    parent=dict(path=str(producer),result_sha256=sha256(producer/'result.json'),request_sha256=sha256(producer/'request.json'),replay=str(proof),replay_sha256=sha256(proof))
    recipe_path=tmp_path/'continue.json';save(recipe_path,dict(schema=CONTINUE,parent=parent,iterations=1,trust=.01,difference_step=.001,backoffs=2,maximum_seconds=300.))
    output=tmp_path/'continuation';result=continue_job(recipe_path,output)
    assert result['sampled_conditions_pass'] and result['all_original_caps_preserved']
    checked=replay_job(output,tmp_path/'replay',sha256(output/'result.json'),sha256(output/'request.json'))
    assert checked['retention_history_replayed'] and checked['original_reference_unchanged']
    assert not checked['optimizer_executed'] and not checked['release_approved']


def test_changed_final_control_archive_cannot_replay(completed,tmp_path):
    producer,proof,_=completed;path=producer/'key-controls.npz';original=path.read_bytes()
    try:
        with np.load(path) as data:clock=data['times_s'];controls=data['controls'].copy()
        controls[3,0,0]=.001;np.savez_compressed(path,times_s=clock,controls=controls)
        with pytest.raises(AssertionError):replay(producer,tmp_path/'bad',sha256(producer/'result.json'),sha256(producer/'request.json'))
        assert not (tmp_path/'bad/result.json').exists()
    finally:path.write_bytes(original)


def test_input_digest_change_rejects_before_creating_job(completed,tmp_path):
    _,_,path=completed;value=read(path)
    for row in value['seed'].values():row['path']=str(path.parent/row['path'])
    value['seed']['controls']['sha256']='0'*64;bad=tmp_path/'bad.json';save(bad,value)
    with pytest.raises(ValueError,match='seed bindings'):run(bad,tmp_path/'job')
    assert not (tmp_path/'job').exists()
