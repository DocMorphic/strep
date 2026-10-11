"""Imported worlds, native clocks, hierarchy and strict author speed policies."""
from pathlib import Path
import copy
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_engine_rotation_speed as speed
from native_scene_contacts import SceneContacts
from native_engine_clock import clock_wire
from gltf_tools import append_accessor,write_glb
from strep import save,read,sha256
from test_native_support import fixture


def make_scene(folder,*,rotating=True,helper=True):
    folder.mkdir(exist_ok=True)
    source,rig,_,_=fixture(folder);doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
    if helper:
        doc['nodes'].append(dict(name='unskinned-parent',translation=[.3,0,.2],children=[0,6]))
        doc['scenes'][0]['nodes']=[7]
    if rotating:
        animation=doc['animations'][0]
        clock=np.array([0,.013579,.200001,.853725,2.],np.float32)
        quaternions=Rotation.from_euler('y',[0,2,8,20,40],degrees=True).as_quat()
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=0,path='rotation')))
        animation['samplers'].append(dict(input=append_accessor(doc,data,clock,'SCALAR'),
            output=append_accessor(doc,data,quaternions,'VEC4'),interpolation='LINEAR'))
    write_glb(source,doc,data)
    spec=dict(schema='strep-native-scene-contacts-v1',duration_s=2.,actors=dict(A=dict(glb=source.name,
        sha256=sha256(source),animation_index=0,placement=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]))),objects={},contacts=[])
    contacts=folder/'contacts.json';save(contacts,spec)
    node=0 if rotating else 1
    policy=dict(schema='strep-native-rotation-speed-policy-v1',contacts_sha256=sha256(contacts),
        tracks=[dict(actor='A',node=node,maximum_degrees_per_second=200.)])
    path=folder/'speed-policy.json';save(path,policy)
    return contacts,path,SceneContacts(spec,folder)


def synthetic(scene,policy,digest):
    tracks,captures,times=speed.plan(scene,policy,digest);cases=[];found=[]
    serialize=lambda value:np.vstack((value[:3,:3].T,value[:3,3])).tolist()
    for name,nodes in captures.items():
        actor=scene.actors[name]
        case=dict(id=name,path='synthetic-source.glb',animation_index=actor['animation_index'],capture_nodes=nodes,
            source_node_count=len(actor['rig'].document['nodes']))
        cases.append(case)
        found.append(dict(id=name,path=case['path'],animation_index=case['animation_index'],original_animation_count=1,
            loop_mode=0,duration_s=scene.duration,selected_animation='Synthetic',capture_nodes=[dict(**n,engine_parent=n['parent'],
            scene_path='Synthetic/'+str(n['node'])) for n in nodes],frames=[dict(requested_time_s=float(t),actual_time_s=float(t),
            node_worlds=[serialize(actor['sampler'].sample(float(t))[n['node']]) for n in nodes]) for t in times]))
    request=dict(cases=cases,tracks=tracks,sample_times_s=times.tolist(),sample_clock=clock_wire(times),
        playback_mode='import',import_bake_fps=30.)
    actual=dict(cases=found,playback_mode='import',import_bake_fps=30.)
    return request,actual


def test_every_fractional_native_key_and_nonjoint_parent_are_measured(tmp_path):
    contacts,path,scene=make_scene(tmp_path);policy=read(path);request,actual=synthetic(scene,policy,sha256(contacts))
    result,arrays=speed.audit(scene,policy,sha256(contacts),request,actual)
    assert [n['node'] for n in request['cases'][0]['capture_nodes']]==[0,7]
    assert result['rotation_speed_conditions_pass'] and result['source_pose_conditions_pass']
    row=result['tracks'][0];assert row['comparisons']==4 and row['speed_acceptance_allowance']==0
    from native_rotation_speed_fit import serialized_rates
    channel=scene.actors['A']['sampler'].channels[-1]
    np.testing.assert_allclose(arrays['track_0_rates_degrees_per_second'],serialized_rates(channel[3],channel[2]),rtol=1e-12,atol=1e-12)
    assert all(result[k] is False for k in speed.FLAGS if k!='original_selected')


