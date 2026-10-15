"""Unit-aware hard recourse and complete real native-export/history replay."""
from pathlib import Path
import copy
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_scene_conic import direction
from native_key_cached_recourse import validate,search_model,probe_label,replay_history,attempt
from native_key_interval_restoration import validate as validate_recipe,SCHEMA,run,retain
from audit_native_key_restoration import run as replay
from strep import read,save,sha256
from test_native_affine_key_pose import affine_setup


def config(**changes):
    return dict(attempts_per_iteration=1,trust=1e-5,normalized_reserve=1e-4,maximum_failed_rows=1,**changes)


@pytest.mark.parametrize('key,value',[('attempts_per_iteration',True),('attempts_per_iteration',5),
    ('maximum_failed_rows',0),('maximum_failed_rows',65),('trust',True),('trust',float('nan')),
    ('trust',.00101),('normalized_reserve',0),('normalized_reserve',.011),('normalized_reserve',float('inf'))])
def test_invalid_repair_budget_cannot_become_unbounded_or_relax_acceptance(key,value):
    value_config=config();value_config[key]=value
    with pytest.raises(ValueError):validate(value_config,.02)


def test_repair_trust_cannot_exceed_primary_trust_or_accept_extra_keys():
    with pytest.raises(ValueError):validate(config(),1e-6)
    value=config();value['acceptance_tolerance']=.1
    with pytest.raises(ValueError):validate(value,.02)


def test_mixed_units_scale_only_the_search_reserve_and_keep_every_row():
    caps=np.array([1.,.5,10.]);scales=np.array([1.,.5,100.])
    before=dict(norms=NormRows([[.2,0,0],[.9,0,0],[12.,0,0]],caps,scales))
    after=dict(norms=NormRows([[.3,0,0],[.90001,0,0],[12.00001,0,0]],caps,scales))
    c=config();c['maximum_failed_rows']=2
    model,details=search_model(before,after,1,c)
    assert details['violating_rows']==[1,2] and details['native_rows']==3
    np.testing.assert_array_equal(model.vectors,after['norms'].vectors)
    np.testing.assert_allclose(model.caps,[1.,.9-1e-4*.5,12.-1e-4*100.],atol=0,rtol=0)
    np.testing.assert_array_equal(before['norms'].caps,caps);np.testing.assert_array_equal(after['norms'].caps,caps)
    assert model.caps[0]==caps[0]  # Edit/contact limits are never rebased.
    _,skipped=search_model(before,after,1,config());assert not skipped['eligible']


def test_all_native_rows_stay_hard_during_actual_repair_solve():
    before=dict(norms=NormRows([[0,0,0],[.9,0,0],[.8,0,0]],[1.,.5,.5],[1.,.5,.5]))
    after=dict(norms=NormRows([[0,0,0],[.90001,0,0],[.7,0,0]],[1.,.5,.5],[1.,.5,.5]))
    c=config();c['trust']=.001
    model,details=search_model(before,after,1,c)
    jac=sparse.csc_matrix(([1.,1.],([3,6],[0,0])),shape=(9,1))
    delta,info=direction(model,jac,np.zeros(1),np.array([-1.]),np.array([1.]),c['trust'],hard_rows=3)
    assert delta is not None and info['protected_norm_rows']==3
    assert np.all(model.residual(jac,delta)<=1e-8)
    assert np.linalg.norm(after['norms'].vectors[1])>.9
    assert np.linalg.norm(after['norms'].vectors[1]+np.array([delta[0],0,0]))<=.9


@pytest.mark.parametrize('label',['../1-0-repair','1-0-repair/other','-1-0','1--0','1-0-repair-0','1-0-repair-extra','01-0'])
def test_probe_label_cannot_escape_or_ambiguously_number_attempts(label):assert not probe_label(label)


@pytest.fixture(scope='module')
def exported(tmp_path_factory):
    folder=tmp_path_factory.mktemp('cached-native');_,scene,contacts,policy,authoring=affine_setup(folder)
    paths=dict(contacts=contacts,geometry=folder/'geometry.json',request=folder/'authoring.json',controls=folder/'controls.npz')
    save(paths['geometry'],policy);save(paths['request'],authoring)
    clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(3,'rotation'))
    np.savez_compressed(paths['controls'],times_s=clock,controls=np.zeros((len(clock),1,3)))
    declaration=dict(schema=SCHEMA,seed={k:dict(path=p.name,sha256=sha256(p)) for k,p in paths.items()},
        active_keys=[3,4,5],iterations=1,trust=.01,difference_step=.001,backoffs=2,maximum_seconds=60.,native_recourse=config())
    path=folder/'recipe.json';save(path,declaration);output=folder/'job';result=run(path,output)
    return output,path,result


