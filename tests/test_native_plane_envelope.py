"""Whole-vertex plane minima, changed extrema and unchanged decoded decisions."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_geometry import closed_fixture,policy
from test_native_partner_surface_rows import scene_fixture
from native_scene_contacts import SceneContacts
from native_scene_geometry import evaluate
from native_partner_surface_rows import build
from native_scene_fit import run as fit
from rig_asset import RigAsset,array
from gltf_tools import append_accessor,write_glb
from strep import save,read,sha256


def prepare(tmp_path,*,normal=(0.,1.,0.),offset=.3):
    source,path,spec=closed_fixture(tmp_path);spec['contacts']=[];save(path,spec)
    request=policy(path,planes=dict(ground=dict(normal_world=list(normal),offset_m=offset)))
    return source,path,spec,request,SceneContacts(spec,tmp_path)


@pytest.mark.parametrize('normal',[(0.,1.,0.),(1.,0.,0.),(2**-.5,2**-.5,0.)])
def test_envelope_matches_full_minimum_and_geometry_at_every_time(tmp_path,normal):
    source,path,_,request,scene=prepare(tmp_path,normal=normal);before=sha256(source)
    guides=build(scene,request,sha256(path),plane_guidance='minimum-envelope')
    geometry,_=evaluate(scene,request,sha256(path));gaps=guides.gaps()
    assert len(guides.rows)==3 and guides.report['world_plane_vertex_evaluations']==24
    for i,time in enumerate(request['clock']['times_s']):
        actor=scene.actors['A'];vertices=actor['rig'].vertices(actor['sampler'].sample(time))
        expected=float((vertices@np.array(normal)).min()-.3)
        assert gaps[i]==pytest.approx(expected,abs=1e-12)
        assert geometry['samples'][i]['world_planes'][0]['maximum_depth_m']==pytest.approx(max(0.,-expected))
    assert sha256(source)==before and not guides.report['quality_approved']


def test_complete_envelopes_fit_budget_without_truncating_vertex_checks(tmp_path):
    _,path,_,request,scene=prepare(tmp_path,offset=5.)
    with pytest.raises(ValueError,match='no subset'):build(scene,request,sha256(path),maximum_rows=3)
    guides=build(scene,request,sha256(path),maximum_rows=3,plane_guidance='minimum-envelope')
    assert len(guides.rows)==3 and guides.report['world_plane_candidate_vertices']==24
    assert guides.report['world_plane_vertex_evaluations']==24 and len(guides.report['samples'])==3
    with pytest.raises(ValueError,match='no subset'):build(scene,request,sha256(path),maximum_rows=2,plane_guidance='minimum-envelope')


def test_changed_minimum_is_reevaluated_and_cannot_be_hidden_by_old_witness(tmp_path):
    _,path,_,request,scene=prepare(tmp_path)
    guides=build(scene,request,sha256(path),plane_guidance='minimum-envelope');old=guides.gaps()
    selected={r['time_s']:r['left']['vertices'][0] for r in guides.rows}
    def moved(actor,time):
        a=scene.actors[actor];v=a['rig'].vertices(a['sampler'].sample(time)).copy();v[selected[time],1]+=1.
        return v
    np.testing.assert_allclose(guides.gaps(moved),old,rtol=0,atol=1e-12)
    geometry,_=evaluate(scene,request,sha256(path),actor_vertices=moved)
    assert not geometry['sampled_conditions_pass']


def test_formerly_clear_plane_stays_in_guidance_and_new_crossing_is_seen(tmp_path):
    _,path,_,request,scene=prepare(tmp_path,offset=-10.)
    guides=build(scene,request,sha256(path),plane_guidance='minimum-envelope')
    assert guides.report['world_plane_candidate_vertices']==0 and len(guides.rows)==3
    def moved(actor,time):
        a=scene.actors[actor];v=a['rig'].vertices(a['sampler'].sample(time)).copy();v[7,1]=-11.
        return v
    np.testing.assert_allclose(guides.gaps(moved),[-1.]*3,rtol=0,atol=1e-12)
    assert not evaluate(scene,request,sha256(path),actor_vertices=moved)[0]['sampled_conditions_pass']


def test_plane_envelope_and_legacy_guides_include_unreferenced_vertices(tmp_path):
    source,path,spec,request,_=prepare(tmp_path);rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);primitive=document['meshes'][0]['primitives'][0]
    attributes=primitive['attributes'];positions=array(document,binary,attributes['POSITION'])
    attributes['POSITION']=append_accessor(document,binary,np.r_[positions,[[0.,-4.,0.]]],'VEC3')
    weights=array(document,binary,attributes['WEIGHTS_0']);attributes['WEIGHTS_0']=append_accessor(document,binary,np.r_[weights,weights[:1]],'VEC4')
    joints=array(document,binary,attributes['JOINTS_0']);values=np.r_[joints,joints[:1]].astype('<u2')
    while len(binary)%4:binary.append(0)
    start=len(binary);binary.extend(values.tobytes());view=len(document['bufferViews'])
    document['bufferViews'].append(dict(buffer=0,byteOffset=start,byteLength=values.nbytes))
    attributes['JOINTS_0']=len(document['accessors']);document['accessors'].append(dict(bufferView=view,componentType=5123,count=9,type='VEC4'))
    write_glb(source,document,binary);spec['actors']['A']['sha256']=sha256(source);save(path,spec);request['contacts_sha256']=sha256(path)
    scene=SceneContacts(spec,tmp_path)
    guides=build(scene,request,sha256(path),plane_guidance='minimum-envelope')
    assert guides.report['referenced_vertices']['A']==8 and guides.report['source_vertices']['A']==9
    assert guides.report['world_plane_vertex_evaluations']==27
    assert all(row['left']['vertices']==[8] for row in guides.rows)
    legacy=build(scene,request,sha256(path));assert sum(row['left']['vertices']==[8] for row in legacy.rows)==3
    from native_compact_surface_rows import build as compact_build
    compact=compact_build(scene,request,sha256(path))
    assert compact.rows==legacy.rows and compact.report['samples']==legacy.report['samples']
    assert compact.report['world_plane_vertex_evaluations']==27
    np.testing.assert_array_equal(compact.gaps(),legacy.gaps())


def test_partner_surface_rows_are_unchanged_by_plane_guidance(tmp_path):
    scene,request,digest=scene_fixture(tmp_path)
    a=build(scene,request,digest);b=build(scene,request,digest,plane_guidance='minimum-envelope')
    assert a.rows==b.rows
    np.testing.assert_array_equal(a.gaps(),b.gaps())


@pytest.mark.parametrize('mode',[None,False,[],{},'subset','minimum'])
def test_invalid_guidance_rejected(tmp_path,mode):
    _,path,_,request,scene=prepare(tmp_path)
    with pytest.raises(ValueError,match='plane guidance'):build(scene,request,sha256(path),plane_guidance=mode)


def test_serialized_fit_records_guidance_and_resume_inherits_it(tmp_path):
    source,path,_,request,_=prepare(tmp_path,offset=-10.);before=sha256(source)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(path),actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)))
    save(tmp_path/'permissions.json',permissions);save(tmp_path/'geometry.json',request)
    a=fit(path,tmp_path/'permissions.json',tmp_path/'first',iterations=1,proposal_model='surface-vector',
        geometry_policy=tmp_path/'geometry.json',plane_guidance='minimum-envelope')
    b=fit(path,tmp_path/'permissions.json',tmp_path/'second',iterations=1,proposal_model='surface-vector',
        geometry_policy=tmp_path/'geometry.json',resume_from=tmp_path/'first')
    assert a['plane_guidance']==b['plane_guidance']=='minimum-envelope'
    assert read(tmp_path/'first/request.json')['plane_guidance']=='minimum-envelope'
    assert a['original_selected'] and b['original_selected'] and a['sampled_geometry_conditions_pass'] and b['sampled_geometry_conditions_pass']
    assert sha256(source)==before and not b['quality_approved']


def test_envelope_flag_requires_the_surface_solver_before_reading_inputs(tmp_path):
    with pytest.raises(ValueError,match='surface-vector'):
        fit(tmp_path/'missing',tmp_path/'missing',tmp_path/'output',plane_guidance='minimum-envelope')
    assert not (tmp_path/'output').exists()
