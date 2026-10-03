"""Composed producer binding, actual counterpart use and sampled scene gates.

Small closed rigs and explicitly mocked engine observations test orchestration;
these fixtures are not presented as actual Godot execution or quality evidence.
"""
from pathlib import Path
from types import SimpleNamespace
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from strep import save,read,sha256
from native_scene_contacts import SceneContacts
from native_object_scene_engine import CombinedObservations,load,run,prepare
from native_scene_engine import run as actor_run
from native_object_asset import run as asset_run,run_engine as object_run,ObjectAsset
from native_object_hold_fit import proposal
from test_native_object_hold_fit import fixture
from test_native_scene_engine import mock_actor,serialized
from test_native_scene_geometry import policy


def producers(tmp_path,monkeypatch):
    # Production's existing worker remains separate; fixture jobs use their own lock.
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'fixture-lock')
    source,path,spec,scene,request=fixture(tmp_path)
    keys,_=proposal(scene,request,sha256(path));spec['objects']['item']['keyframes']=keys;save(path,spec)
    scene=SceneContacts(spec,tmp_path);exe=tmp_path/'fixture-engine';exe.write_bytes(b'mocked engine only')
    def execute(command,**kwargs):
        request=read(command[-2])
        if 'cases' in request:
            from rig_asset import RigAsset
            from native_support_clock import NativeSupportSampler
            cases=[]
            for c in request['cases']:
                rig=RigAsset.load(c['path']);sampler=NativeSupportSampler(rig.document,rig.binary,c['animation_index'])
                row=mock_actor(rig,sampler,request['sample_times_s'],path=c['path']);row['id']=c['id'];cases.append(row)
                Path(c['animation_output']).write_bytes(b'mocked actor resource')
            objects=[]
            for name in scene.objects:
                p,r=scene.object_poses(name,request['sample_times_s']);frames=[]
                for t,v,m in zip(request['sample_times_s'],p,r):
                    world=np.eye(4);world[:3,:3]=m;world[:3,3]=v
                    frames.append(dict(requested_time_s=t,matrix=serialized(world),rotation_xyzw=Rotation.from_matrix(m).as_quat().tolist()))
                objects.append(dict(id=name,frames=frames))
            save(command[-1],dict(engine=dict(string='fixture only'),cases=cases,objects=objects))
        else:
            asset=ObjectAsset(request['asset_path']);times=request['payload']['sample_times_s'];native={};default={}
            for name in scene.objects:
                p,r=asset.object_poses(name,times);q=Rotation.from_matrix(r).as_quat()
                native[name]=[dict(time_s=t,translation_m=v.tolist(),rotation_xyzw=w.tolist()) for t,v,w in zip(times,p,q)]
                default[name]=copy.deepcopy(native[name])
                for row in default[name]:row['translation_m'][0]+=.02
            Path(request['resource_path']).write_bytes(b'mocked object resource')
            save(command[-1],{'engine':dict(string='fixture only'),'default-import':default,'native-authoring':native})
        return SimpleNamespace(returncode=0)
    import subprocess
    monkeypatch.setattr(subprocess,'run',execute)
    asset_dir=tmp_path/'asset';asset_run(path,asset_dir)
    pp=tmp_path/'policy.json';p=policy(path);p['clock']['times_s']=read(asset_dir/'engine-payload.json')['sample_times_s'];save(pp,p)
    actors=tmp_path/'actors';objects=tmp_path/'objects'
    actor_run(path,actors,geometry_policy=pp,engine=exe,playback_mode='native-authoring')
    object_run(asset_dir,objects,exe)
    return path,pp,actors,objects


def test_full_composed_job_preserves_failed_default_and_passes_native_sampled_scene(tmp_path,monkeypatch):
    path,pp,actors,objects=producers(tmp_path,monkeypatch);out=tmp_path/'combined';result=run(path,pp,actors,objects,out)
    assert result['all_sampled_conditions_pass'] and result['geometry_pass'] and result['source_contacts_pass']
    assert result['contacts_pass']=={'default-import':False,'native-authoring':True}
    assert all(v['passed'] for v in result['skin_errors'].values())
    assert all(v['passed'] for v in result['object_pose_reports']['native-authoring'].values())
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert not result['gpu_render_checked'] and not result['real_time_playback_verified']
    assert not read(out/'native-authoring-contacts.json')['loaded_skin_weights_normalized']
    for n,h in result['files_sha256'].items():assert sha256(out/n)==h
    with pytest.raises(ValueError,match='Fresh'):run(path,pp,actors,objects,out)


