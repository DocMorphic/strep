"""Passing-pair guidance never bypasses full original/incumbent protections."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
import trimesh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import native_mesh_prop_scene_fit_v2 as module
from native_mesh_prop_scene_fit_v2 import signed_upper,PairGuards,passing_entities,optimize,fit,compare
from native_mesh_prop_scene_fit import SceneGuidance,signed
from native_mesh_prop_pose import GripPoseEdit,conditions,metrics
from strep import read,save,sha256
from test_native_mesh_prop_pose import setup
from test_native_mesh_prop_scene import cube


def warm_file(tmp_path,pp,controls=None):
    path=tmp_path/'warm.json';save(path,dict(schema='strep-prop-source-relative-warm-start-v1',permissions_sha256=sha256(pp),controls=[0.,0,.5*(1-1e-12),1.] if controls is None else controls));return path


def test_upper_bound_is_conservative_against_complete_queries(tmp_path):
    asset=cube(tmp_path/'box.glb');mesh=trimesh.Trimesh(asset.vertices_m,asset.faces,process=False);rng=np.random.default_rng(65)
    for points in [rng.uniform(-2,2,(128,3)),rng.uniform(-.08,.08,(12,3)),np.array([[.1+1e-9,0,0],[.1-1e-9,0,0]])]:
        exact=float((signed(mesh,points)+1e-8).max());assert signed_upper(mesh,points,1e-8)>=exact-1e-13


@pytest.mark.parametrize('points,padding',[(np.empty((0,3)),1e-8),(np.array([[True,False,True]]),1e-8),(np.array([[np.nan,0,0]]),1e-8),(np.zeros((2,2)),1e-8),(np.zeros((1,3)),0),(np.zeros((1,3)),True)])
def test_invalid_upper_inputs_reject(tmp_path,points,padding):
    asset=cube(tmp_path/'box.glb');mesh=trimesh.Trimesh(asset.vertices_m,asset.faces,process=False)
    with pytest.raises(ValueError):signed_upper(mesh,points,padding)


def test_guard_distinguishes_repaired_pose_from_colliding_pose(tmp_path):
    pp,policy_path,*_=setup(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));reference=[0.,0,.5*(1-1e-12),1.];guards=PairGuards(guide,['actor:A'],reference)
    assert np.all(guards.upper(reference)<=guards.limits) and np.any(guards.upper([0.,0,0,1])>guards.limits)
    assert guards.describe()['active_entities']==['actor:A'] and not guards.describe()['author_permissions_changed']


@pytest.mark.parametrize('names',[['missing'],['actor:A','actor:A'],[False]])
def test_unknown_duplicate_or_nonstring_guards_reject(tmp_path,names):
    pp,policy_path,*_=setup(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path))
    with pytest.raises(ValueError):PairGuards(guide,names,[0.,0,0,0])


def test_empty_guard_population_is_explicit_and_finite(tmp_path):
    pp,policy_path,*_=setup(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));guards=PairGuards(guide,[],[0.,0,0,0])
    assert guards.upper([0.,0,0,0]).shape==(0,) and guards.describe()['sampled_upper_limits_m']==[]


def test_pair_selection_requires_unique_complete_key_decisions():
    row=dict(time_s=1.,mesh_pairs=[dict(left=['actor','A'],right=['prop','box'],passed=False),dict(left=['actor','B'],right=['prop','box'],passed=True),dict(left=['prop','other'],right=['prop','box'],passed=True)])
    report=dict(samples=[row]);assert passing_entities(report,'box',1.)==['actor:B','prop:other']
    with pytest.raises(ValueError):passing_entities(report,'box',.5)
    with pytest.raises(ValueError):passing_entities(dict(samples=[row,row]),'box',1.)
    row['mesh_pairs'].append(copy.deepcopy(row['mesh_pairs'][1]))
    with pytest.raises(ValueError):passing_entities(report,'box',1.)


def geometry_flags(a,b):
    pairs=[dict(left=['actor',name],right=['prop','box'],passed=passed,surface=dict(records=[] if passed else [dict(kind='crossing')]),vertex_containment=[]) for name,passed in [('A',a),('B',b)]]
    return dict(samples=[dict(time_s=1.,base_scene=dict(actor_objects=[],actor_pairs=[],world_planes=[]),mesh_pairs=pairs,mesh_primitive_pairs=[],mesh_world_planes=[],passed=bool(a and b))])


def test_incumbent_repair_cannot_be_traded_for_another_repair():
    before=geometry_flags(False,False);incumbent=geometry_flags(True,False);candidate=geometry_flags(False,True)
    original=conditions(before);warm=conditions(incumbent);protected={k:original[k] or warm[k] for k in original}
    row=compare(dict(sampled_pose_permissions_pass=True,all_declared_point_contacts_pass=True,sampled_geometry_pass=False),candidate,original,protected,metrics(before),metrics(incumbent))
    assert row['new_failed_original_conditions']==0 and row['new_failed_geometry_conditions']==1 and row['collision_metrics_no_worse_than_source'] and not row['admissible_for_comparison']


def test_optimizer_budget_without_feasible_guard_does_not_approve_fallback(tmp_path):
    pp,policy_path,*_=setup(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));guards=PairGuards(guide,['actor:A'],[0.,0,.5*(1-1e-12),1.])
    result=optimize(guide,[0.,0,0,1.],guards,tmp_path/'guidance',maximum_evaluations=1)
    assert result['stop_reason']=='evaluation_limit' and result['unique_guidance_evaluations']==1 and not result['sampled_guard_feasible_found'] and result['best_guidance_energy'] is None and not result['geometry_approved']


def test_cached_optimizer_preserves_source_limits_and_explicit_counts(tmp_path):
    pp,policy_path,*_=setup(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));initial=[0.,0,.25,1.];guards=PairGuards(guide,[],initial)
    result=optimize(guide,initial,guards,tmp_path/'guidance',maximum_evaluations=24,maximum_iterations=4)
    assert result['best_guidance_energy']<result['starting_energy'] and result['measure_calls']>=result['unique_guidance_evaluations'] and result['sampled_guard_feasible_found']
    assert guide.edit.evaluate(result['best_guidance_controls'])['report']['native_pose_permissions_pass'] and result['clearance_fraction_fixed']==1. and not result['quality_approved']


def test_known_repair_gets_all_export_checks_and_protected_identities(tmp_path):
    pp,policy_path,path,spec,_=setup(tmp_path);pins=GripPoseEdit(pp).inputs;warm=warm_file(tmp_path,pp);result=fit(pp,policy_path,warm,tmp_path/'fit',maximum_evaluations=1)
    assert result['sampled_feasible_probe']==1 and result['initial_qualified'] and result['incumbent_repairs_protected']==2 and result['geometry_times']==3
    assert read(tmp_path/'fit/pair-guards.json')['reference_kind']=='qualified-initial' and read(tmp_path/'fit/pair-guards.json')['active_entities']==['actor:A']
    assert read(tmp_path/'fit/probe-001/geometry.json')['sampled_conditions_pass'] and not result['source_rebased'] and not result['character_motion_edited'] and not result['release_approved']
    exported=read(tmp_path/'fit/probe-001/mesh-scene.json');assert exported['props']['crate']['keyframes'][0]==spec['props']['crate']['keyframes'][0] and all(sha256(p)==d for p,d in pins.items())


def test_missing_key_is_added_without_dropping_requested_times(tmp_path):
    pp,policy_path,*_=setup(tmp_path);policy=read(policy_path);policy['clock']['times_s']=[0.,2.];save(policy_path,policy);digest=sha256(policy_path)
    result=fit(pp,policy_path,warm_file(tmp_path,pp),tmp_path/'fit',maximum_evaluations=1)
    inp=read(tmp_path/'fit/input.json');assert inp['requested_geometry_clock_s']==[0.,2.] and inp['geometry_clock_s']==[0.,1.,2.] and inp['edited_key_added_to_geometry_clock']
    assert result['geometry_times']==3 and result['sampled_feasible_probe']==1 and sha256(policy_path)==digest and read(tmp_path/'fit/effective-policy.json')['limits']==policy['limits']


def test_full_postcheck_rejects_optimizer_that_breaks_qualified_repair(tmp_path,monkeypatch):
    pp,policy_path,path,spec,permission=setup(tmp_path);spec['props']['bad']=copy.deepcopy(spec['props']['crate']);spec['props']['bad']['keyframes']=[dict(time_s=0.,translation_m=[10.,-1.,0],rotation_xyzw=[0,0,0,1])]
    save(path,spec);permission['mesh_scene_sha256']=sha256(path);save(pp,permission);policy=read(policy_path);policy['mesh_scene_sha256']=sha256(path);save(policy_path,policy)
    def injected(*args,**kwargs):
        folder=args[3];folder.mkdir();result=dict(unique_guidance_evaluations=0,stop_reason='injected-test-proposal',sampled_guard_feasible_found=True,best_guidance_controls=[0.,0,0,1.]);save(folder/'result.json',result);return result
    monkeypatch.setattr(module,'optimize',injected)
    result=fit(pp,policy_path,warm_file(tmp_path,pp),tmp_path/'fit',backtrack_steps=1)
    row=result['history'][2];assert result['initial_qualified'] and result['incumbent_repairs_protected']>0 and row['new_failed_original_conditions']==0 and row['new_failed_geometry_conditions']>0 and not row['admissible_for_comparison'] and result['best_admissible_probe']==1


@pytest.mark.parametrize('option,value',[('backtrack_steps',0),('backtrack_steps',13),('backtrack_steps',True),('maximum_evaluations',0),('maximum_evaluations',513),('maximum_iterations',0),('maximum_iterations',True)])
def test_bad_budgets_reject_before_any_output(tmp_path,option,value):
    pp,policy_path,*_=setup(tmp_path)
    with pytest.raises(ValueError):fit(pp,policy_path,warm_file(tmp_path,pp),tmp_path/'no',**{option:value})
    assert not (tmp_path/'no').exists()


def test_bad_native_start_rejects_before_any_output(tmp_path):
    pp,policy_path,*_=setup(tmp_path)
    with pytest.raises(ValueError):fit(pp,policy_path,warm_file(tmp_path,pp,[.8,.8,0,1.]),tmp_path/'no')
    assert not (tmp_path/'no').exists()
