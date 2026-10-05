"""Generated point-contact contracts, not anatomy or motion-quality evidence."""
import copy
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import native_transfer_calibration as calibration
import native_transfer_scene as bridge
import native_rig_transfer as transfer
from native_scene_contacts import SceneContacts
from strep import read,save,sha256
from test_native_transfer_scene import scene_fixture


def permissions(comparison,*,root=0.,calls=1800,starts=7):
    return dict(schema=calibration.SCHEMA,comparison=dict(path=str(comparison),sha256=sha256(comparison/'result.json')),
        actors=dict(A=dict(role_rotations_degrees=dict(LeftArm=15,LeftForeArm=15),
            maximum_root_offset_m=root,maximum_joint_displacement_m=.06)),
        search=dict(evaluations=210,calls=calls,seconds=120,starts=starts))


@pytest.fixture(scope='module')
def studies(tmp_path_factory):
    root=tmp_path_factory.mktemp('calibration');studies={}
    for name,options in [('small',dict(size=1.005,moving=True)),('large',dict(size=1.3,helpers=True,moving=True)),
        ('both',dict(both=True,moving=True))]:
        recipe=scene_fixture(root/name,**options);comparison=recipe.parent/'comparison';bridge.run(recipe,comparison)
        recipe=recipe.parent/'calibration.json';save(recipe,permissions(comparison))
        if name=='both':
            value=read(recipe);value['actors']['B']=copy.deepcopy(value['actors']['A'])
            value['actors']['B']['role_rotations_degrees']=dict(RightArm=15,RightForeArm=15)
            value['search'].update(evaluations=1,starts=1,calls=12);save(recipe,value)
        out=recipe.parent/'fit';result=calibration.run(recipe,out)
        studies[name]=(recipe,comparison,out,result)
    return studies


def test_serialized_correction_retains_every_original_target_and_limit(studies):
    recipe,comparison,out,result=studies['small']
    assert not read(comparison/'result.json')['candidate_contact_samples_pass']
    assert result['sampled_calibration_conditions_pass'] and result['candidate_contact_samples_pass']
    assert result['source_rates_pass'] and result['joint_displacement_pass']
    original=read(comparison/'contacts.json');changed=read(out/'contacts.json')
    assert changed['contacts']==original['contacts'] and changed['objects']==original['objects']
    assert {k:v for k,v in changed['actors']['A'].items() if k not in ('glb','sha256','animation_index')}=={
        k:v for k,v in original['actors']['A'].items() if k not in ('glb','sha256','animation_index')}
    assert changed['actors']['A']['animation_index']==1
    assert SceneContacts(changed,out).evaluate()[0]['passed']
    assert calibration.verify(out,sha256(out/'result.json'))==result
    assert all(result[k] is False for k in ('geometry_verified','surface_orientation_verified',
        'engine_playback_verified','quality_approved','release_approved'))
    assert result['whole_clip_boundary_poses_may_change'] and result['original_selected']


def test_large_rig_conditional_reach_conflict_skips_solver_and_export(studies):
    _,_,out,result=studies['large']
    assert result['status']=='incompatible_with_joint_bound' and not result['optimizer_started']
    rows=read(out/'preflight.json')['rows']
    assert any(r.get('conflict_verified') and r['contact']=='partner-initiated' for r in rows)
    assert all(not (out/p).exists() for p in ('search.json','contacts.json','observations.npz','transfer-A'))
    assert calibration.verify(out)==result


def test_both_editable_partners_do_not_claim_fixed_target_certificate(studies):
    _,_,out,result=studies['both']
    assert result['sampled_calibration_conditions_pass'] and (out/'transfer-B/character.glb').is_file()
    rows=read(out/'preflight.json')['rows']
    assert any(r['contact']=='partner' and r.get('reason','').startswith('Both sides editable') for r in rows)
    assert calibration.verify(out)==result


