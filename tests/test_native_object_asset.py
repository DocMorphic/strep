"""Real Float32 storage, merged clocks and unchanged contact sampling."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_object_hold_fit import fixture
from native_object_hold_fit import proposal
from native_scene_contacts import SceneContacts
from native_object_asset import stored_clock,export,ObjectAsset,audit,run,scene_from_snapshots,run_engine
from gltf_tools import read_glb,write_glb
from strep import save,read,sha256


def test_nearby_native_and_frame_times_merge_with_explicit_source_mapping():
    times=np.array([0.,1.,1.+1e-8,1.+2e-8,2.])
    clock,record=stored_clock(times)
    assert np.array_equal(clock,[0,1,2])
    assert record['source_to_stored_index']==[0,1,1,1,2]
    assert record['collision_groups']==[dict(stored_time_s=1.,source_indices=[1,2,3],source_times_s=times[1:4].tolist())]
    assert record['maximum_timestamp_rounding_s']==2e-8+1-1


@pytest.mark.parametrize('times',[[0.],[0.,0.],[.1,1.],[0.,np.nan],[0.,np.inf],[0.,2.,1.]])
def test_invalid_storage_clocks_reject(times):
    with pytest.raises(ValueError):stored_clock(times)


@pytest.mark.parametrize('shape',['box','sphere','cylinder'])
def test_saved_primitive_tracks_pass_original_hold_clocks_without_changing_actors(tmp_path,shape):
    source,path,spec,scene,request=fixture(tmp_path,shape)
    keys,_=proposal(scene,request,sha256(path));spec['objects']['item']['keyframes']=keys
    save(path,spec);scene=SceneContacts(spec,tmp_path);source_hash=sha256(source)
    output=tmp_path/'export';result=run(path,output)
    assert result['sampled_asset_conditions_pass'] and result['actor_bytes_unchanged']
    assert sha256(source)==source_hash
    actual=read(output/'asset-audit.json');original,_=scene.evaluate()
    assert actual['contacts']['passed'] and actual['contacts']['frame_sampling_contract']==original['frame_sampling_contract']
    for old,new in zip(original['contacts'],actual['contacts']['contacts']):
        assert old['limits']==new['limits'] and old['interval_s']==new['interval_s']
        assert [p['times_s'] for p in old['relative_speed_populations']]==[p['times_s'] for p in new['relative_speed_populations']]
    asset=ObjectAsset(output/'objects.glb');times=asset.objects['item']['translation'][0]
    assert np.all(np.diff(times)>0) and len(asset.channels)==3
    assert np.array_equal(asset.objects['item']['scale'][1],np.ones((len(times),3)))
    assert not actual['geometry_checked'] and not actual['quality_approved'] and actual['original_selected']
    snapshot=scene_from_snapshots(output);assert snapshot.inputs and all(sha256(p)==h for p,h in snapshot.inputs.items())
    second=tmp_path/'repeat';run(path,second);assert (output/'objects.glb').read_bytes()==(second/'objects.glb').read_bytes()
    with pytest.raises(ValueError,match='Fresh'):run(path,output)


def test_collision_group_resamples_at_stored_time_instead_of_choosing_last_source_pose(tmp_path):
    _,_,spec,_,_=fixture(tmp_path)
    obj=spec['objects']['item'];obj['keyframes']=[dict(time_s=t,translation_m=[x,0,0],rotation_xyzw=[0,0,0,1])
        for t,x in [(0.,0.),(1.,1.),(1.+1e-8,10.),(2.,2.)]]
    scene=SceneContacts(spec,tmp_path);path=tmp_path/'objects.glb';clocks=export(scene,path);asset=ObjectAsset(path)
    assert len(clocks['item']['collision_groups'])==1
    p,_=asset.object_poses('item',[1.]);assert p.tolist()==[[1.,0.,0.]]
    report,_=audit(scene,asset,np.array([0.,1.,1.+1e-8,2.]))
    assert not report['sampled_conditions_pass'] and report['object_poses']['item']['maximum_position_error_m']>8


def test_static_object_receives_complete_duration_tracks(tmp_path):
    _,_,spec,_,_=fixture(tmp_path);spec['objects']['item']['keyframes']=spec['objects']['item']['keyframes'][:1]
    scene=SceneContacts(spec,tmp_path);path=tmp_path/'objects.glb';export(scene,path);asset=ObjectAsset(path)
    assert np.array_equal(asset.objects['item']['translation'][0],[0.,2.])
    p,r=asset.object_poses('item',[0.,.3,2.]);assert np.array_equal(p[0],p[-1]) and np.array_equal(r[0],r[-1])


def test_exact_native_rotation_knots_keep_declared_and_stored_poses(tmp_path):
    from scipy.spatial.transform import Rotation
    _,_,spec,_,_=fixture(tmp_path)
    spec['objects']['item']['keyframes']=[dict(time_s=t,translation_m=[0.,0.,0.],rotation_xyzw=q)
        for t,q in [(0.,[0.,0.,0.,1.]),(.5,Rotation.from_rotvec([.003,.002,.001]).as_quat().tolist()),(1.,[0.,0.,0.,1.]),(2.,[0.,0.,0.,1.])]]
    scene=SceneContacts(spec,tmp_path);path=tmp_path/'objects.glb';export(scene,path);asset=ObjectAsset(path)
    clock,q=asset.objects['item']['rotation']
    assert np.array_equal(q[clock==1.],[[0.,0.,0.,1.]])
    _,actual=asset.object_poses('item',clock)
    assert np.array_equal(actual,Rotation.from_quat(q).as_matrix())


def test_engine_audit_rejects_implementation_drift_before_launch(tmp_path,monkeypatch):
    _,path,_,_,_=fixture(tmp_path);output=tmp_path/'asset';run(path,output)
    archived=output/'implementation/native_object_asset.py';archived.write_bytes(archived.read_bytes()+b'\n# drift\n')
    import native_object_asset as module
    def launch(*args,**kwargs):pytest.fail('Engine must not launch with changed implementation')
    monkeypatch.setattr(module.subprocess,'run',launch)
    with pytest.raises(ValueError,match='recorded unchanged implementation'):run_engine(output,tmp_path/'engine',tmp_path/'not-launched.exe')


@pytest.mark.parametrize('fault',['clock-bounds','scale','missing','interpolation'])
def test_malformed_saved_assets_fail_explicitly(tmp_path,fault):
    _,_,_,scene,_=fixture(tmp_path);path=tmp_path/'objects.glb';export(scene,path);doc,binary=read_glb(path)
    if fault=='clock-bounds':doc['accessors'][doc['animations'][0]['samplers'][0]['input']]['max']=[-1.]
    if fault=='scale':doc['animations'][0]['channels'][2]['target']['path']='translation'
    if fault=='missing':doc['animations'][0]['channels'].pop()
    if fault=='interpolation':doc['animations'][0]['samplers'][0]['interpolation']='STEP'
    write_glb(path,doc,binary)
    with pytest.raises(ValueError):ObjectAsset(path)
