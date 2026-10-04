"""Synthetic imported observations only; no real engine or human evidence."""
from pathlib import Path
from types import SimpleNamespace
import copy
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import save, read, sha256
import native_object_scene_surface as surface
from native_surface_contact import evaluate, normals
from native_scene_contacts import SceneContacts
from test_native_surface_contact import scene_fixture, policy


def observed(scene, rotation=0):
    def vertices(name, time):
        a=scene.actors[name];p,r=a['placement']
        points=a['rig'].vertices(a['sampler'].sample(time))@r.T+p
        pivot=points[scene.rows[0]['ids'][0]]
        return Rotation.from_euler('x',rotation,degrees=True).apply(points-pivot)+pivot
    actor=SimpleNamespace(actor_vertices=vertices,
        actor_points=lambda name,ids,times:np.array([vertices(name,float(t))[ids] for t in times]))
    return actor,SimpleNamespace(object_poses=scene.object_poses)


@pytest.mark.parametrize('rotation,passed',[(0,True),(180,False)])
def test_point_and_normal_observations_use_imported_skin_together(tmp_path,rotation,passed):
    _,_,_,spec,path,scene=scene_fixture(tmp_path);p=policy(path,spec)
    actor,objects=observed(scene,rotation)
    imported=surface.ImportedContactScene(scene,actor,objects)
    result,arrays=evaluate(imported,p,sha256(path),actor_vertices=actor.actor_vertices,object_poses=objects.object_poses)
    assert result['point_contacts_pass'] and result['surface_contacts_pass']==passed
    expected=0 if passed else 180
    assert result['contacts'][0]['samples'][0]['points'][0]['opposition_error_degrees']==pytest.approx(expected)
    np.testing.assert_allclose(arrays['contact_0_source_normals_world'][0,0], [0,-1 if passed else 1,0],atol=1e-12)


def test_imported_object_pose_changes_contact_and_normal_target_in_same_epoch(tmp_path):
    _,rig,reader,spec,path,scene=scene_fixture(tmp_path)
    point=rig.vertices(reader.sample(1.))[0]
    spec['objects']['item']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2),
        keyframes=[dict(time_s=t,translation_m=(point-[0,.2,0]).tolist(),rotation_xyzw=[0.,0.,0.,1.]) for t in [0.,2.]])
    spec['contacts'][0]['target']=dict(space='object',object='item',points_m=[[0.,.2,0.]])
    save(path,spec);scene=SceneContacts(spec,tmp_path);p=policy(path,spec);actor,objects=observed(scene)
    def imported_pose(name,times):
        pos,rot=scene.object_poses(name,times);pos[:,0]+=.1
        return pos,rot
    objects.object_poses=imported_pose
    imported=surface.ImportedContactScene(scene,actor,objects)
    result,_=evaluate(imported,p,sha256(path),actor_vertices=actor.actor_vertices,object_poses=objects.object_poses)
    assert not result['point_contacts_pass'] and not result['surface_contacts_pass']
    assert result['contacts'][0]['contact_points_pass'] is False


def complete_fixture(tmp_path,monkeypatch):
    from test_native_object_bounded_scene import inputs
    from native_object_bounded_scene import run
    fit,handoff,engine=inputs(tmp_path,monkeypatch)
    folder=tmp_path/'scene';base=run(fit,handoff,folder,engine)
    assert base['bounded_scene_conditions_pass']
    request=read(folder/'request.json');scene=SceneContacts(read(request['contacts']),Path(request['contacts']).parent)
    contacts={}
    for entry in scene.rows:
        row=entry['authored'];a=scene.actors[row['actor']];time=row.get('time_s',row.get('interval_s',[0])[0])
        p,r=a['placement'];v=a['rig'].vertices(a['sampler'].sample(time))@r.T+p
        from native_scene_geometry import faces_for
        groups=[entry['ids']] if row['reduction']=='centroid' else [[int(i)] for i in entry['ids']]
        ns=normals(v,faces_for(a['rig'])[0],groups,minimum_area=1e-14,minimum_coherence=.1)
        assert all(n['available'] for n in ns)
        _,rotation=scene.object_poses(row['target']['object'],[time])
        target=(-np.array([n['normal_world'] for n in ns])@rotation[0]).tolist()
        contacts[row['id']]=dict(target_normal=dict(space='object',normals=target))
    policy_path=tmp_path/'surface-policy.json'
    save(policy_path,dict(schema='strep-native-surface-contact-v1',contacts_sha256=sha256(request['contacts']),
        maximum_actor_pose_queries=20000,limits=dict(maximum_opposition_error_degrees=15.,backface_allowance_m=.0005,
        minimum_normal_area_m2=1e-14,minimum_normal_coherence=.1),contacts=contacts))
    return folder,policy_path