def test_profile_fk_agrees_with_original_native_transfer_evaluator(studies):
    recipe,comparison,_,_=studies['small'];problem=calibration.CalibrationProblem(comparison,read(recipe))
    for value in [np.zeros(problem.size),np.linspace(-.31,.28,problem.size)]:
        world=problem.worlds(value)['A'];profile=problem.profiles(value)['A'];a=problem.actors['A'];bound=a['inputs']
        sampler,sm,tm,skeleton,offset,_,_=bound[5]
        if np.any(value):offset=offset+np.asarray(profile.get('world_offset_m',[0,0,0]))-np.asarray(a['profile'].get('world_offset_m',[0,0,0]))
        expected=transfer.evaluate_transfer(bound[2],bound[3],sampler,sm,tm,skeleton,offset,profile,problem.times)[0]
        np.testing.assert_allclose(world,expected,atol=1e-12,rtol=0)


def test_root_and_rotation_coordinates_cannot_exceed_author_limits(studies):
    recipe,comparison,_,_=studies['small'];value=read(recipe);value['actors']['A']['maximum_root_offset_m']=.01
    p=calibration.CalibrationProblem(comparison,value);controls=np.full(p.size,20.)
    angles,root=p.decode(controls)['A'];assert np.linalg.norm(root)<.01
    assert np.all(np.linalg.norm(angles,axis=1)<np.deg2rad(15))
    before=p.actors['A']['profile'];after=p.profiles(controls)['A']
    assert {k:v for k,v in before.items() if k not in ('axis_alignment_xyzw','world_offset_m')}=={
        k:v for k,v in after.items() if k not in ('axis_alignment_xyzw','world_offset_m')}
    assert set(after['axis_alignment_xyzw'])-set(before.get('axis_alignment_xyzw',{}))<=set(value['actors']['A']['role_rotations_degrees'])
    for invalid in [np.zeros(p.size-1),np.full(p.size,np.nan),np.full(p.size,20.01)]:
        with pytest.raises(ValueError,match='coordinates'):p.decode(invalid)


def test_complete_touch_and_speed_clocks_and_old_target_clip_survive(studies):
    _,comparison,out,_=studies['small']
    with np.load(out/'observations.npz',allow_pickle=False) as saved:
        np.testing.assert_array_equal(saved['contact_0_times_s'],[.0853725])
        assert saved['contact_1_times_s'].dtype==np.dtype('float64')
    audit=read(out/'frame-audit.json')
    assert all(len(c['relative_speed_populations'])==12 for c in audit['contacts'][1:])
    bound=bridge.transfer_audit.bound_candidate(out/'transfer-A')
    assert transfer.preserves_target(bound[3],bound[7],bound[1]['target_mapping'])
    assert bound[7].document['animations'][0]==bound[3].document['animations'][0]
    assert sha256(out/'transfer-A/source.glb')==sha256(comparison/'input/transfers/A/source.glb')


def test_portable_replay_has_no_dependency_on_original_comparison(studies,tmp_path):
    _,_,out,result=studies['small'];moved=tmp_path/'portable';shutil.copytree(out,moved)
    recipe=read(moved/'recipe.json');assert Path(recipe['comparison']['path'])!=moved/'comparison'
    assert calibration.verify(moved,sha256(out/'result.json'))==result


@pytest.mark.parametrize('fault',['schema','extra','sha','actor','role','angle','root','joint','calls','starts','evaluations','seconds'])
def test_invalid_recipe_rejects_before_output(studies,tmp_path,fault):
    recipe,_,_,_=studies['small'];value=read(recipe)
    if fault=='schema':value['schema']='other'
    elif fault=='extra':value['geometry_verified']=True
    elif fault=='sha':value['comparison']['sha256']='0'*64
    elif fault=='actor':value['actors']['B']=value['actors'].pop('A')
    elif fault=='role':value['actors']['A']['role_rotations_degrees']['Unknown']=1
    elif fault=='angle':value['actors']['A']['role_rotations_degrees']['LeftArm']=45.1
    elif fault=='root':value['actors']['A']['maximum_root_offset_m']=.221
    elif fault=='joint':value['actors']['A']['maximum_joint_displacement_m']=True
    elif fault in ('calls','starts','evaluations'):value['search'][fault]=True
    else:value['search']['seconds']=float('nan')
    path=tmp_path/'invalid.json'
    # Deliberately malformed external JSON must reach the input validator;
    # the normal project writer correctly refuses NaN before writing it.
    path.write_text(json.dumps(value),encoding='utf8');out=tmp_path/'output'
    with pytest.raises((ValueError,IndexError)):calibration.run(path,out)
    assert not out.exists()


