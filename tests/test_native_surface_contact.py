"""Explicit surface normals, target coordinates and retained audit evidence."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_surface_contact import normals,policy_for,evaluate,run
from native_scene_contacts import SceneContacts
from test_native_scene_contacts import setup
from strep import save,read,sha256


def policy(path,spec):
    targets={}
    for row in spec['contacts']:
        space=row['target']['space']
        targets[row['id']]=dict(target_normal=dict(space='partner-surface') if space=='actor' else dict(space=space,normals=[[0.,1.,0.]]))
    return dict(schema='strep-native-surface-contact-v1',contacts_sha256=sha256(path),maximum_actor_pose_queries=2000,
        limits=dict(maximum_opposition_error_degrees=15.,backface_allowance_m=.0005,minimum_normal_area_m2=1e-14,minimum_normal_coherence=.1),contacts=targets)


def scene_fixture(tmp_path):
    source,rig,reader,spec=setup(tmp_path,mode='touch');path=tmp_path/'contacts.json';save(path,spec)
    return source,rig,reader,spec,path,SceneContacts(spec,tmp_path)


def test_incident_faces_count_once_for_centroid_and_preserve_winding():
    p=np.array([[0.,0,0],[1,0,0],[0,1,0]]);f=np.array([[0,1,2]])
    a=normals(p,f,[[0,1]],minimum_area=1e-14,minimum_coherence=.1)[0]
    assert a['available'] and a['incident_faces']==[0] and a['summed_twice_area_m2']==1
    np.testing.assert_array_equal(a['normal_world'],[0,0,1])
    b=normals(p,f[:,::-1],[[0]],minimum_area=1e-14,minimum_coherence=.1)[0]
    np.testing.assert_array_equal(b['normal_world'],[0,0,-1])


@pytest.mark.parametrize('kind',['cancellation','degenerate','unused'])
def test_unreliable_normals_remain_unavailable(kind):
    p=np.array([[0.,0,0],[1,0,0],[0,1,0],[2,2,2]]);f=np.array([[0,1,2]])
    if kind=='cancellation':f=np.array([[0,1,2],[0,2,1]])
    if kind=='degenerate':f=np.array([[0,1,2],[0,0,1]])
    a=normals(p,f,[[3 if kind=='unused' else 0]],minimum_area=1e-14,minimum_coherence=.1)[0]
    assert not a['available'] and a['normal_world'] is None


def test_world_contact_keeps_original_position_and_new_normal_conditions_separate(tmp_path):
    _,_,_,spec,path,scene=scene_fixture(tmp_path);p=policy(path,spec)
    r,a=evaluate(scene,p,sha256(path));assert r['point_contacts_pass'] and r['surface_contacts_pass']
    assert r['actor_pose_queries']==1 and r['new_authored_conditions'] and r['anatomical_review_pending']
    np.testing.assert_allclose(a['contact_0_source_normals_world'],[[[0,-1,0]]],atol=1e-12)
    spec['contacts'][0]['target']['points_m'][0][1]+=.002;spec['contacts'][0]['limits']['position_m']=.01
    save(path,spec);p['contacts_sha256']=sha256(path);r,_=evaluate(SceneContacts(spec,tmp_path),p,sha256(path))
    point=r['contacts'][0]['samples'][0]['points'][0]
    assert r['point_contacts_pass'] and not r['surface_contacts_pass']
    assert point['opposition_error_degrees']==0 and point['source_target_projection_m']==pytest.approx(-.002)
    assert not r['collision_verified'] and not r['quality_approved']


@pytest.mark.parametrize('opposed',[True,False])
def test_partner_normals_derive_from_target_skin_and_pose(tmp_path,opposed):
    _,rig,reader,spec,path,scene=scene_fixture(tmp_path);spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    q=Rotation.from_euler('z',180 if opposed else 0,degrees=True);v=rig.vertices(reader.sample(1.))[0]
    spec['actors']['B']['placement']=dict(rotation_xyzw=q.as_quat().tolist(),translation_m=(v-q.apply(v)).tolist())
    spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    save(path,spec);p=policy(path,spec);r,a=evaluate(SceneContacts(spec,tmp_path),p,sha256(path))
    assert r['point_contacts_pass'] and r['actor_pose_queries']==2
    assert r['surface_contacts_pass']==opposed
    assert r['contacts'][0]['samples'][0]['points'][0]['opposition_error_degrees']==pytest.approx(0 if opposed else 180)
    # Coplanar overlapping triangles still need a separate geometry audit.
    assert not r['collision_verified']


def test_object_normal_uses_rigid_object_coordinates_at_exact_touch_time(tmp_path):
    _,rig,reader,spec,path,scene=scene_fixture(tmp_path);v=rig.vertices(reader.sample(1.))[0]
    q=Rotation.from_euler('z',60,degrees=True);local=np.array([0,.2,0]);position=v-q.apply(local)
    spec['objects']['box']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.4,.4,.4]),keyframes=[
        dict(time_s=t,translation_m=position.tolist(),rotation_xyzw=Rotation.from_euler('z',angle,degrees=True).as_quat().tolist()) for t,angle in [(0.,0),(2.,120)]])
    spec['contacts'][0]['target']=dict(space='object',object='box',points_m=[local.tolist()])
    save(path,spec);p=policy(path,spec);p['limits']['maximum_opposition_error_degrees']=70
    r,a=evaluate(SceneContacts(spec,tmp_path),p,sha256(path));assert r['surface_contacts_pass']
    np.testing.assert_allclose(a['contact_0_target_normals_world'][0,0],q.apply([0,1,0]),atol=1e-12)
    assert r['contacts'][0]['samples'][0]['points'][0]['opposition_error_degrees']==pytest.approx(60)


def test_centroid_uses_union_of_incident_faces_and_all_hold_clocks(tmp_path):
    _,rig,reader,spec,path,scene=scene_fixture(tmp_path);row=spec['contacts'][0]
    row.update(mode='hold',interval_s=[.8,1.2],limits=dict(position_m=1e-6,relative_speed_m_s=1e-6),vertices=[[6,0,0],[6,0,1]],reduction='centroid')
    row['target']['points_m']=[rig.vertices(reader.sample(1.))[:2].mean(0).tolist()]
    save(path,spec);p=policy(path,spec);scene=SceneContacts(spec,tmp_path)
    r,a=evaluate(scene,p,sha256(path));_,clocks=scene.evaluate()
    np.testing.assert_array_equal(a['contact_0_times_s'],clocks['contact_0_times_s'])
    assert r['surface_contacts_pass'] and r['actor_pose_queries']==len(a['contact_0_times_s'])
    for s in r['contacts'][0]['samples']:assert s['points'][0]['source_normal']['incident_faces']==[0]


@pytest.mark.parametrize('fault',['binding','omitted','normal','coordinate','budget','angle','area','coherence','extra'])
def test_invalid_policies_reject_without_hidden_defaults(tmp_path,fault):
    _,_,_,spec,path,scene=scene_fixture(tmp_path);p=policy(path,spec);item=p['contacts'][spec['contacts'][0]['id']]['target_normal']
    if fault=='binding':p['contacts_sha256']='0'*64
    if fault=='omitted':p['contacts']={}
    if fault=='normal':item['normals']=[[0,2,0]]
    if fault=='coordinate':item['space']='object'
    if fault=='budget':p['maximum_actor_pose_queries']=True
    if fault=='angle':p['limits']['maximum_opposition_error_degrees']=91
    if fault=='area':p['limits']['minimum_normal_area_m2']=0
    if fault=='coherence':p['limits']['minimum_normal_coherence']=0
    if fault=='extra':item['default']=True
    with pytest.raises(ValueError):policy_for(p,scene,sha256(path))


def test_full_actor_population_and_budget_required(tmp_path):
    _,_,_,spec,path,scene=scene_fixture(tmp_path);p=policy(path,spec)
    with pytest.raises(ValueError,match='population'):evaluate(scene,p,sha256(path),actor_vertices=lambda *a:np.zeros((1,3)))
    spec['actors']['B']=copy.deepcopy(spec['actors']['A']);spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    save(path,spec);p=policy(path,spec);p['maximum_actor_pose_queries']=1
    with pytest.raises(ValueError,match='budget'):evaluate(SceneContacts(spec,tmp_path),p,sha256(path))


def test_fresh_audit_snapshots_sources_methods_and_keeps_unapproved(tmp_path):
    source,_,_,spec,path,scene=scene_fixture(tmp_path);p=policy(path,spec);policy_path=tmp_path/'policy.json';save(policy_path,p)
    before=sha256(source);out=tmp_path/'audit';r=run(path,policy_path,out)
    assert r['surface_contacts_pass'] and r['original_selected'] and not r['quality_approved']
    assert sha256(source)==before
    for name,h in r['implementation_sha256'].items():assert sha256(out/'implementation'/name)==h
    for name,e in r['source_snapshots'].items():assert sha256(out/e['path'])==e['sha256']==sha256(name)
    assert r['observations_sha256']==sha256(out/'observations.npz')
    with pytest.raises(ValueError,match='Fresh'):run(path,policy_path,out)


def test_method_mutation_leaves_failed_pipeline_and_no_result(tmp_path,monkeypatch):
    import native_surface_contact as audit
    _,_,_,spec,path,scene=scene_fixture(tmp_path);policy_path=tmp_path/'policy.json';save(policy_path,policy(path,spec));out=tmp_path/'audit'
    original=audit.evaluate
    def changed(*args):
        result=original(*args);file=out/'implementation/native_surface_contact.py';file.write_bytes(file.read_bytes()+b'\n');return result
    monkeypatch.setattr(audit,'evaluate',changed)
    with pytest.raises(ValueError,match='method'):run(path,policy_path,out)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()


def fit_fixture(tmp_path,*,wrong_normal=False):
    from test_native_scene_fit import prepare
    source,spec,contacts,p,permissions,_,_=prepare(tmp_path)
    spec['contacts'][0]['target']['points_m'][0][1]-=.002;save(contacts,spec)
    p['contacts_sha256']=sha256(contacts);save(permissions,p)
    target_policy=policy(contacts,spec)
    if wrong_normal:target_policy['contacts'][spec['contacts'][0]['id']]['target_normal']['normals']=[[0.,-1.,0.]]
    surface_path=tmp_path/'surface-policy.json';save(surface_path,target_policy)
    return source,contacts,permissions,surface_path


@pytest.mark.parametrize('wrong_normal',[False,True])
def test_fit_final_surface_filter_cannot_pass_only_on_point_distance(tmp_path,wrong_normal):
    from native_scene_fit import run as fit
    source,contacts,permissions,surface_path=fit_fixture(tmp_path,wrong_normal=wrong_normal);before=sha256(source);out=tmp_path/'fit'
    r=fit(contacts,permissions,out,surface_contact_policy=surface_path)
    assert r['point_and_motion_constraints_pass']
    assert r['native_constraints_pass']==(not wrong_normal)==r['surface_contact_conditions_pass']
    assert r['original_selected'] and not r['release_approved'] and sha256(source)==before
    assert r['surface_contact_result_sha256']==sha256(out/'surface-contact-audit/result.json')
    assert read(out/'request.json')['surface_contact_policy_sha256']==sha256(surface_path)
    assert read(out/'surface-contact-audit/policy.json')['contacts_sha256']==sha256(out/'proposal/contacts.json')


@pytest.mark.parametrize('fault',['omit','change','archive'])
def test_resume_cannot_drop_change_or_corrupt_added_surface_conditions(tmp_path,fault):
    from native_scene_fit import run as fit
    source,c,p,policy_path=fit_fixture(tmp_path);first=tmp_path/'first';fit(c,p,first,surface_contact_policy=policy_path)
    argument=policy_path
    if fault=='omit':argument=None
    if fault=='change':
        value=read(policy_path);value['limits']['maximum_opposition_error_degrees']=20.;save(policy_path,value)
    if fault=='archive':
        path=first/'surface-contact-policy.json';path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='surface contact policy'):
        fit(c,p,tmp_path/'second',resume_from=first,surface_contact_policy=argument)
    assert not (tmp_path/'second').exists()


def test_resume_retains_exact_added_surface_policy_and_original_caps(tmp_path):
    from native_scene_fit import run as fit
    _,c,p,policy_path=fit_fixture(tmp_path);first=tmp_path/'first';fit(c,p,first,surface_contact_policy=policy_path)
    second=tmp_path/'second';r=fit(c,p,second,resume_from=first,surface_contact_policy=policy_path)
    assert r['native_constraints_pass'] and r['surface_contact_conditions_pass']
    with np.load(first/'source-rate-caps.npz') as a,np.load(second/'source-rate-caps.npz') as b:
        assert set(a.files)==set(b.files)
        for k in a.files:np.testing.assert_array_equal(a[k],b[k])


def test_added_surface_policy_mutation_fails_the_fit_even_after_audit(tmp_path,monkeypatch):
    import native_surface_contact as audit
    from native_scene_fit import run as fit
    _,c,p,policy_path=fit_fixture(tmp_path);out=tmp_path/'fit';original=audit.evaluate
    def changed(*args):
        result=original(*args);policy_path.write_bytes(policy_path.read_bytes()+b'\n');return result
    monkeypatch.setattr(audit,'evaluate',changed)
    with pytest.raises(ValueError,match='input changed'):fit(c,p,out,surface_contact_policy=policy_path)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()
