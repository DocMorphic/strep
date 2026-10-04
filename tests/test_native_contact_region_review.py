"""Whole-region exposure, persistent material references and source integrity."""
import copy
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_contact_region_review as review
from native_surface_contact import normals
from native_scene_contacts import SceneContacts
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from strep import read,save,sha256
from test_native_scene_contacts import setup


def fixture(tmp_path,*,mode='touch',copies=1,lower=.05):
    source,rig,reader,spec=setup(tmp_path,mode=mode)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    primitive=document['meshes'][0]['primitives'][0]
    for index in range(copies):
        other=copy.deepcopy(primitive)
        other['attributes']['POSITION']=append_accessor(document,binary,rig.primitives[0]['positions']+[0.,-lower,0.],'VEC3')
        document['meshes'][0]['primitives'].append(other)
    write_glb(source,document,binary);spec['actors']['A']['sha256']=sha256(source)
    path=tmp_path/'contacts.json';save(path,spec);scene=SceneContacts(spec,tmp_path)
    policy=dict(schema='strep-native-contact-region-review-v1',contacts_sha256=sha256(path),
        maximum_surface_pose_queries=2000,maximum_candidate_curve_values=2000000,
        limits=dict(support_band_m=.001,maximum_candidate_normal_angle_degrees=20.,minimum_normal_area_m2=1e-14,minimum_normal_coherence=.1),
        contacts={row['id']:dict(source_vertices=scene.actors[row['actor']]['skin'].vertex_references.tolist()) for row in spec['contacts']})
    return source,path,spec,scene,policy


def test_inner_point_contact_pass_is_not_an_exposed_region(tmp_path):
    _,path,spec,scene,policy=fixture(tmp_path)
    before=copy.deepcopy(spec);result,arrays=review.evaluate(scene,policy,sha256(path))
    side=result['contacts'][0]['sides'][0]
    assert result['point_contacts_pass'] and not result['contacts'][0]['original_points_exposed']
    assert side['declared_region_vertices']==6 and side['maximum_front_extent_m']==pytest.approx(.05,abs=1e-8)
    candidates=side['candidates'][0]
    assert candidates['vertices']==[[6,1,0],[6,1,1],[6,1,2]]
    assert candidates['requires_author_selection'] and candidates['eligible_at_every_original_contact_time']
    assert spec==before and result['original_contact_limits_unchanged'] and not result['original_intent_changed']
    assert not any(result[k] for k in ('collision_verified','quality_approved','training_admitted','release_approved'))
    assert arrays['contact_0_source_point_0_reference_shift_m'].shape==(1,3)


def test_exposed_point_keeps_original_intent_even_when_other_points_are_offered(tmp_path):
    _,path,_,scene,policy=fixture(tmp_path,lower=0.)
    result,_=review.evaluate(scene,policy,sha256(path))
    assert result['contacts'][0]['original_points_exposed']
    assert result['contacts'][0]['sides'][0]['candidates'][0]['count']==6
    assert result['original_selected'] and result['anatomical_review_pending']


def test_all_hold_clocks_and_persistent_reference_shift_curves_survive(tmp_path):
    _,path,_,scene,policy=fixture(tmp_path,mode='hold')
    result,arrays=review.evaluate(scene,policy,sha256(path));_,original=scene.evaluate()
    np.testing.assert_array_equal(arrays['contact_0_times_s'],original['contact_0_times_s'])
    count=len(original['contact_0_times_s']);side=result['contacts'][0]['sides'][0]
    assert len(side['samples'])==count and result['surface_pose_queries']==count
    assert side['candidates'][0]['count']==3
    assert arrays['contact_0_source_point_0_reference_shift_m'].shape==(count,3)
    np.testing.assert_allclose(np.max(arrays['contact_0_source_point_0_reference_shift_m'],axis=0),side['candidates'][0]['maximum_reference_shift_m'],atol=0,rtol=0)


def test_per_frame_vertex_switching_is_not_a_persistent_contact_candidate(tmp_path):
    _,path,_,scene,policy=fixture(tmp_path,mode='hold')
    def changed(name,time):
        actor=scene.actors[name];p,r=actor['placement'];v=actor['rig'].vertices(actor['sampler'].sample(time))@r.T+p
        if time>1.:v[3:,1]+=.1
        return v
    result,arrays=review.evaluate(scene,policy,sha256(path),actor_vertices=changed)
    side=result['contacts'][0]['sides'][0]
    assert side['candidates'][0]['count']==0 and not side['original_point_exposed_at_every_time']
    assert arrays['contact_0_source_point_0_reference_shift_m'].shape==(len(arrays['contact_0_times_s']),0)
    assert any(s['points'][0]['envelope']['eligible_vertices']==[0,1,2] for s in side['samples'])