@pytest.mark.parametrize('damage',['missing-frame','clock','parent','mapping','alias','matrix','shear','reflection','duration','limit','mode'])
def test_incomplete_or_changed_engine_measurements_reject(tmp_path,damage):
    contacts,path,scene=make_scene(tmp_path);policy=read(path);request,actual=synthetic(scene,policy,sha256(contacts));case=actual['cases'][0]
    if damage=='missing-frame':case['frames'].pop(1)
    elif damage=='clock':case['frames'][1]['actual_time_s']+=1e-10
    elif damage=='parent':case['capture_nodes'][0]['engine_parent']=1
    elif damage=='mapping':case['capture_nodes'].pop()
    elif damage=='alias':case['capture_nodes'][1]['scene_path']=case['capture_nodes'][0]['scene_path']
    elif damage=='matrix':case['frames'][0]['node_worlds'].pop()
    elif damage=='shear':case['frames'][0]['node_worlds'][0][1][0]=.01
    elif damage=='reflection':case['frames'][0]['node_worlds'][0][0][0]=-1
    elif damage=='duration':case['duration_s']=float('nan')
    elif damage=='limit':request['tracks'][0]['maximum_degrees_per_second']+=1
    elif damage=='mode':actual['playback_mode']='native-authoring'
    with pytest.raises((ValueError,TypeError)):speed.audit(scene,policy,sha256(contacts),request,actual)


def test_small_pose_error_can_still_violate_strict_speed_limit(tmp_path):
    contacts,path,scene=make_scene(tmp_path,rotating=False);policy=read(path);policy['tracks'][0]['maximum_degrees_per_second']=0
    request,actual=synthetic(scene,policy,sha256(contacts))
    result,_=speed.audit(scene,policy,sha256(contacts),request,actual);assert result['all_sampled_conditions_pass']
    actual['cases'][0]['frames'][1]['node_worlds'][1][:3]=Rotation.from_euler('z',.0001,degrees=True).as_matrix().T.tolist()
    result,_=speed.audit(scene,policy,sha256(contacts),request,actual)
    assert result['source_pose_conditions_pass'] and not result['rotation_speed_conditions_pass']
    assert result['tracks'][0]['failed_intervals']==[0,1]


def test_parent_rotation_cancels_from_local_joint_speed(tmp_path):
    contacts,path,scene=make_scene(tmp_path);policy=read(path);policy['tracks']=[dict(actor='A',node=1,maximum_degrees_per_second=1e-8)]
    request,actual=synthetic(scene,policy,sha256(contacts));result,_=speed.audit(scene,policy,sha256(contacts),request,actual)
    assert result['all_sampled_conditions_pass'] and result['tracks'][0]['maximum_observed_degrees_per_second']<1e-8


@pytest.mark.parametrize('node',[6,7,99])
def test_nonjoint_or_missing_rotation_track_rejects(tmp_path,node):
    contacts,path,scene=make_scene(tmp_path);policy=read(path);policy['tracks'][0]['node']=node
    with pytest.raises(ValueError):speed.plan(scene,policy,sha256(contacts))


def test_complete_receipt_replays_and_summary_or_array_tampering_rejects(tmp_path,monkeypatch):
    contacts,path,scene=make_scene(tmp_path/'input',rotating=False)
    engine=tmp_path/'engine';engine.write_bytes(b'synthetic execution fixture, not an engine')
    monkeypatch.setattr(speed,'worker_lock',lambda:__import__('contextlib').nullcontext())
    def capture(command,**kwargs):
        request=read(command[-2]);_,actual=synthetic(scene,read(path),sha256(contacts))
        actual['engine']={'fixture':True}
        for item,found in zip(request['cases'],actual['cases']):found['path']=item['path']
        save(command[-1],actual);return __import__('types').SimpleNamespace(returncode=0)
    monkeypatch.setattr(speed.subprocess,'run',capture)
    folder=tmp_path/'output';result=speed.run(contacts,path,folder,engine=engine)
    assert speed.verify(contacts,path,folder)==result
    modified=copy.deepcopy(result);modified['rotation_speed_conditions_pass']=False;save(folder/'result.json',modified)
    with pytest.raises(ValueError,match='fresh matrix replay'):speed.verify(contacts,path,folder)
    save(folder/'result.json',result)
    with np.load(folder/'observations.npz') as archive:arrays={n:archive[n].copy() for n in archive.files}
    arrays['track_0_rates_degrees_per_second'][0]=99;np.savez_compressed(folder/'observations.npz',**arrays)
    # Rebinding a transport hash cannot make altered measurements agree.
    result['observations_sha256']=sha256(folder/'observations.npz');save(folder/'result.json',result)
    with pytest.raises(ValueError,match='array changed'):speed.verify(contacts,path,folder)