def test_complete_pose_budget_rejects_without_partial_calibration_cache(studies,monkeypatch):
    recipe,comparison,_,_=studies['small'];monkeypatch.setattr(calibration,'POSE_TRANSFORM_LIMIT',1)
    with pytest.raises(ValueError,match='no truncation'):calibration.CalibrationProblem(comparison,read(recipe))


@pytest.mark.parametrize('fault',['limit','object','placement','profile','controls','observations','method','quality','typed','missing','score'])
def test_rehashed_candidate_or_scope_changes_reject(studies,tmp_path,fault):
    _,_,original,_=studies['small'];out=tmp_path/'changed';shutil.copytree(original,out)
    if fault in ('limit','object','placement'):
        path=out/'contacts.json';value=read(path)
        if fault=='limit':value['contacts'][1]['limits']['position_m']=.003
        elif fault=='object':value['objects']['box']['keyframes'][0]['translation_m'][0]+=.01
        else:value['actors']['A']['placement']['translation_m'][0]+=.01
        save(path,value)
    elif fault=='profile':
        path=out/'A-profile.json';value=read(path);value['world_offset_m']=[.01,0,0];save(path,value)
    elif fault in ('controls','score'):
        path=out/'search.json';value=read(path)
        if fault=='controls':value['controls'][0]+=.01
        else:value['selected_score'][0]+=1
        save(path,value)
    elif fault=='observations':
        path=out/'observations.npz'
        with np.load(path,allow_pickle=False) as data:arrays={k:data[k].copy() for k in data.files}
        arrays['contact_0_candidate_effector_world_m'].flat[0]+=.001;np.savez_compressed(path,**arrays)
    elif fault=='method':(out/'implementation/native_transfer_calibration.py').write_text('changed',encoding='utf8')
    elif fault=='missing':(out/'preflight.json').unlink()
    result=read(out/'result.json')
    if fault=='quality':result['quality_approved']=True
    elif fault=='typed':result['sampled_calibration_conditions_pass']=1
    result['files_sha256']=calibration.payload_hashes(out);save(out/'result.json',result)
    with pytest.raises((ValueError,FileNotFoundError)):calibration.verify(out)


def test_shared_objective_call_budget_stops_all_starts_and_keeps_original(studies):
    recipe,comparison,_,_=studies['small'];value=read(recipe);value['search']['calls']=1
    problem=calibration.CalibrationProblem(comparison,value);controls,search=calibration.fit(problem)
    assert search['objective_calls']==1 and search['budget_exhausted']
    np.testing.assert_array_equal(controls,np.zeros(problem.size))
    assert len(search['starts'])==0


def test_search_evaluation_allocations_share_one_total_budget(studies,monkeypatch):
    recipe,comparison,_,_=studies['small'];value=read(recipe);value['search'].update(evaluations=11,starts=7,calls=20)
    problem=calibration.CalibrationProblem(comparison,value)
    from types import SimpleNamespace
    def exercise(fun,seed,**kwargs):
        fun(seed);return SimpleNamespace(nfev=kwargs['max_nfev'],status=0)
    monkeypatch.setattr(calibration,'least_squares',exercise)
    _,search=calibration.fit(problem)
    assert sum(s['evaluation_budget'] for s in search['starts'])==11
    assert search['objective_calls']==7 and not search['budget_exhausted']