def test_partner_regions_follow_both_actor_placements_without_anatomy_assumptions(tmp_path):
    source,path,spec,scene,policy=fixture(tmp_path)
    spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    q=Rotation.from_euler('z',180,degrees=True);point=scene.actor_points('A',[0],[1.])[0,0]
    spec['actors']['B']['placement']=dict(translation_m=(point-q.apply(point)).tolist(),rotation_xyzw=q.as_quat().tolist())
    row=spec['contacts'][0];row['target']=dict(space='actor',actor='B',vertices=row['vertices'],reduction=row['reduction'])
    save(path,spec);scene=SceneContacts(spec,tmp_path);policy['contacts_sha256']=sha256(path)
    policy['contacts'][row['id']]['partner_vertices']=scene.actors['B']['skin'].vertex_references.tolist()
    result,_=review.evaluate(scene,policy,sha256(path));sides=result['contacts'][0]['sides']
    assert len(sides)==2 and result['surface_pose_queries']==2 and result['point_contacts_pass']
    assert [s['maximum_front_extent_m'] for s in sides]==pytest.approx([.05,.05],abs=1e-8)
    np.testing.assert_allclose(sides[0]['samples'][0]['points'][0]['normal_world'],-np.array(sides[1]['samples'][0]['points'][0]['normal_world']),atol=1e-12)


def test_large_explicit_region_and_candidate_population_are_not_truncated(tmp_path):
    _,path,_,scene,policy=fixture(tmp_path,copies=100,lower=0.)
    result,arrays=review.evaluate(scene,policy,sha256(path));side=result['contacts'][0]['sides'][0]
    assert side['declared_region_vertices']==303 and side['candidates'][0]['count']==303
    assert len(arrays['contact_0_source_point_0_candidate_ids'])==303
    assert not side['candidates'][0]['directly_encodable_as_one_contact']


@pytest.mark.parametrize('fault',['partial','nan','contact-mismatch'])
def test_incomplete_or_inconsistent_full_surface_rejects(tmp_path,fault):
    _,path,_,scene,policy=fixture(tmp_path)
    def broken(name,time):
        actor=scene.actors[name];p,r=actor['placement'];v=actor['rig'].vertices(actor['sampler'].sample(time))@r.T+p
        if fault=='partial':return v[:-1]
        if fault=='nan':v[-1,0]=np.nan
        if fault=='contact-mismatch':v[0,0]+=.01
        return v
    with pytest.raises(ValueError):review.evaluate(scene,policy,sha256(path),actor_vertices=broken)


@pytest.mark.parametrize('budget',['pose','curve'])
def test_budget_refuses_entire_population_before_a_surface_query(tmp_path,budget):
    _,path,_,scene,policy=fixture(tmp_path,mode='hold')
    policy['maximum_surface_pose_queries' if budget=='pose' else 'maximum_candidate_curve_values']=1
    def forbidden(*args):raise AssertionError('partial surface evaluation ran')
    with pytest.raises(ValueError,match='population exceeds budget'):
        review.evaluate(scene,policy,sha256(path),actor_vertices=forbidden)


@pytest.mark.parametrize('fault',['binding','missing-contact','missing-original','duplicate','unknown','boolean-ref','unknown-limit','negative-band','angle','pose-bool','curve-bool'])
def test_invalid_or_rebound_region_request_rejects(tmp_path,fault):
    _,path,_,scene,policy=fixture(tmp_path);item=next(iter(policy['contacts'].values()))
    if fault=='binding':policy['contacts_sha256']='wrong'
    if fault=='missing-contact':policy['contacts'].clear()
    if fault=='missing-original':item['source_vertices']=item['source_vertices'][1:]
    if fault=='duplicate':item['source_vertices'][-1]=item['source_vertices'][0]
    if fault=='unknown':item['source_vertices'][-1]=[9,9,9]
    if fault=='boolean-ref':item['source_vertices'][0][2]=False
    if fault=='unknown-limit':policy['limits']['extra']=1.
    if fault=='negative-band':policy['limits']['support_band_m']=-.1
    if fault=='angle':policy['limits']['maximum_candidate_normal_angle_degrees']=91.
    if fault=='pose-bool':policy['maximum_surface_pose_queries']=True
    if fault=='curve-bool':policy['maximum_candidate_curve_values']=True
    with pytest.raises(ValueError):review.policy_for(policy,scene,sha256(path))