def test_complete_audit_keeps_original_scene_and_records_additional_failure(tmp_path,monkeypatch):
    folder,p=complete_fixture(tmp_path,monkeypatch);before=sha256(folder/'result.json')
    result=surface.run(folder,p,tmp_path/'surface')
    assert result['surface_conditions_pass']['native-authoring'] and result['sampled_scene_and_surface_conditions_pass']
    assert not result['surface_conditions_pass']['default-import']
    assert result['original_selected'] and not result['quality_approved'] and not result['geometry_queries_rerun']
    assert sha256(folder/'result.json')==before
    for n,h in result['files_sha256'].items():assert sha256(tmp_path/'surface'/n)==h
    bad=read(p)
    for item in bad['contacts'].values():item['target_normal']['normals']=(-np.array(item['target_normal']['normals'])).tolist()
    save(tmp_path/'opposite.json',bad)
    rejected=surface.run(folder,tmp_path/'opposite.json',tmp_path/'rejected')
    assert rejected['original_sampled_scene_conditions_pass'] and not rejected['sampled_scene_and_surface_conditions_pass']
    assert not rejected['surface_conditions_pass']['native-authoring'] and rejected['original_selected']
    assert sha256(folder/'result.json')==before
    with pytest.raises(ValueError,match='Fresh'):surface.run(folder,p,tmp_path/'surface')
    # Added surface success cannot approve a failed earlier scene decision.
    original_bound=surface._bound_scene
    def failed_base(path):
        request,base,*observations=original_bound(path)
        base=copy.deepcopy(base);base['bounded_scene_conditions_pass']=False
        return request,base,*observations
    monkeypatch.setattr(surface,'_bound_scene',failed_base)
    inherited=surface.run(folder,p,tmp_path/'failed-base')
    assert inherited['surface_conditions_pass']['native-authoring']
    assert not inherited['original_sampled_scene_conditions_pass'] and not inherited['sampled_scene_and_surface_conditions_pass']


@pytest.mark.parametrize('failure',['changed_file','changed_method','extra_file','pending'])
def test_bound_scene_transport_failures_reject_before_normal_measurement(tmp_path,monkeypatch,failure):
    # This preflight ends before loading producers. No fabricated engine result is accepted.
    folder=tmp_path/'scene';(folder/'implementation').mkdir(parents=True)
    for n in surface.BOUND_METHODS:
        (folder/'implementation'/n).write_bytes((surface.ROOT/'scripts'/n).read_bytes())
    methods={n:sha256(folder/'implementation'/n) for n in surface.BOUND_METHODS}
    save(folder/'pipeline.json',dict(status='processing' if failure=='pending' else 'complete'))
    save(folder/'request.json',dict(schema=surface.BOUND_SCHEMA))
    result=dict(status='complete',schema=surface.BOUND_SCHEMA,implementation_sha256=methods,
        files_sha256={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file() and p.name!='pipeline.json'})
    save(folder/'result.json',result)
    if failure=='changed_file':(folder/'request.json').write_bytes(b'changed')
    if failure=='changed_method':(folder/'implementation'/surface.BOUND_METHODS[0]).write_bytes(b'changed')
    if failure=='extra_file':(folder/'unbound.txt').write_text('unbound fixture')
    with pytest.raises((ValueError,__import__('json').JSONDecodeError)):surface.bound_scene(folder)
