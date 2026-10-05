"""Actual tiny skin decoding; engine subprocess fixtures are explicitly mocked."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_imported_surface_contact as audit
from native_scene_contacts import SceneContacts
from native_scene_engine import EngineObservations,sample_times,run as actor_run
from native_object_scene_engine import CombinedObservations
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import read,save,sha256
from test_native_scene_contacts import setup
from test_native_scene_engine import mock_actor,serialized
from test_native_scene_geometry import policy as geometry_policy
from test_native_surface_contact import policy as surface_policy
from test_native_object_scene_engine import producers


def observations(scene,*,shift=0.,reverse=False):
    _,arrays = scene.evaluate(); times = sample_times(scene,arrays); cases=[]; raw=[]
    for name,entry in scene.actors.items():
        case = dict(id=name,path='fixture-'+name+'.glb',animation_index=entry['animation_index']); cases.append(case)
        row = mock_actor(entry['rig'],entry['sampler'],times,path=case['path'],reverse=reverse); row['id']=name
        for frame in row['frames']:
            for matrix in frame['bones']: matrix[3][1] += shift
        raw.append(row)
    props = []
    for name in scene.objects:
        p,r = scene.object_poses(name,times); frames=[]
        for t,v,m in zip(times,p,r):
            world = np.eye(4); world[:3,:3]=m; world[:3,3]=v
            frames.append(dict(requested_time_s=t,matrix=serialized(world),rotation_xyzw=Rotation.from_matrix(m).as_quat().tolist()))
        props.append(dict(id=name,frames=frames))
    return EngineObservations(scene,dict(cases=raw,objects=props),cases,times)


def simple(tmp_path,*,shift=0.,reverse=False,partner=False,mode='touch'):
    source,rig,reader,spec = setup(tmp_path,mode=mode)
    if partner:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
        q = Rotation.from_euler('z',180,degrees=True); v = rig.vertices(reader.sample(1.))[0]
        spec['actors']['B']['placement'] = dict(rotation_xyzw=q.as_quat().tolist(),translation_m=(v-q.apply(v)).tolist())
        spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    path = tmp_path/'contacts.json'; save(path,spec); scene = SceneContacts(spec,tmp_path)
    return path,spec,scene,surface_policy(path,spec),observations(scene,shift=shift,reverse=reverse)


@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('partner',[False,True])
def test_world_and_partner_normals_preserve_canonical_winding(tmp_path,reverse,partner):
    path,_,scene,policy,actor = simple(tmp_path,reverse=reverse,partner=partner)
    result,arrays = audit.evaluate(scene,policy,sha256(path),actor,{'native-authoring':actor})
    assert result['native_and_imported_surface_contacts_pass']
    assert result['counts']['source-native'] == result['counts']['native-authoring']
    assert result['reports']['native-authoring']['actor_pose_queries'] == 1+int(partner)
    for suffix in ('times_s','source_normals_world','target_normals_world','normal_available'):
        np.testing.assert_array_equal(arrays['source-native_contact_0_'+suffix],arrays['native-authoring_contact_0_'+suffix])
    assert not any(result[k] for k in ('engine_executed','geometry_queries_rerun','collision_verified',
        'native_rate_caps_checked','real_time_playback_verified','quality_approved','release_approved'))


@pytest.mark.parametrize('shift,side_fail',[(.002,False),(-.002,True)])
def test_imported_points_and_normals_share_actual_trajectory_not_source_points(tmp_path,shift,side_fail):
    path,_,scene,policy,actor = simple(tmp_path,shift=shift)
    result,_ = audit.evaluate(scene,policy,sha256(path),actor,{'native-authoring':actor})
    assert result['reports']['source-native']['surface_contacts_pass']
    measured = result['reports']['native-authoring']
    assert not measured['point_contacts_pass'] and not result['native_and_imported_surface_contacts_pass']
    assert result['counts']['native-authoring']['failed_orientation_or_side_points'] == int(side_fail)
    point = measured['contacts'][0]['samples'][0]['points'][0]
    assert point['source_target_projection_m'] == pytest.approx(shift)
    assert not measured['raw_imported_weights_renormalized']


def test_actual_object_rotation_changes_normal_even_when_grip_point_still_meets(tmp_path):
    path,spec,scene,policy,_ = simple(tmp_path); point = np.array(spec['contacts'][0]['target']['points_m'][0]); local = np.array([0.,.2,0.])
    spec['objects']['item'] = dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2),
        keyframes=[dict(time_s=t,translation_m=(point-local).tolist(),rotation_xyzw=[0,0,0,1]) for t in [0.,2.]])
    spec['contacts'][0]['target'] = dict(space='object',object='item',points_m=[local.tolist()])
    save(path,spec); scene = SceneContacts(spec,tmp_path); policy = surface_policy(path,spec); actor = observations(scene)
    q = Rotation.from_euler('z',180,degrees=True)
    def raw(changed):
        return dict(item=[dict(time_s=t,translation_m=(point-(q.apply(local) if changed else local)).tolist(),
                              rotation_xyzw=q.as_quat().tolist() if changed else [0,0,0,1]) for t in actor.times])
    providers = {mode:CombinedObservations(scene,actor,raw(mode=='native-authoring'),actor.times)
                 for mode in ('default-import','native-authoring')}
    result,arrays = audit.evaluate(scene,policy,sha256(path),actor,providers)
    assert result['default_comparison_preserved'] and result['counts']['default-import']['surface_contacts_pass']
    assert result['counts']['native-authoring']['point_contacts_pass']
    assert result['counts']['native-authoring']['failed_orientation_or_side_points'] == 1
    assert result['reports']['native-authoring']['contacts'][0]['samples'][0]['points'][0]['opposition_error_degrees'] == pytest.approx(180.)
    assert not result['native_and_imported_surface_contacts_pass']
    np.testing.assert_allclose(arrays['native-authoring_contact_0_target_normals_world'],[[[0,-1,0]]],atol=1e-12)


@pytest.mark.parametrize('fault',['mode','scene','clock','vertices','budget'])
def test_incomplete_mixed_or_excessive_observations_reject(tmp_path,fault,monkeypatch):
    path,spec,scene,policy,actor = simple(tmp_path); providers={'native-authoring':actor}
    if fault == 'mode': providers = {}
    elif fault == 'scene': actor.scene = SceneContacts(spec,tmp_path)
    elif fault == 'clock': actor.times = np.array([0.,2.])
    elif fault == 'vertices': monkeypatch.setattr(actor,'actor_vertices',lambda *a:np.zeros((1,3)))
    else: policy['maximum_actor_pose_queries'] = 0
    with pytest.raises(ValueError): audit.evaluate(scene,policy,sha256(path),actor,providers)


def actor_producer(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'fixture-lock')
    path,spec,_,sp,_ = simple(tmp_path)
    gp = tmp_path/'geometry.json'; save(gp,geometry_policy(path))
    pp = tmp_path/'surface.json'; save(pp,sp)
    engine = tmp_path/'mock-engine'; engine.write_bytes(b'engine observations are a test double')
    def execute(command,**kwargs):
        request = read(command[-2]); cases=[]
        for case in request['cases']:
            rig = RigAsset.load(case['path']); sampler = NativeSupportSampler(rig.document,rig.binary,case['animation_index'])
            row = mock_actor(rig,sampler,request['sample_times_s'],path=case['path']); row['id']=case['id']; cases.append(row)
            Path(case['animation_output']).write_bytes(b'explicit mocked actor resource')
        save(command[-1],dict(engine=dict(string='fixture only'),cases=cases,objects=[]))
        return SimpleNamespace(returncode=0)
    import subprocess
    monkeypatch.setattr(subprocess,'run',execute)
    actors = tmp_path/'actors'; actor_run(path,actors,geometry_policy=gp,engine=engine,playback_mode='native-authoring')
    return path,pp,gp,actors


def test_actor_only_file_workflow_replays_every_normal_and_array_without_engine(tmp_path,monkeypatch):
    path,pp,gp,actors = actor_producer(tmp_path,monkeypatch); out = tmp_path/'surface-audit'
    result = audit.run(path,pp,gp,actors,out)
    assert result['native_and_imported_surface_contacts_pass']
    proof = audit.verify(out); assert proof['complete_normals_points_and_decisions_recomputed']
    assert proof['result_sha256'] == sha256(out/'result.json') and not proof['geometry_queries_rerun']
    with pytest.raises(ValueError,match='Fresh'): audit.run(path,pp,gp,actors,out)
    with pytest.raises(ValueError,match='invent'): audit.load(path,gp,actors,tmp_path/'fabricated-object')


def test_bound_object_producers_preserve_default_failures_and_complete_replay(tmp_path,monkeypatch):
    path,gp,actors,objects = producers(tmp_path,monkeypatch); pp = tmp_path/'surface.json'; save(pp,surface_policy(path,read(path)))
    out = tmp_path/'surface-audit'; result = audit.run(path,pp,gp,actors,out,object_dir=objects)
    assert not result['reports']['default-import']['point_contacts_pass']
    assert result['reports']['native-authoring']['point_contacts_pass']
    assert result['default_comparison_preserved']
    assert audit.verify(out)['counts'] == result['counts']
    with pytest.raises(ValueError,match='actual object'): audit.load(path,gp,actors,None)


@pytest.mark.parametrize('fault',['decision','false-type','count-type','normal','array','request','snapshot','method','source','resource','pipeline'])
def test_rebound_or_incomplete_evidence_rejects(tmp_path,monkeypatch,fault):
    path,pp,gp,actors = actor_producer(tmp_path,monkeypatch); out = tmp_path/'surface-audit'; audit.run(path,pp,gp,actors,out)
    result = read(out/'result.json')
    if fault == 'decision': result['native_and_imported_surface_contacts_pass'] = False
    elif fault == 'false-type': result['quality_approved'] = 0
    elif fault == 'count-type': result['counts']['native-authoring']['points'] = 1.
    elif fault == 'normal': result['reports']['native-authoring']['contacts'][0]['samples'][0]['points'][0]['source_normal']['normal_world'][0] = .1
    elif fault == 'array':
        with np.load(out/'observations.npz',allow_pickle=False) as z: arrays={n:z[n].copy() for n in z.files}
        arrays['native-authoring_contact_0_source_normals_world'][0,0,0] += .1
        np.savez_compressed(out/'observations.npz',**arrays); result['observations_sha256']=sha256(out/'observations.npz')
    elif fault == 'request':
        request = read(out/'request.json'); request['engine_observation_times_s'].pop(); save(out/'request.json',request)
        result['request_sha256'] = sha256(out/'request.json')
    elif fault == 'snapshot': next((out/'input').glob('*.glb')).write_bytes(b'changed')
    elif fault == 'method': (out/'implementation/native_imported_surface_contact.py').write_bytes(b'changed')
    elif fault == 'source': pp.write_bytes(pp.read_bytes()+b'\n')
    elif fault == 'resource': (actors/'A-animation.res').write_bytes(b'changed resource')
    else: save(out/'pipeline.json',dict(status='processing'))
    save(out/'result.json',result)
    with pytest.raises(ValueError): audit.verify(out)


def test_source_change_preserves_failed_partial_output(tmp_path,monkeypatch):
    path,pp,gp,actors = actor_producer(tmp_path,monkeypatch); original = audit.evaluate
    def changed(*args):
        result = original(*args); pp.write_bytes(pp.read_bytes()+b'\n'); return result
    monkeypatch.setattr(audit,'evaluate',changed); out=tmp_path/'failed'
    with pytest.raises(ValueError,match='source changed'): audit.run(path,pp,gp,actors,out)
    assert read(out/'pipeline.json')['status'] == 'failed' and not (out/'result.json').exists()


def test_hold_replays_every_original_contact_time_and_relative_speed_population(tmp_path):
    path,_,scene,policy,actor = simple(tmp_path,mode='hold')
    result,arrays = audit.evaluate(scene,policy,sha256(path),actor,{'native-authoring':actor})
    _,native_arrays = scene.evaluate()
    np.testing.assert_array_equal(arrays['native-authoring_contact_0_times_s'],native_arrays['contact_0_times_s'])
    assert result['counts']['native-authoring']['contact_samples'] == len(native_arrays['contact_0_times_s']) > 1
    assert result['reports']['native-authoring']['actor_pose_queries'] == len(native_arrays['contact_0_times_s'])
    assert result['native_and_imported_surface_contacts_pass']


@pytest.mark.parametrize('fault',['result','request','snapshot','method'])
def test_evidence_mutation_during_replay_is_detected(tmp_path,monkeypatch,fault):
    path,pp,gp,actors = actor_producer(tmp_path,monkeypatch); out=tmp_path/'surface-audit'
    audit.run(path,pp,gp,actors,out); original=audit.evaluate
    def changed(*args):
        result = original(*args)
        if fault in ('result','request'): target=out/(fault+'.json')
        elif fault == 'snapshot': target=next((out/'input').glob('*.glb'))
        else: target=out/'implementation/native_imported_surface_contact.py'
        target.write_bytes(target.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(audit,'evaluate',changed)
    with pytest.raises(ValueError,match='changed|differs'): audit.verify(out)
