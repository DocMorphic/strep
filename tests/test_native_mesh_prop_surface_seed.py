"""Guidance is source-relative and complete audits retain conflicting contacts."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import native_mesh_prop_surface_seed as module
from native_mesh_prop_surface_seed import unit,opposing_orientation,incident_guidance,surface_proposals,search
from native_mesh_prop_pose import GripPoseEdit
from native_mesh_prop_scene import MeshPropScene
from strep import read,save,sha256
from test_native_mesh_prop_pose import setup


@pytest.mark.parametrize('source,target',[( [1.,0,0],[1.,0,0]),([1.,0,0],[-1.,0,0]),([.2,-.4,.8],[-.7,.1,.2])])
@pytest.mark.parametrize('twist',[0.,63.,180.,315.])
def test_opposing_normals_and_twist_preserve_rigid_rotation(source,target,twist):
    r=opposing_orientation(source,target,twist).as_matrix()
    np.testing.assert_allclose(r@unit(source),-unit(target),rtol=0,atol=8e-16)
    np.testing.assert_allclose(r.T@r,np.eye(3),rtol=0,atol=9e-16);assert abs(np.linalg.det(r)-1)<1e-15


def test_world_twist_is_about_actor_normal():
    normal=unit([.3,-.4,.5]);a=opposing_orientation([1.,0,0],normal,0.);b=opposing_orientation([1.,0,0],normal,90.)
    np.testing.assert_allclose((b*a.inv()).as_matrix(),Rotation.from_rotvec(normal*np.pi/2).as_matrix(),rtol=0,atol=7e-16)


@pytest.mark.parametrize('value',[[0.,0,0],[False,1.,0],np.array([True,False,False]),[np.nan,0,0],[np.inf,0,0],[1.,2.]])
def test_invalid_normal_rejected(value):
    with pytest.raises(ValueError):unit(value)


def test_all_incident_faces_retained_and_area_weighted():
    v=np.array([[0.,0,0],[2,0,0],[0,1,0],[0,0,3],[9,9,9],[10,9,9],[9,10,9]])
    f=np.array([[0,1,2],[0,3,1],[4,5,6]])
    guide=incident_guidance(v,f,np.array([0]));assert guide['incident_faces']==[0,1]
    assert [r['face'] for r in guide['directions']]==[None,0,1]
    np.testing.assert_allclose(guide['directions'][0]['normal'],unit([0.,6,2]),rtol=0,atol=0)
    assert not guide['geometry_approval'] and not guide['outward_normal_verified']


def test_cancelling_mean_keeps_both_opposed_face_directions():
    guide=incident_guidance(np.array([[0.,0,0],[1,0,0],[0,1,0]]),np.array([[0,1,2],[0,2,1]]),np.array([0]))
    assert not guide['weighted_normal_available'] and len(guide['directions'])==2


@pytest.mark.parametrize('faces,ids',[(np.array([[0,0,1]]),[0]),(np.array([[0,1,3]]),[0]),(np.array([[0.,1,2]]),[0]),(np.array([[0,1,2]]),[0,0]),(np.array([[0,1,2]]),[True]),(np.array([[0,1,2]]),[3])])
def test_invalid_or_degenerate_guidance_rejects_without_face_drop(faces,ids):
    with pytest.raises(ValueError):incident_guidance(np.array([[0.,0,0],[1,0,0],[0,1,0]]),faces,np.array(ids))


def test_fixture_seed_reconstructs_original_relative_controls_and_contact(tmp_path):
    pp,policy_path,path,spec,permission=setup(tmp_path);originals={p:sha256(p) for p in [pp,path,tmp_path/'prop.glb',tmp_path/'actor.glb'] if p.exists()}
    edit=GripPoseEdit(pp);originals={Path(p):digest for p,digest in edit.inputs.items()};guide,table=surface_proposals(edit,(0.,90.));assert guide['incident_faces'] and len(table)==2*len(guide['directions']);checked=0
    for i,row in enumerate(table):
        value=row['controls']
        try:response=edit.evaluate(value)
        except ValueError:continue
        if not response['report']['native_pose_permissions_pass']:continue
        checked+=1
        target=opposing_orientation(next(r for r in edit.scene._rows if r['authored']['id']=='mesh-touch')['normal'],guide['directions'][row['direction_index']]['normal'],row['twist_degrees'])
        np.testing.assert_allclose(response['rotation_matrix'],target.as_matrix(),rtol=0,atol=1e-15)
        manifest=edit.write(value,tmp_path/f'candidate-{i}');candidate=MeshPropScene(manifest);audit,_=candidate.contact_audit();assert audit['all_declared_point_contacts_pass']
        assert read(manifest)['props']['crate']['keyframes'][0]==spec['props']['crate']['keyframes'][0]
        bound,_=edit.sampled_permissions(candidate,read(policy_path));assert bound['all_sampled_pose_permissions_pass']
    assert checked>0 and all(sha256(p)==digest for p,digest in originals.items())


@pytest.mark.parametrize('twists',[[],[0.,0.],[360.],[False],[float('nan')],list(range(17))])
def test_bad_twists_reject(tmp_path,twists):
    pp,*_=setup(tmp_path)
    with pytest.raises(ValueError):surface_proposals(GripPoseEdit(pp),twists)


def test_locked_rotation_yields_no_orientation_proposals(tmp_path):
    pp,_,_,_,permission=setup(tmp_path);permission['maximum_rotation_degrees']=0.;save(pp,permission)
    guide,table=surface_proposals(GripPoseEdit(pp));assert guide['rotation_locked'] and table==[]


def test_contact_time_must_include_edit_key(tmp_path):
    pp,_,path,spec,permission=setup(tmp_path);spec['mesh_contacts'][0]['interval_s']=[0.,0.];save(path,spec);permission['mesh_scene_sha256']=sha256(path);save(pp,permission)
    with pytest.raises(ValueError,match='contact interval'):surface_proposals(GripPoseEdit(pp))


def test_search_retains_out_of_domain_guidance_instead_of_clipping(tmp_path,monkeypatch):
    pp,policy_path,*_=setup(tmp_path)
    monkeypatch.setattr(module,'surface_proposals',lambda *args: ({},[dict(direction_index=0,twist_degrees=0.,controls=[1.1,0,0,1])]))
    result=search(pp,policy_path,tmp_path/'search',maximum_candidates=2)
    assert result['history'][1]['reason']=='control_domain' and not (tmp_path/'search/probe-001').exists()
    assert result['best_admissible_probe']==0 and result['sampled_feasible_probe'] is None and not result['quality_approved']


def test_warm_start_requires_original_permission_binding(tmp_path):
    pp,policy_path,*_=setup(tmp_path);warm=tmp_path/'warm.json';save(warm,dict(schema='strep-prop-source-relative-warm-start-v1',permissions_sha256='0'*64,controls=[0,0,0,0]))
    with pytest.raises(ValueError,match='original pose permissions'):search(pp,policy_path,tmp_path/'no',warm_start_path=warm)
    assert not (tmp_path/'no').exists()


def test_guided_search_repairs_known_convex_fixture_with_complete_checks(tmp_path):
    pp,policy_path,*_=setup(tmp_path);result=search(pp,policy_path,tmp_path/'guided')
    chosen=result['sampled_feasible_probe'];assert chosen is not None and chosen>0
    row=result['history'][chosen];assert row['kind']=='surface-guided' and row['sampled_candidate_pass'] and row['new_failed_geometry_conditions']==0
    report=read(tmp_path/f'guided/probe-{chosen:03d}/geometry.json');assert len(report['samples'])==3 and report['sampled_conditions_pass']
    assert result['source_assets_and_author_permissions_unchanged'] and result['original_selected'] and not result['physics_verified']


def test_verified_warm_start_is_remeasured_under_original_caps(tmp_path):
    pp,policy_path,*_=setup(tmp_path);warm=tmp_path/'warm.json';save(warm,dict(schema='strep-prop-source-relative-warm-start-v1',permissions_sha256=sha256(pp),controls=[0.,0,.5*(1-1e-12),1.]))
    result=search(pp,policy_path,tmp_path/'warm-search',warm_start_path=warm)
    assert result['sampled_feasible_probe']==1 and result['history'][1]['kind']=='source-relative-warm-start'
    assert not result['source_rebased'] and not result['character_motion_edited'] and result['geometry_times']==3
