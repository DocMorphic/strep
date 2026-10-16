"""Pinned reusable paired fitting retains source contracts and failure evidence."""
from pathlib import Path
from types import SimpleNamespace
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_contact_objectives import separated
from native_interval_pair_fit_job import inputs,run,position_rows,SCHEMA
from native_scene_geometry import policy_for
from strep import read,save,sha256


def recipe(models,folder):
    model=models['A'];base=model.producer.parent.parent
    cp=next(Path(p) for p,h in model.pins.items() if h==model.digest)
    pin=lambda p:dict(path=str(p),sha256=sha256(p))
    times=policy_for(model.policy,model.scene,model.digest)[0];sample=int(np.flatnonzero(times==model.clock[3])[0])
    value=dict(schema=SCHEMA,contacts=pin(cp),geometry=pin(base/'geometry.json'),
        actors={n:dict(request=pin(m.producer.parent/'authoring.json'),controls=pin(m.producer.parent/'zero.npz'),active_keys=m.active.tolist()) for n,m in models.items()},
        surface_samples=[sample],surface_seed=137,trust=.1,difference_step=.001,contact_reserve_m=.0005,maximum_nonzeros=6000000)
    path=folder/'recipe.json';save(path,value);return path,value


def test_position_reserves_do_not_change_speed_or_unavailable_rate_rows():
    data=[dict(entry=dict(authored=dict(reduction='individual'),ids=[1,2]),times=[0,1,2],populations=[dict(times_s=[0]),dict(times_s=[0,1,2])]),
          dict(entry=dict(authored=dict(reduction='centroid'),ids=[1,2,3]),times=[0,1],populations=[])]
    pair=SimpleNamespace(names=['A'],models={'A':SimpleNamespace(contact_rows=data)},contact_caps=np.ones(13))
    np.testing.assert_array_equal(position_rows(pair),[0,1,2,3,4,5,11,12])
    pair.contact_caps=np.ones(14)
    with pytest.raises(ValueError,match='layout'):position_rows(pair)


@pytest.mark.parametrize('fault',['hash','nonzero','boolean-key','noncontiguous','duplicate-sample','reserve','trust','budget','unknown-field','actor-path','seed'])
def test_invalid_recipe_rejects_before_output_creation(separated,tmp_path,fault):
    models,_=separated;path,value=recipe(models,tmp_path);value=copy.deepcopy(value)
    if fault=='hash':value['contacts']['sha256']='0'*64
    elif fault=='nonzero':
        m=models['A'];p=tmp_path/'not-zero.npz';np.savez_compressed(p,times_s=m.clock,controls=np.ones_like(m.seed));value['actors']['A']['controls']=dict(path=str(p),sha256=sha256(p))
    elif fault=='boolean-key':value['actors']['A']['active_keys']=[True,4]
    elif fault=='noncontiguous':value['actors']['A']['active_keys']=[2,4]
    elif fault=='duplicate-sample':value['surface_samples']*=2
    elif fault=='reserve':value['contact_reserve_m']=-1
    elif fault=='trust':value['trust']=True
    elif fault=='budget':value['maximum_nonzeros']=6000001
    elif fault=='actor-path':value['actors']['../elsewhere']=value['actors'].pop('A')
    elif fault=='seed':value['surface_seed']=True
    else:value['approve']=True
    save(path,value);output=tmp_path/'output'
    with pytest.raises(ValueError):inputs(path,output)
    assert not output.exists()


def test_actual_paired_job_retains_complete_source_norms_and_never_approves(separated,tmp_path):
    import trimesh
    models,_=separated;path,value=recipe(models,tmp_path);before={p:sha256(p) for m in models.values() for p in m.pins}
    rng_before=copy.deepcopy(trimesh.util.random_generator().bit_generator.state)
    output=tmp_path/'fit';result=run(path,output)
    assert trimesh.util.random_generator().bit_generator.state==rng_before
    assert result['status']=='complete' and result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert result['controls']==sum(m.size for m in models.values()) and read(output/'pipeline.json')['status']=='complete'
    meta=read(output/'linearization.json');n=meta['native_rows'];c=meta['contact_rows']
    with np.load(output/'start-observations.npz') as original,np.load(output/'affine-observations.npz') as affine:
        for key in ['vectors','caps','scales']:np.testing.assert_array_equal(affine[key][:n],original['native_'+key])
        np.testing.assert_allclose(affine['caps'][n:n+c],original['contact_caps']-.0005,atol=0,rtol=0)
    assert all(sha256(p)==h for p,h in before.items())
    if result['candidate_contacts']:
        assert result['decoded_native_floor_geometry_pending'] and (output/'proposed-direction.npz').exists()
    else:assert not result['decoded_native_floor_geometry_pending']
    with pytest.raises(ValueError,match='fresh'):run(path,output)


def test_infeasible_iterate_is_saved_before_rejection_even_with_solved_status(separated,tmp_path,monkeypatch):
    import native_interval_pair_fit_job as module
    models,_=separated;path,_=recipe(models,tmp_path)
    monkeypatch.setattr(module,'direction',lambda system,jac,value,*args,**kwargs:(np.zeros_like(value),dict(status='Solved',test_injected=True)))
    result=run(path,tmp_path/'fit');assert not result['affine_pass'] and result['candidate_contacts'] is None
    assert (tmp_path/'fit/proposed-direction.npz').is_file() and not (tmp_path/'fit/probe-00').exists()
    assert not read(tmp_path/'fit/affine-postcheck.json')['passed']


def test_feasible_export_remains_unselected_until_independent_validation(tmp_path,monkeypatch):
    import native_interval_pair_fit_job as module
    from test_native_pair_key_guides import make_inputs
    source=tmp_path/'source';source.mkdir();models,_=make_inputs(source);path,_=recipe(models,tmp_path)
    monkeypatch.setattr(module,'direction',lambda system,jac,value,*args,**kwargs:(np.zeros_like(value),dict(status='Solved',test_injected=True)))
    result=run(path,tmp_path/'fit')
    assert result['affine_pass'] and result['decoded_authored_contacts_pass'] and result['decoded_native_floor_geometry_pending']
    assert result['original_selected'] and not result['quality_approved']
    assert Path(result['candidate_contacts']).is_file() and (tmp_path/'fit/proposed-direction.npz').is_file()


def test_source_change_between_validation_and_loading_keeps_the_original_pin(separated,tmp_path,monkeypatch):
    import native_interval_pair_fit_job as module
    models,_=separated;path,value=recipe(models,tmp_path)
    declaration=tmp_path/'actor.json';save(declaration,read(value['actors']['A']['request']['path']))
    expected=sha256(declaration);value['actors']['A']['request']=dict(path=str(declaration),sha256=expected);save(path,value)
    original=module.KeyIntervalModel.from_inputs;calls=[]
    def changed(**kwargs):
        if not calls:
            data=read(declaration);data['maximum_joint_displacement_m']*=.9;save(declaration,data)
            assert kwargs['expected_sha256']['request']==expected
        calls.append(True);return original(**kwargs)
    monkeypatch.setattr(module.KeyIntervalModel,'from_inputs',changed)
    with pytest.raises(ValueError,match='bindings'):run(path,tmp_path/'fit')
    assert calls and not (tmp_path/'fit/result.json').exists()