def test_opt_in_passing_native_asset_has_no_invented_repairs_and_replays(exported,tmp_path):
    output,path,result=exported
    assert result['sampled_conditions_pass'] and result['history']==[]
    proof=replay(output,tmp_path/'replay',sha256(output/'result.json'),sha256(output/'request.json'))
    assert proof['retention_history_replayed'] and not proof['optimizer_executed']
    assert not proof['release_approved'] and not proof['quality_approved']


def history_fixture(tmp_path):
    """Decoded-state stand-ins isolate history tampering from shared geometry math."""
    class Problem:
        lower=np.array([-1.]);upper=np.array([1.]);edit_count=0
    def state(label,value,vector,accepted):
        return dict(record=dict(label=label,controls=[value]),norms=NormRows([[vector,0,0]],[.5],[1.]),accepted=accepted)
    fresh={'start':state('start',0.,.9,False),'1-0':state('1-0',.01,.90001,False),
        '1-0-repair':state('1-0-repair',.00999,.89999,True),'final':state('final',.00999,.89999,True)}
    c=config();recipe=dict(iterations=1,backoffs=2,native_recourse=c)
    path=tmp_path/'iterations/1';path.mkdir(parents=True);np.savez_compressed(path/'direction.npz',delta=[.01])
    sparse.save_npz(path/'affine-jacobian.npz',sparse.csc_matrix([[1.],[0.],[0.]]))
    repair=path/'repair-0';repair.mkdir();save(repair/'solver.json',dict(status='Solved'))
    d=np.array([-1e-5]);expected=np.array([.01])+d
    fresh['1-0-repair']['record']['controls']=expected.tolist();fresh['final']['record']['controls']=expected.tolist()
    np.savez_compressed(repair/'controls.npz',before=[.01],raw_delta=d,delta=d,after=expected)
    _,details=search_model(fresh['start'],fresh['1-0'],0,c)
    attempt=dict(**details,anchor_label='start',candidate_label='1-0',affine_jacobian_sha256=sha256(path/'affine-jacobian.npz'),
        solver_sha256=sha256(repair/'solver.json'),solver_status='Solved',controls_sha256=sha256(repair/'controls.npz'),label='1-0-repair',accepted=True)
    save(repair/'attempt.json',attempt)
    history=[dict(iteration=1,accepted_fraction=1.,probes=[dict(label='1-0',fraction=1.,accepted=False,recourse=[attempt])],solver_status='Solved',selected_label='1-0-repair')]
    return Problem(),recipe,fresh,history,repair


def test_rejected_primary_and_accepted_repair_are_distinct_replay_decisions(tmp_path):
    problem,recipe,fresh,history,_=history_fixture(tmp_path)
    value=replay_history(problem,recipe,tmp_path,history,fresh,[0.],lambda a,b:b['accepted'])
    np.testing.assert_array_equal(value,fresh['final']['record']['controls'])
    assert history[0]['probes'][0]['accepted'] is False


def test_failed_cached_solver_is_preserved_without_inventing_an_export(tmp_path):
    problem,recipe,fresh,history,path=history_fixture(tmp_path)
    before=fresh['start'];candidate=fresh['1-0'];folder=path.parent
    np.savez_compressed(folder/'affine-system.npz',value=before['record']['controls'],vectors=before['norms'].vectors,
        caps=before['norms'].caps,scales=before['norms'].scales)
    sparse.save_npz(folder/'affine-jacobian.npz',sparse.csc_matrix((3,1)))
    result,repaired=attempt(problem,before,candidate,folder,folder/'fixed-conflict',recipe['native_recourse'])
    assert result['solver_status']=='FixedProtectedConflict' and repaired is None
    assert result['label'] is None and result['controls_sha256'] is None and not result['accepted']
    assert read(folder/'fixed-conflict/attempt.json')==result
    assert not (folder/'fixed-conflict/controls.npz').exists()