@pytest.mark.parametrize('fault',['pending','source','policy','actor-raw','object-raw','method','resource','actor-snapshot','missing-script','missing-animation','missing-object-receipt'])
def test_changed_or_partial_producers_reject_before_combination(tmp_path,monkeypatch,fault):
    path,pp,actors,objects=producers(tmp_path,monkeypatch)
    if fault=='pending':save(objects/'pipeline.json',dict(status='processing'))
    if fault=='source':v=read(path);v['contacts'][0]['limits']['position_m']=.004;save(path,v)
    if fault=='policy':v=read(pp);v['limits']['penetration_m']=.006;save(pp,v)
    if fault=='actor-raw':(actors/'engine-output.json').write_bytes((actors/'engine-output.json').read_bytes()+b'\n')
    if fault=='object-raw':(objects/'engine-output.json').write_bytes((objects/'engine-output.json').read_bytes()+b'\n')
    if fault=='method':(actors/'implementation/native_scene_engine.py').write_bytes(b'changed')
    if fault=='resource':(objects/'native-animation.res').write_bytes(b'changed')
    if fault=='actor-snapshot':next((actors/'input').glob('*.glb')).write_bytes(b'changed')
    if fault=='missing-script':
        receipt=read(actors/'raw-engine-receipt.json');receipt['executed_scripts_sha256'].pop('native_godot_preview.gd');save(actors/'raw-engine-receipt.json',receipt)
        result=read(actors/'result.json');result['raw_engine_receipt_sha256']=sha256(actors/'raw-engine-receipt.json');save(actors/'result.json',result)
    if fault=='missing-animation':result=read(actors/'result.json');result['animation_resources_sha256']={};save(actors/'result.json',result)
    if fault=='missing-object-receipt':result=read(objects/'result.json');result['files_sha256'].pop('native-animation.res');save(objects/'result.json',result)
    with pytest.raises(ValueError):load(path,pp,actors,objects)


@pytest.mark.parametrize('fault',['missing','count','clock','nan','quaternion'])
def test_complete_actual_object_counterparts_required(tmp_path,fault):
    _,_,_,scene,_=fixture(tmp_path);times=np.array([0.,1.,2.])
    raw={'item':[dict(time_s=t,translation_m=[0.,0.,0.],rotation_xyzw=[0.,0.,0.,1.]) for t in times]}
    if fault=='missing':raw={}
    if fault=='count':raw['item'].pop()
    if fault=='clock':raw['item'][1]['time_s']+=.001
    if fault=='nan':raw['item'][1]['translation_m'][0]=np.nan
    if fault=='quaternion':raw['item'][1]['rotation_xyzw']=[0.,0.,0.,0.]
    with pytest.raises(ValueError):CombinedObservations(scene,None,raw,times)


def test_counterpart_observations_and_exact_clocks_are_authoritative(tmp_path):
    _,_,_,scene,_=fixture(tmp_path);times=np.array([0.,1.,2.]);raw={'item':[dict(time_s=t,translation_m=[t,0.,0.],rotation_xyzw=[0.,0.,0.,1.]) for t in times]}
    observed=CombinedObservations(scene,None,raw,times)
    p,_=observed.object_poses('item',[1.,2.]);assert p.tolist()==[[1.,0.,0.],[2.,0.,0.]]
    with pytest.raises(ValueError,match='Missing exact'):observed.object_poses('item',[.5])


def test_prepare_keeps_complete_frame_policy_adds_stored_keys_and_preserves_original_bundle(tmp_path,monkeypatch):
    path,pp,actors,objects=producers(tmp_path,monkeypatch);asset_dir=tmp_path/'asset'
    p=read(pp);p['clock']['mode']='native-and-frame-populations';expanded=tmp_path/'expanded-policy.json';save(expanded,p)
    original={n:sha256(asset_dir/n) for n in read(asset_dir/'result.json')['files_sha256']}
    out=tmp_path/'prepared';result=prepare(path,expanded,asset_dir,out)
    prepared=read(out/'common-policy.json');payload=read(out/'engine-payload.json');clock=np.asarray(payload['sample_times_s'])
    assert prepared['clock']['mode']==p['clock']['mode'] and prepared['limits']==p['limits'] and prepared['planes']==p['planes']
    assert result['sampled_asset_conditions_pass'] and np.isin(read(asset_dir/'engine-payload.json')['sample_times_s'],clock).all()
    from native_scene_geometry import policy_for
    scene=SceneContacts(read(path),tmp_path);required,_,_=policy_for(p,scene,sha256(path));assert np.isin(required,clock).all()
    for track in ObjectAsset(out/'objects.glb').objects.values():assert np.isin(track['translation'][0],clock).all()
    assert original=={n:sha256(asset_dir/n) for n in original} and (out/'objects.glb').read_bytes()==(asset_dir/'objects.glb').read_bytes()
    assert sha256(out/'clock-preparation.py')==result['clock_preparation']['implementation_sha256']
    with pytest.raises(ValueError,match='Fresh'):prepare(path,expanded,asset_dir,out)


def test_prepare_rejects_another_source_scene_without_rewriting_inputs(tmp_path,monkeypatch):
    path,pp,_,_=producers(tmp_path,monkeypatch);original=read(path);original['contacts'][0]['limits']['position_m']=.001
    other=tmp_path/'other.json';save(other,original)
    with pytest.raises(ValueError,match='same original contact scene'):prepare(other,pp,tmp_path/'asset',tmp_path/'prepared')
