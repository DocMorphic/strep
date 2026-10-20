import copy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from strep import save, read, sha256
from native_mesh_prop_scene import MeshPropScene
from native_mesh_character_fit import MeshCharacterProblem, fit
from native_scene_norms import rows
from test_native_mesh_prop_scene import fixture


def prepared(tmp_path, *, moving=False, conflict=False):
    path, spec, policy, prop, grip_path = fixture(tmp_path)
    actor_path=tmp_path/spec['actor_scene'];actors=read(actor_path)
    actors['contacts']=[];save(actor_path,actors);spec['actor_scene_sha256']=sha256(actor_path)
    from native_scene_contacts import SceneContacts
    source=SceneContacts(actors,tmp_path);point=source.actor_points('A',np.array([2]),np.array([1.]))[0,0]
    face=next(i for i in range(len(prop.faces)) if prop.surface_point(i,[.2,.3,.5])['winding_normal'][0]>.99)
    grip=dict(schema='strep-prop-grip-selection-v1',label='Right face',**prop.surface_point(face,[.2,.3,.5]));save(grip_path,grip)
    target=point+[-.01,0,0];position=target-np.array(grip['position_m'])
    keys=[dict(time_s=0.,translation_m=position.tolist(),rotation_xyzw=[0,0,0,1])]
    if moving:
        keys += [dict(time_s=.7,translation_m=(position+[.03,.01,0]).tolist(),rotation_xyzw=Rotation.from_euler('z',.3).as_quat().tolist()),dict(time_s=2.,translation_m=position.tolist(),rotation_xyzw=[0,0,0,1])]
    spec['props']['crate']['keyframes']=keys
    spec['mesh_contacts']=[dict(id='reach',actor='A',vertices=[[6,0,2]],reduction='centroid',prop='crate',grip=grip_path.name,grip_sha256=sha256(grip_path),mode='hold' if moving else 'touch',interval_s=[.3,1.7] if moving else [1.,1.],limits=dict(position_m=.002,relative_speed_m_s=.02) if moving else dict(position_m=.002))]
    if conflict:
        actors['contacts']=[dict(id='protected-source-point',actor='A',vertices=[[6,0,2]],reduction='centroid',target=dict(space='world',points_m=[point.tolist()]),mode='touch',interval_s=[1.,1.],limits=dict(position_m=1e-7))]
        save(actor_path,actors);spec['actor_scene_sha256']=sha256(actor_path)
    save(path,spec);policy['mesh_scene_sha256']=sha256(path);policy_path=tmp_path/'policy.json';save(policy_path,policy)
    permissions=dict(schema='strep-native-mesh-character-edit-v1',mesh_scene=path.name,mesh_scene_sha256=sha256(path),actors=dict(A=dict(window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02,editable_clip_boundaries=['start','end'])))
    permissions_path=tmp_path/'permissions.json';save(permissions_path,permissions)
    return path,permissions_path,policy_path


def test_moving_mesh_targets_match_independent_complete_contact_clock(tmp_path):
    path,permissions,_=prepared(tmp_path,moving=True);problem=MeshCharacterProblem(permissions)
    report,arrays=problem.mesh.contact_audit();contact=problem.rows[-1]
    np.testing.assert_array_equal(contact['times'],arrays['mesh_contact_0_times_s'])
    assert .7 in contact['times'] and len(contact['times'])>600
    vectors=rows(problem,problem.initial);np.testing.assert_allclose(vectors.residual(),problem.model(problem.initial),atol=1e-9,rtol=1e-12)
    count=len(contact['times']);actual=problem.model(problem.initial)[problem.protected_rows:problem.protected_rows+count]
    error=arrays['mesh_contact_0_error_object_m'];expected=(np.linalg.norm(error,axis=2).ravel()-.002)/.002
    np.testing.assert_allclose(actual,expected,atol=1e-12)
    assert 'geometry' not in problem.scene.objects['crate'] # No invented collision box.
    assert not report['all_declared_point_contacts_pass']