def test_successful_cached_solve_cannot_bypass_full_geometry_retention(tmp_path,monkeypatch):
    from test_native_key_interval_restoration import observed,geometry
    import native_key_interval_restoration as restoration
    problem,recipe,fresh,history,path=history_fixture(tmp_path)
    before=fresh['start'];candidate=fresh['1-0'];folder=path.parent
    before.update(observed(geometry((.005,.002)),rate=2.))
    before['record'].update(label='start',controls=[0.])
    np.savez_compressed(folder/'affine-system.npz',value=before['record']['controls'],vectors=before['norms'].vectors,
        caps=before['norms'].caps,scales=before['norms'].scales)
    checked=[]
    def decoded(p,value,output):
        checked.append(output);result=observed(geometry((.006,.002)),rate=1.)
        result['record'].update(label=output.name,controls=value.tolist());return result
    monkeypatch.setattr(restoration,'evaluate',decoded)
    c=recipe['native_recourse'].copy();c['trust']=.001
    result,repaired=attempt(problem,before,candidate,folder,folder/'geometry-rejected',c)
    assert result['solver_status'] in ('Solved','AlmostSolved') and repaired is not None and checked
    assert result['accepted'] is False and result['label']=='1-0-repair'
    assert (folder/'geometry-rejected/controls.npz').exists()


def test_failed_repair_can_be_followed_by_an_ordinary_accepted_backoff(tmp_path):
    problem,recipe,fresh,history,path=history_fixture(tmp_path)
    repair=history[0]['probes'][0]['recourse'][0];repair['accepted']=False;save(path/'attempt.json',repair)
    fresh['1-0-repair']['accepted']=False
    fresh['1-1']=copy.deepcopy(fresh['final']);fresh['1-1']['record'].update(label='1-1',controls=[.005])
    fresh['final']['record']['controls']=[.005]
    history[0]['probes'].append(dict(label='1-1',fraction=.5,accepted=True,recourse=[]))
    history[0].update(selected_label='1-1',accepted_fraction=.5)
    value=replay_history(problem,recipe,tmp_path,history,fresh,[0.],lambda a,b:b['accepted'])
    np.testing.assert_array_equal(value,[.005])


def test_continuation_recipe_validates_the_same_optional_repair_budget():
    from native_key_continuation_job import validate as check,SCHEMA as continuation_schema
    parent=dict(path='parent',result_sha256='a'*64,request_sha256='b'*64,replay='proof.json',replay_sha256='c'*64)
    recipe=dict(schema=continuation_schema,parent=parent,iterations=1,trust=.01,difference_step=.001,
        backoffs=2,maximum_seconds=60.,native_recourse=config())
    assert check(recipe)==recipe
    recipe['native_recourse']['trust']=.02
    with pytest.raises(ValueError):check(recipe)


@pytest.mark.parametrize('fault',['selected','acceptance','budget','source','delta','omitted','extra','reserve','solver'])
def test_repair_replay_rejects_tampered_choices_controls_budgets_and_limits(tmp_path,fault):
    problem,recipe,fresh,history,path=history_fixture(tmp_path);attempt=history[0]['probes'][0]['recourse'][0]
    if fault=='selected':history[0]['selected_label']='1-0'
    elif fault=='acceptance':attempt['accepted']=False;save(path/'attempt.json',attempt)
    elif fault=='budget':recipe['native_recourse']['attempts_per_iteration']=0
    elif fault=='source':attempt['candidate_label']='start';save(path/'attempt.json',attempt)
    elif fault=='delta':np.savez_compressed(path/'controls.npz',before=[.01],raw_delta=[-.1],delta=[-.1],after=[-.09]);attempt['controls_sha256']=sha256(path/'controls.npz');save(path/'attempt.json',attempt)
    elif fault=='omitted':fresh.pop('1-0-repair')
    elif fault=='extra':fresh['2-0']=copy.deepcopy(fresh['1-0'])
    elif fault=='reserve':recipe['native_recourse']['normalized_reserve']*=2
    else:save(path/'solver.json',dict(status='PrimalInfeasible'))
    with pytest.raises((ValueError,AssertionError)):replay_history(problem,recipe,tmp_path,history,fresh,[0.],lambda a,b:b['accepted'])
