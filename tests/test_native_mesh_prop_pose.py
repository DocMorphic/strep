"""Bounded prop edits preserve original assets, grips, frozen keys and failures."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from native_mesh_prop_pose import GripPoseEdit,candidate_controls,conditions,search,pareto_improvement
from native_mesh_prop_scene import MeshPropScene
from native_scene_contacts import SceneContacts
from native_observation_archive import verify
from static_prop_asset import StaticPropAsset
from strep import read,save,sha256
from test_native_mesh_prop_scene import fixture,contact


def setup(tmp_path):
    path,spec,policy,prop,grip_path=fixture(tmp_path);scene=SceneContacts(read(tmp_path/'contacts.json'),tmp_path)
    target=scene.actor_points('A',np.array([2]),np.array([1.]))[0,0];local=np.asarray(read(grip_path)['position_m'])
    spec['props']['crate']['keyframes']=[dict(time_s=t,translation_m=p,rotation_xyzw=[0,0,0,1]) for t,p in [(0.,[3.,1.,0]),(1.,(target-local).tolist()),(2.,[3.,1.,0])]]
    row=contact(grip_path);row['vertices']=[[6,0,2]];spec['mesh_contacts']=[row];save(path,spec);policy['mesh_scene_sha256']=sha256(path)
    permission=dict(schema='strep-native-mesh-prop-pose-edit-v1',mesh_scene=path.name,mesh_scene_sha256=sha256(path),prop='crate',key_index=1,contact_id='mesh-touch',frozen_keys=[0,2],maximum_rotation_degrees=180.,maximum_translation_m=.5,maximum_clearance_m=5e-7,clearance_direction_local=[1.,0,0])
    pp=tmp_path/'permissions.json';save(pp,permission);policy_path=tmp_path/'policy.json';save(policy_path,policy)
    return pp,policy_path,path,spec,permission


def test_zero_export_preserves_every_native_pose_and_all_asset_bytes(tmp_path):
    pp,policy_path,path,spec,_=setup(tmp_path);before={p:p.read_bytes() for p in tmp_path.iterdir() if p.is_file()};edit=GripPoseEdit(pp)
    manifest=edit.write(np.zeros(4),tmp_path/'zero');derived=read(manifest)
    assert derived['props']['crate']['keyframes']==spec['props']['crate']['keyframes']
    original=MeshPropScene(path);candidate=MeshPropScene(manifest);times=np.linspace(0,2,65)
    for a,b in zip(original.prop_poses('crate',times),candidate.prop_poses('crate',times)):assert a.tobytes()==b.tobytes()
    assert all(p.read_bytes()==raw for p,raw in before.items())
    bound,arrays=edit.sampled_permissions(candidate,read(policy_path));assert bound['all_sampled_pose_permissions_pass'] and not np.any(arrays['translation_m']) and not np.any(arrays['rotation_degrees'])
    assert not read(manifest.parent/'proposal.json')['release_approved']


def test_rotated_clearance_candidate_repairs_complete_declared_scene_and_contacts(tmp_path):
    pp,policy_path,path,spec,_=setup(tmp_path);edit=GripPoseEdit(pp);value=np.array([0.,0,.5*(1-1e-12),1.])
    response=edit.evaluate(value);assert response['report']['native_pose_permissions_pass']
    before,_=MeshPropScene(path).geometry(read(policy_path));assert not before['sampled_conditions_pass']
    manifest=edit.write(value,tmp_path/'fixed');candidate=MeshPropScene(manifest);policy=read(policy_path);policy['mesh_scene_sha256']=sha256(manifest)
    contact_report,_=candidate.contact_audit();geometry,_=candidate.geometry(policy)
    assert contact_report['all_declared_point_contacts_pass'] and geometry['sampled_conditions_pass']
    bound,_=edit.sampled_permissions(candidate,read(policy_path));assert bound['all_sampled_pose_permissions_pass']
    assert before['actor_faces']==geometry['actor_faces'] and before['prop_faces']==geometry['prop_faces']
    original_conditions=conditions(before);new_conditions=conditions(geometry);assert original_conditions.keys()==new_conditions.keys() and all(not passed or new_conditions[key] for key,passed in original_conditions.items())
    exported=read(manifest);assert exported['props']['crate']['keyframes'][0]==spec['props']['crate']['keyframes'][0] and exported['props']['crate']['keyframes'][2]==spec['props']['crate']['keyframes'][2]
    assert exported['actor_scene_sha256']==spec['actor_scene_sha256'] and exported['mesh_contacts'][0]['grip_sha256']==spec['mesh_contacts'][0]['grip_sha256']
    assert not response['report']['transition_compatibility_verified']


def test_all_three_local_rotation_axes_match_independent_rigid_geometry(tmp_path):
    pp,_,_,_,permission=setup(tmp_path);edit=GripPoseEdit(pp);value=np.array([.08,-.05,.03,.4]);response=edit.evaluate(value)
    r=Rotation.from_rotvec(np.radians(permission['maximum_rotation_degrees'])*value[:3]).as_matrix()
    point=edit._point;original_pivot=edit._position+edit._rotation@point
    expected=original_pivot+r@(np.asarray(permission['clearance_direction_local'])*permission['maximum_clearance_m']*value[3]-point)
    np.testing.assert_allclose(response['position_m'],expected,atol=2e-16,rtol=0)
    np.testing.assert_allclose(response['rotation_matrix'],r,atol=2e-16,rtol=0)
    assert response['report']['rotation_change_degrees']>0 and response['report']['translation_change_m']>0


def test_cumulative_values_always_reference_original_permissions(tmp_path):
    pp,_,_,_,_=setup(tmp_path);edit=GripPoseEdit(pp)
    first=edit.write(np.array([.2,0,0,0]),tmp_path/'first');second=edit.write(np.array([.3,0,0,0]),tmp_path/'second')
    a,b=read(first)['props']['crate']['keyframes'][1],read(second)['props']['crate']['keyframes'][1]
    assert abs(np.degrees(Rotation.from_quat(a['rotation_xyzw']).magnitude())-36)<1e-12
    assert abs(np.degrees(Rotation.from_quat(b['rotation_xyzw']).magnitude())-54)<1e-12


@pytest.mark.parametrize('value',[np.ones(4),[1.,1,0,0]])
def test_failed_norm_bounds_cannot_be_exported_or_clipped(tmp_path,value):
    pp,_,_,_,_=setup(tmp_path);edit=GripPoseEdit(pp);assert not edit.evaluate(value)['report']['native_pose_permissions_pass']
    output=tmp_path/'failed'
    with pytest.raises(ValueError,match='not clipped'):edit.write(value,output)
    assert not output.exists()


def test_center_displacement_is_a_separate_hard_permission(tmp_path):
    pp,_,_,_,permission=setup(tmp_path);permission['maximum_translation_m']=0.;save(pp,permission);edit=GripPoseEdit(pp)
    assert edit.evaluate(np.zeros(4))['report']['native_pose_permissions_pass']
    assert not edit.evaluate([0,0,.5,0])['report']['native_pose_permissions_pass']
    with pytest.raises(ValueError):edit.write([0,0,.5,0],tmp_path/'no')


@pytest.mark.parametrize('value',[[0,0,0],np.full(4,np.nan),np.full(4,np.inf),np.ones(4,dtype=bool),[False,0.,0.,0.],[1.1,0,0,0],[0,0,0,-.1],[0,0,0,1.1]])
def test_malformed_or_out_of_box_controls_reject(tmp_path,value):
    pp,_,_,_,_=setup(tmp_path)
    with pytest.raises(ValueError):GripPoseEdit(pp).evaluate(value)


@pytest.mark.parametrize('fault',['scene_digest','prop','key','frozen_key','duplicate_frozen','boolean_frozen','contact','angle','translation','clearance','direction'])
def test_invalid_or_unauthorized_pose_declarations_reject(tmp_path,fault):
    pp,_,_,_,p=setup(tmp_path)
    if fault=='scene_digest':p['mesh_scene_sha256']='0'*64
    elif fault=='prop':p['prop']='missing'
    elif fault=='key':p['key_index']=True
    elif fault=='frozen_key':p['frozen_keys']=[0,1,2]
    elif fault=='duplicate_frozen':p['frozen_keys']=[0,0]
    elif fault=='boolean_frozen':p['frozen_keys']=[False]
    elif fault=='contact':p['contact_id']='missing'
    elif fault=='angle':p['maximum_rotation_degrees']=181
    elif fault=='translation':p['maximum_translation_m']=-1
    elif fault=='clearance':p['maximum_clearance_m']=.2
    else:p['clearance_direction_local']=[1.,1.,0]
    save(pp,p)
    with pytest.raises(ValueError):GripPoseEdit(pp)


def test_locks_and_finite_candidate_table_do_not_remove_authorized_axes(tmp_path):
    pp,_,_,_,permission=setup(tmp_path);edit=GripPoseEdit(pp);table=np.asarray(candidate_controls(edit))
    assert table.shape==(80,4) and np.all(np.sum(table[:,:3]**2,axis=1)<=1)
    assert all(np.any(table[:,axis]>0) and np.any(table[:,axis]<0) for axis in range(3))
    permission['maximum_rotation_degrees']=0.;save(pp,permission);locked=GripPoseEdit(pp)
    assert len(candidate_controls(locked))==2
    with pytest.raises(ValueError,match='locked'):locked.evaluate([.1,0,0,0])
    permission['maximum_clearance_m']=0.;save(pp,permission);locked=GripPoseEdit(pp)
    assert len(candidate_controls(locked))==1
    with pytest.raises(ValueError,match='locked'):locked.evaluate([0,0,0,.1])


def test_nontrivial_original_rotations_retain_exact_zero_sampled_change(tmp_path):
    pp,policy_path,path,spec,permission=setup(tmp_path)
    for index,key in enumerate(spec['props']['crate']['keyframes']):key['rotation_xyzw']=Rotation.from_euler('xyz',[10+index,20-index,30+index],degrees=True).as_quat().tolist()
    save(path,spec);permission['mesh_scene_sha256']=sha256(path);permission['maximum_rotation_degrees']=0.;permission['maximum_clearance_m']=0.;save(pp,permission)
    policy=read(policy_path);policy['mesh_scene_sha256']=sha256(path);edit=GripPoseEdit(pp);manifest=edit.write(np.zeros(4),tmp_path/'zero')
    report,arrays=edit.sampled_permissions(MeshPropScene(manifest),policy)
    assert report['all_sampled_pose_permissions_pass'] and not np.any(arrays['rotation_degrees'])


def test_repeated_export_and_changed_source_files_reject_without_writes(tmp_path):
    pp,_,_,_,_=setup(tmp_path);edit=GripPoseEdit(pp);output=tmp_path/'once';edit.write(np.zeros(4),output)
    with pytest.raises(ValueError,match='Fresh'):edit.write(np.zeros(4),output)
    grip=tmp_path/'grip.json';grip.write_bytes(grip.read_bytes()+b' ')
    with pytest.raises(ValueError,match='changed'):edit.write(np.zeros(4),tmp_path/'changed')
    assert not (tmp_path/'changed').exists()


def test_complete_search_retains_rejections_and_finds_only_sampled_solution(tmp_path):
    pp,policy_path,_,_,_=setup(tmp_path);output=tmp_path/'search';result=search(pp,policy_path,output)
    assert result['sampled_feasible_probe'] is not None and result['no_original_geometry_conditions_omitted']
    assert result['history'][0]['sampled_geometry_pass'] is False and result['history'][-1]['sampled_candidate_pass']
    assert all(row.get('new_failed_geometry_conditions',0)>=0 for row in result['history'])
    chosen=output/f"probe-{result['sampled_feasible_probe']:03d}"
    verify(chosen/'geometry-observations.npz');assert read(chosen/'sampled-permissions.json')['all_sampled_pose_permissions_pass']
    assert not result['quality_approved'] and not result['release_approved'] and not result['continuous_collision_certified'] and not result['character_motion_edited']


def test_limited_search_cannot_claim_full_table_or_infeasibility(tmp_path):
    pp,policy_path,_,_,_=setup(tmp_path);result=search(pp,policy_path,tmp_path/'limited',maximum_candidates=1)
    assert result['candidate_table_size']==80 and result['candidates_recorded']==1 and not result['complete_table_evaluated']
    assert result['sampled_feasible_probe'] is None and result['best_admissible_probe']==0 and not result['release_approved']
    assert not result['improving_candidate_found']


def test_fewer_crossings_cannot_hide_deeper_penetration_or_new_failed_samples():
    before=dict(failed_conditions=2,failed_samples=1,surface_records=10,maximum_depth_m=.02)
    assert pareto_improvement(dict(before,maximum_depth_m=.01),before)
    assert not pareto_improvement(dict(before,surface_records=1,maximum_depth_m=.03),before)
    assert not pareto_improvement(dict(before,failed_samples=2,maximum_depth_m=.001),before)
    assert not pareto_improvement(before,before)
    assert pareto_improvement(before,None)
    for bad in [dict(before,maximum_depth_m=float('nan')),dict(before,surface_records=-1),dict(before,failed_samples=True)]:
        with pytest.raises(ValueError):pareto_improvement(bad,before)


def test_other_grips_are_rechecked_and_can_reject_an_individually_valid_pose(tmp_path):
    pp,_,path,spec,permission=setup(tmp_path);prop=StaticPropAsset.load(tmp_path/'prop.glb')
    first=dict(schema='strep-prop-grip-selection-v1',label='First',**prop.surface_point(0,[0.,0,1.]))
    second=dict(schema='strep-prop-grip-selection-v1',label='Second',**prop.surface_point(0,[1.,0,0]))
    save(tmp_path/'grip.json',first);save(tmp_path/'second-grip.json',second)
    spec['mesh_contacts'][0]['grip_sha256']=sha256(tmp_path/'grip.json')
    scene=SceneContacts(read(tmp_path/'contacts.json'),tmp_path);target=scene.actor_points('A',np.array([2]),np.array([1.]))[0,0]
    spec['props']['crate']['keyframes'][1]['translation_m']=(target-np.asarray(first['position_m'])).tolist()
    row=copy.deepcopy(spec['mesh_contacts'][0]);row.update(id='second-grip',vertices=[[6,0,2],[6,0,3]],reduction='centroid',grip='second-grip.json',grip_sha256=sha256(tmp_path/'second-grip.json'));spec['mesh_contacts'].append(row)
    save(path,spec);permission['mesh_scene_sha256']=sha256(path);save(pp,permission)
    original,_=MeshPropScene(path).contact_audit();assert original['all_declared_point_contacts_pass']
    edit=GripPoseEdit(pp);value=np.array([.5*(1-1e-12),0,0,1.]);assert edit.evaluate(value)['report']['native_pose_permissions_pass']
    manifest=edit.write(value,tmp_path/'second-grip-failure');after,_=MeshPropScene(manifest).contact_audit()
    assert after['mesh_contacts'][0]['passed'] and not after['mesh_contacts'][1]['passed'] and not after['all_declared_point_contacts_pass']


def test_unrelated_prop_tracks_are_never_changed(tmp_path):
    pp,_,path,spec,permission=setup(tmp_path);spec['props']['unrelated']=copy.deepcopy(spec['props']['crate'])
    for key in spec['props']['unrelated']['keyframes']:key['translation_m']=[8.,2.,1.]
    save(path,spec);permission['mesh_scene_sha256']=sha256(path);save(pp,permission)
    manifest=GripPoseEdit(pp).write([0,0,.25,.5],tmp_path/'unchanged-other');after=read(manifest)
    assert after['props']['unrelated']['keyframes']==spec['props']['unrelated']['keyframes']
    assert after['props']['unrelated']['sha256']==spec['props']['unrelated']['sha256']
