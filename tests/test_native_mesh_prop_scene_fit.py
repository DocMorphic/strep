"""All-entity guidance is separate from original complete acceptance checks."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from native_mesh_prop_scene_fit import SceneGuidance,face_points,optimize,fit,signed,positive_signed
from native_mesh_prop_pose import GripPoseEdit
from strep import read,save,sha256
from test_native_mesh_prop_pose import setup
from test_native_mesh_prop_scene import cube


def make(tmp_path):
    pp,policy_path,path,spec,permission=setup(tmp_path)
    return pp,policy_path,path,spec,permission


def bind(pp,policy_path,path,spec,permission):
    save(path,spec);permission['mesh_scene_sha256']=sha256(path);save(pp,permission);policy=read(policy_path);policy['mesh_scene_sha256']=sha256(path);save(policy_path,policy)


def test_triangle_samples_include_vertices_edges_and_interior():
    v=np.array([[0.,0,0],[6,0,0],[0,3,0]])
    actual=face_points(v,np.array([[0,1,2]]))
    expected=np.array([[0.,0,0],[6,0,0],[0,3,0],[3,0,0],[3,1.5,0],[0,1.5,0],[2,1,0]])
    np.testing.assert_array_equal(actual,expected)


def test_both_actors_contribute_with_same_pose(tmp_path):
    pp,policy_path,path,spec,permission=make(tmp_path);actor_path=tmp_path/'contacts.json';actors=read(actor_path);actors['actors']['B']=copy.deepcopy(actors['actors']['A']);save(actor_path,actors);spec['actor_scene_sha256']=sha256(actor_path);bind(pp,policy_path,path,spec,permission)
    guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));result=guide.evaluate([0.,0,0,0]);terms={v['name']:v for v in result['terms']}
    assert terms['actor:A->prop']['positive_samples']>0
    for prefix in ['','prop->']:
        suffix='->prop' if not prefix else ''
        a,b=terms[prefix+'actor:A'+suffix],terms[prefix+'actor:B'+suffix]
        assert a['samples']==b['samples'] and a['mean_squared_scaled_residual']==b['mean_squared_scaled_residual']
    assert not result['geometry_approved'] and len(guide.summary['entities'])==2


def test_far_actor_is_skipped_only_by_complete_reachable_bounds(tmp_path):
    pp,policy_path,path,spec,permission=make(tmp_path);actor_path=tmp_path/'contacts.json';actors=read(actor_path);actors['actors']['B']=copy.deepcopy(actors['actors']['A']);actors['actors']['B']['placement']['translation_m']=[100.,0,0];save(actor_path,actors);spec['actor_scene_sha256']=sha256(actor_path);bind(pp,policy_path,path,spec,permission)
    guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));b=next(r for r in guide.summary['entities'] if r['name']=='actor:B')
    assert b['whole_bounds_disjoint'] and b['reachable_faces']==b['inverse_complete_prop_points']==0
    assert {v['name'] for v in guide.evaluate([0.,0,0,0])['terms']} >= {'actor:B->prop','prop->actor:B'}


def test_containing_other_prop_is_measured_even_without_nearby_faces(tmp_path):
    pp,policy_path,path,spec,permission=make(tmp_path);initial=GripPoseEdit(pp);container_path=tmp_path/'container.glb';asset=cube(container_path,extents=(4,4,4))
    spec['props']['container']=dict(glb=container_path.name,sha256=asset.source_sha256,geometry_sha256=asset.geometry_sha256,keyframes=[dict(time_s=0.,translation_m=initial._pivot.tolist(),rotation_xyzw=[0,0,0,1])]);bind(pp,policy_path,path,spec,permission)
    guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));summary=next(v for v in guide.summary['entities'] if v['name']=='prop:container')
    assert not summary['whole_bounds_disjoint'] and summary['reachable_faces']==0 and summary['inverse_complete_prop_points']>0
    term=next(v for v in guide.evaluate([0.,0,0,0])['terms'] if v['name']=='prop->prop:container')
    assert term['positive_samples']==term['samples'] and term['maximum_residual_m']>1.


def test_primitive_and_plane_residuals_preserve_full_prop_faces(tmp_path):
    pp,policy_path,path,spec,permission=make(tmp_path);edit=GripPoseEdit(pp);actor_path=tmp_path/'contacts.json';actors=read(actor_path)
    actors['objects']['block']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.3,.3,.3]),keyframes=[dict(time_s=0.,translation_m=edit._pivot.tolist(),rotation_xyzw=[0,0,0,1])]);save(actor_path,actors);spec['actor_scene_sha256']=sha256(actor_path);bind(pp,policy_path,path,spec,permission)
    guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));terms={v['name']:v for v in guide.evaluate([0.,0,0,0])['terms']}
    assert terms['primitive:block']['samples']==12 and terms['primitive:block']['positive_samples']>0
    assert terms['plane:floor']['samples']==8 and guide.summary['primitive_objects']==['block']


def test_reachable_sphere_contains_all_original_relative_trials(tmp_path):
    pp,policy_path,*_=make(tmp_path);edit=GripPoseEdit(pp);guide=SceneGuidance(edit,read(policy_path));rng=np.random.default_rng(583)
    for _ in range(40):
        xyz=rng.normal(size=3);xyz=xyz/np.linalg.norm(xyz)*rng.uniform(0,.99);response=edit.evaluate(np.r_[xyz,rng.random()]);vertices=guide.asset.vertices_m@response['rotation_matrix'].T+response['position_m']
        assert np.linalg.norm(vertices-edit._pivot,axis=1).max()<=guide.radius+2e-15


@pytest.mark.parametrize('maximum',[False,0,6,250001])
def test_invalid_guidance_admission_rejects(tmp_path,maximum):
    pp,policy_path,*_=make(tmp_path)
    with pytest.raises(ValueError):SceneGuidance(GripPoseEdit(pp),read(policy_path),maximum_points=maximum)


def test_guidance_budget_cannot_silently_drop_actor_faces(tmp_path):
    pp,policy_path,*_=make(tmp_path)
    with pytest.raises(ValueError,match='no faces dropped'):SceneGuidance(GripPoseEdit(pp),read(policy_path),maximum_points=84)


def test_native_ball_margin_and_centre_bound_are_not_relaxed(tmp_path):
    pp,policy_path,*_=make(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path))
    assert guide.margins([.8,.8,0,0])[0]<0 and not guide.evaluate([.8,.8,0,0])['native_pose_permissions_pass']
    assert np.all(guide.margins([0.,0,0,0])>=0)


def test_evaluation_limit_retains_every_measured_proposal(tmp_path):
    pp,policy_path,*_=make(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path))
    result=optimize(guide,[0.,0,0,0],tmp_path/'guidance',maximum_evaluations=1)
    assert result['stop_reason']=='evaluation_limit' and result['evaluations']==1 and result['optimizer'] is None
    assert len(read(tmp_path/'guidance/history.json'))==1 and not result['geometry_approved']


def test_locked_rotation_never_calls_optimizer(tmp_path):
    pp,policy_path,_,_,permission=make(tmp_path);permission['maximum_rotation_degrees']=0.;save(pp,permission);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path))
    result=optimize(guide,[0.,0,0,0],tmp_path/'locked');assert result['stop_reason']=='rotation_locked' and result['evaluations']==1


@pytest.mark.parametrize('evaluations,iterations',[(0,1),(513,1),(True,1),(2,0),(2,101),(2,True)])
def test_bad_optimizer_budgets_reject(tmp_path,evaluations,iterations):
    pp,policy_path,*_=make(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path))
    with pytest.raises(ValueError):optimize(guide,[0.,0,0,0],tmp_path/'no',maximum_evaluations=evaluations,maximum_iterations=iterations)
    assert not (tmp_path/'no').exists()


def test_initial_native_bound_failure_cannot_become_new_source(tmp_path):
    pp,policy_path,*_=make(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path))
    with pytest.raises(ValueError,match='original native permissions'):optimize(guide,[.8,.8,0,0],tmp_path/'no')


def test_complete_export_checks_known_repaired_warm_start(tmp_path):
    pp,policy_path,path,spec,_=make(tmp_path);warm=tmp_path/'warm.json';save(warm,dict(schema='strep-prop-source-relative-warm-start-v1',permissions_sha256=sha256(pp),controls=[0.,0,.5*(1-1e-12),1.]))
    pins=GripPoseEdit(pp).inputs;result=fit(pp,policy_path,warm,tmp_path/'fit',maximum_evaluations=1)
    assert result['sampled_feasible_probe']==1 and result['guidance_stop_reason']=='evaluation_limit' and result['geometry_times']==3
    assert not result['source_rebased'] and not result['character_motion_edited'] and not result['quality_approved'] and result['original_selected']
    candidate=read(tmp_path/'fit/probe-001/mesh-scene.json');assert candidate['props']['crate']['keyframes'][0]==spec['props']['crate']['keyframes'][0] and candidate['props']['crate']['keyframes'][2]==spec['props']['crate']['keyframes'][2]
    assert all(sha256(p)==d for p,d in pins.items()) and read(tmp_path/'fit/probe-001/geometry.json')['sampled_conditions_pass']


def test_forged_warm_binding_rejects_before_output(tmp_path):
    pp,policy_path,*_=make(tmp_path);warm=tmp_path/'warm.json';save(warm,dict(schema='strep-prop-source-relative-warm-start-v1',permissions_sha256='0'*64,controls=[0.,0,0,0]))
    with pytest.raises(ValueError,match='permission-bound'):fit(pp,policy_path,warm,tmp_path/'no')
    assert not (tmp_path/'no').exists()


def test_actual_local_optimizer_reduces_geometry_guidance_without_approval(tmp_path):
    pp,policy_path,*_=make(tmp_path);guide=SceneGuidance(GripPoseEdit(pp),read(policy_path));initial=[0.,0,.25,1.]
    result=optimize(guide,initial,tmp_path/'search',maximum_evaluations=48,maximum_iterations=6)
    assert result['best_guidance_energy']<result['starting_energy'] and guide.edit.evaluate(result['best_guidance_controls'])['report']['native_pose_permissions_pass']
    assert not result['source_rebased'] and not result['geometry_approved'] and not result['quality_approved']


def test_positive_residual_screen_matches_complete_signed_queries(tmp_path):
    import trimesh
    asset=cube(tmp_path/'cube.glb');mesh=trimesh.Trimesh(asset.vertices_m,asset.faces,process=False)
    rng=np.random.default_rng(24);points=np.r_[rng.uniform(-1,1,(160,3)),rng.uniform(-.09,.09,(40,3)),np.array([[.1-1e-9,0,0],[.1+1e-9,0,0],[.1+1e-6,0,0]])]
    expected=np.maximum(0,signed(mesh,points)+1e-8);actual=positive_signed(mesh,points,1e-8)
    np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-14)