def test_vectorized_incidence_matches_scalar_oracle_with_degenerate_and_cancelled_faces():
    vertices=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1],[2,2,2]])
    faces=np.array([[0,1,2],[0,3,1],[0,2,3],[0,0,1],[1,2,3],[1,3,2]])
    unit,available=review.vertex_normals(vertices,faces,1e-14,.1)
    oracle=normals(vertices,faces,[[i] for i in range(len(vertices))],minimum_area=1e-14,minimum_coherence=.1)
    assert available.tolist()==[r['available'] for r in oracle]
    for i,row in enumerate(oracle):
        if row['available']:np.testing.assert_allclose(unit[i],row['normal_world'],atol=1e-15,rtol=0)
        else:np.testing.assert_array_equal(unit[i],0.)


def test_centroid_uses_union_of_faces_not_average_vertex_normals(tmp_path):
    _,path,spec,_,policy=fixture(tmp_path)
    row=spec['contacts'][0];row['vertices']=[[6,0,0],[6,0,1]];row['reduction']='centroid'
    scene=SceneContacts(spec,tmp_path);row['target']['points_m']=[scene.actor_points('A',[0,1],[1.])[0].mean(0).tolist()]
    save(path,spec);scene=SceneContacts(spec,tmp_path);policy['contacts_sha256']=sha256(path)
    result,_=review.evaluate(scene,policy,sha256(path));side=result['contacts'][0]['sides'][0]
    assert len(side['samples'][0]['points'])==1 and side['candidates'][0]['count']==3
    assert result['point_contacts_pass']


def test_wrapper_snapshots_and_full_array_readback_preserve_originals(tmp_path):
    source,path,spec,scene,policy=fixture(tmp_path);policy_path=tmp_path/'region-policy.json';save(policy_path,policy)
    bindings={str(p):sha256(p) for p in (source,path,policy_path)};out=tmp_path/'review'
    result=review.run(path,policy_path,out)
    assert result['status']=='complete' and result['arrays_roundtrip_exact']
    assert result['inputs_sha256']==bindings and all(sha256(p)==h for p,h in bindings.items())
    assert all(sha256(out/result['source_snapshots'][p]['path'])==h for p,h in bindings.items())
    assert all(sha256(out/'implementation'/n)==h for n,h in result['implementation_sha256'].items())
    with pytest.raises(ValueError,match='Fresh'):review.run(path,policy_path,out)


def test_failed_budget_job_is_retained_and_cannot_be_overwritten(tmp_path):
    _,path,_,_,policy=fixture(tmp_path,mode='hold');policy['maximum_surface_pose_queries']=1
    p=tmp_path/'policy.json';save(p,policy);out=tmp_path/'failed'
    with pytest.raises(ValueError,match='population exceeds budget'):review.run(path,p,out)
    assert read(out/'pipeline.json')['status']=='failed' and (out/'request.json').exists()
    assert not (out/'result.json').exists()
    with pytest.raises(ValueError,match='Fresh'):review.run(path,p,out)


def test_input_mutation_during_review_preserves_failed_attempt(tmp_path,monkeypatch):
    _,path,_,_,policy=fixture(tmp_path);p=tmp_path/'policy.json';save(p,policy);out=tmp_path/'mutated'
    original=review.evaluate
    def mutate(*args,**kwargs):
        result=original(*args,**kwargs);p.write_bytes(p.read_bytes()+b'\n');return result
    monkeypatch.setattr(review,'evaluate',mutate)
    with pytest.raises(ValueError,match='source changed'):review.run(path,p,out)
    assert read(out/'pipeline.json')['status']=='failed' and (out/'observations.npz').exists()


def test_method_mutation_during_review_preserves_failed_attempt(tmp_path,monkeypatch):
    _,path,_,_,policy=fixture(tmp_path);p=tmp_path/'policy.json';save(p,policy);out=tmp_path/'method-mutated'
    root=tmp_path/'methods';(root/'scripts').mkdir(parents=True)
    for name in review.METHODS:shutil.copyfile(review.ROOT/'scripts'/name,root/'scripts'/name)
    monkeypatch.setattr(review,'ROOT',root);original=review.evaluate
    changed=root/'scripts'/'native_contact_region_review.py';before=sha256(changed)
    def mutate(*args,**kwargs):
        result=original(*args,**kwargs);changed.write_bytes(changed.read_bytes()+b'\n');return result
    monkeypatch.setattr(review,'evaluate',mutate)
    with pytest.raises(ValueError,match='methods changed'):review.run(path,p,out)
    assert read(out/'pipeline.json')['status']=='failed' and (out/'observations.npz').exists()
    assert sha256(out/'implementation'/changed.name)==before and sha256(changed)!=before
    assert not (out/'result.json').exists()
