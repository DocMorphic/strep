"""Explicit empty point targets must not bypass floor geometry or edit bounds."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_geometry import closed_fixture,policy
from native_scene_contacts import SceneContacts,run as contact_audit
from native_scene_fit import run as fit
from native_scene_geometry import evaluate
from strep import save,read,sha256


def scene(tmp_path):
    source,path,spec=closed_fixture(tmp_path);spec['contacts']=[];save(path,spec)
    return source,path,spec


def test_explicit_empty_contacts_are_not_contact_intent_evidence(tmp_path):
    source,path,spec=scene(tmp_path);before=sha256(source)
    result,observations=SceneContacts(spec,tmp_path).evaluate()
    assert result['passed'] and result['contacts']==[] and observations=={}
    assert result['point_contact_conditions_declared']==0 and not result['point_contact_intent_evaluated']
    assert not result['quality_approved'] and not result['continuous_contact_certified']
    assert sha256(source)==before


@pytest.mark.parametrize('replacement',[None,{},False])
def test_empty_declaration_requires_an_actual_list(tmp_path,replacement):
    _,_,spec=scene(tmp_path);spec['contacts']=replacement
    with pytest.raises(ValueError,match='0-64'):SceneContacts(spec,tmp_path)


def test_empty_point_contacts_do_not_hide_floor_failure(tmp_path):
    _,path,spec=scene(tmp_path);loaded=SceneContacts(spec,tmp_path)
    assert loaded.evaluate()[0]['passed']
    request=policy(path,planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=10.)))
    result,_=evaluate(loaded,request,sha256(path))
    assert not result['sampled_conditions_pass'] and len(result['samples'])==3
    assert all(not sample['world_planes'][0]['passed'] for sample in result['samples'])
    assert all(sample['world_planes'][0]['maximum_depth_m']>9. for sample in result['samples'])


def test_empty_point_audit_retains_sources_and_empty_observation_archive(tmp_path):
    source,path,_=scene(tmp_path);result=contact_audit(path,tmp_path/'audit')
    assert result['source_snapshots'][str(source.resolve())]['sha256']==sha256(source)
    assert result['point_contact_conditions_declared']==0 and not result['point_contact_intent_evaluated']
    with np.load(tmp_path/'audit/observations.npz',allow_pickle=False) as archive:assert archive.files==[]
    with pytest.raises(ValueError,match='Fresh'):contact_audit(path,tmp_path/'audit')


@pytest.mark.parametrize('floor_height,expected_pass',[(-10.,True),(10.,False)])
def test_geometry_only_fit_keeps_hard_bounds_and_original_selection(tmp_path,floor_height,expected_pass):
    source,path,spec=scene(tmp_path);before=sha256(source)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(path),actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],
        tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)))
    save(tmp_path/'permissions.json',permissions)
    request=policy(path,planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=floor_height)))
    save(tmp_path/'geometry.json',request)
    result=fit(path,tmp_path/'permissions.json',tmp_path/'fit',iterations=1,proposal_model='surface-vector',
               geometry_policy=tmp_path/'geometry.json')
    assert result['sampled_geometry_conditions_pass'] is expected_pass
    assert result['original_selected'] and not result['quality_approved']
    assert sha256(source)==before
    audit=read(tmp_path/'fit/contact-audit/result.json')
    assert audit['point_contact_conditions_declared']==0 and not audit['point_contact_intent_evaluated']
    geometry=read(tmp_path/'fit/geometry-audit/result.json')
    assert geometry['sampled_conditions_pass'] is expected_pass