def test_serialized_candidate_keeps_props_grips_and_unpermitted_payloads(tmp_path):
    path,permissions,_=prepared(tmp_path);problem=MeshCharacterProblem(permissions);before={p:sha256(p) for p in problem.inputs}
    controls=problem.initial.copy();controls.reshape(-1,3)[:,0]=-.25
    candidate,residual,_,audits=problem.write(controls,tmp_path/'candidate')
    assert audits['A']['passed'] and audits['A']['strict_edit_caps_pass']
    assert audits['A']['clip_boundary_changes'] # Explicitly opted in, never implied compatibility.
    np.testing.assert_allclose(residual,problem.model(controls),atol=1e-9,rtol=1e-12)
    for name,prop in problem.mesh._props.items():
        np.testing.assert_array_equal(prop['positions'],candidate._props[name]['positions'])
        np.testing.assert_array_equal(prop['rotations'],candidate._props[name]['rotations'])
        assert prop['asset'].geometry_sha256==candidate._props[name]['asset'].geometry_sha256
    assert all(sha256(p)==digest for p,digest in before.items())


@pytest.mark.parametrize('fault',['mesh','permission','track','boundary'])
def test_permission_changes_are_not_inferred_or_rebased(tmp_path,fault):
    path,p,_=prepared(tmp_path);spec=read(p)
    if fault=='mesh':spec['mesh_scene_sha256']='0'*64
    elif fault=='permission':spec['allow_all_joints']=True
    elif fault=='track':spec['actors']['A']['tracks'][0]['maximum_change']=1
    else:spec['actors']['A']['editable_clip_boundaries']=['middle']
    save(p,spec)
    with pytest.raises(ValueError):MeshCharacterProblem(p)


def test_real_guarded_direction_corrects_reach_without_geometry_regression(tmp_path):
    path,p,policy=prepared(tmp_path);before={source:sha256(source) for source in MeshCharacterProblem(p).inputs}
    complete=read(policy);complete['clock']['mode']='native-and-frame-populations';save(policy,complete)
    result=fit(p,policy,tmp_path/'fit',iterations=4,trust=.25,backtracks=4)
    assert result['accepted_steps']>0 and result['sampled_candidate_pass'],result
    assert result['original_selected'] and not result['props_changed'] and not result['quality_approved']
    selected=tmp_path/'fit'/result['candidate'];decision=read(selected/'decision.json')
    assert decision['geometry_conditions_no_regression'] and decision['geometry_metrics_no_worse']
    history=read(tmp_path/'fit/history.json')
    assert history[0]['floor_protection']['rows']>600
    assert decision['geometry_metrics']['maximum_depth_m']==0
    candidate=MeshPropScene(selected/'mesh-scene.json');report,arrays=candidate.contact_audit()
    assert report==read(selected/'contacts.json') and report['all_declared_point_contacts_pass']
    with np.load(selected/'contact-observations.npz') as saved:
        for key,value in arrays.items():np.testing.assert_array_equal(value,saved[key])
    assert all(sha256(source)==digest for source,digest in before.items())


def test_incompatible_protected_contact_is_retained_as_failure(tmp_path):
    _,p,policy=prepared(tmp_path,conflict=True);result=fit(p,policy,tmp_path/'fit',iterations=1,trust=.25,backtracks=2)
    assert not result['sampled_candidate_pass'] and result['original_selected'] and not result['release_approved']
    for row in read(tmp_path/'fit/probes.json') if (tmp_path/'fit/probes.json').exists() else []:
        if row['accepted']:assert row['contact_rows_no_worse'] and row['geometry_conditions_no_regression']


def test_closer_contact_cannot_buy_a_new_mesh_collision(tmp_path):
    path,p,policy_path=prepared(tmp_path);spec=read(path)
    scene=MeshPropScene(path);point=scene._scene.actor_points('A',np.array([2]),np.array([1.]))[0,0]
    obstacle=copy.deepcopy(spec['props']['crate'])
    obstacle['keyframes']=[dict(time_s=0.,translation_m=(point+[-.105,-.2,.2]).tolist(),rotation_xyzw=[0,0,0,1])]
    spec['props']['obstacle']=obstacle;save(path,spec)
    permission=read(p);permission['mesh_scene_sha256']=sha256(path);save(p,permission)
    policy=read(policy_path);policy['mesh_scene_sha256']=sha256(path);save(policy_path,policy)
    result=fit(p,policy_path,tmp_path/'fit',iterations=3,trust=.25,backtracks=4)
    assert not result['sampled_candidate_pass'] and result['original_selected']
    probes=read(tmp_path/'fit/probes.json')
    assert any(r['geometry_evaluated'] and not r['geometry_conditions_no_regression'] and not r['accepted'] for r in probes)
    assert all(r['geometry_conditions_no_regression'] and r['geometry_metrics_no_worse'] for r in probes if r['accepted'])
