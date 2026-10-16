"""Complete clock/raw transform provenance and affine skin/object reconstruction.

Engine observations here are explicit source-only test doubles. Real Godot
capture validation remains a separate experiment.
"""
import copy,json,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256
from native_scene_contacts import SceneContacts
from native_scene_imported_skin import ImportedSceneSkin
from native_runtime_affine_skin import AffineSkin
from native_engine_contacts import matrices
from test_native_scene_geometry import policy
import test_native_scene_runtime as fixture_module
from test_native_scene_runtime import observations
from test_native_scene_runtime_modes import wire
import native_scene_runtime_modes as runtime
import native_runtime_surface_capture as capture


def source(tmp_path,monkeypatch,*,configured=None,fractional=False,third=False,multi=False,transform=None):
    original=fixture_module.tracks_setup
    if fractional or third or multi:
        def setup(folder):
            glb,spec,scene,times,request,report,worlds=original(folder)
            if fractional or multi:
                from rig_asset import read_asset,array
                from gltf_tools import append_accessor,write_glb
                document,binary=read_asset(glb);binary=bytearray(binary)
                for mesh in document['meshes']:
                    for primitive in list(mesh['primitives']):
                        accessor=primitive['attributes']['POSITION'];count=document['accessors'][accessor]['count']
                        if fractional:primitive['attributes']['WEIGHTS_0']=append_accessor(document,binary,np.tile([.1,.2,.3,.4],(count,1)),'VEC4')
                        if multi:
                            extra=copy.deepcopy(primitive);positions=array(document,bytes(binary),accessor)+[0.,0.,.25]
                            extra['attributes']['POSITION']=append_accessor(document,binary,positions,'VEC3');mesh['primitives'].append(extra)
                write_glb(glb,document,binary)
                for actor in spec['actors'].values():actor['sha256']=sha256(glb)
            if third:
                spec['actors']['C']=copy.deepcopy(spec['actors']['A']);spec['actors']['C']['placement']['translation_m']=[4.,0.,0.]
                request['actors']['C']=copy.deepcopy(request['actors']['A'])
            scene=SceneContacts(spec,folder);report,_=scene.evaluate()
            worlds={n:np.array([a['sampler'].sample(t)[a['rig'].joints] for t in times]) for n,a in scene.actors.items()}
            return glb,spec,scene,times,request,report,worlds
        monkeypatch.setattr(fixture_module,'tracks_setup',setup)
    folder,_,manifest,_,scene,times,events,asset=fixture_module.fixture(tmp_path)
    gp=policy(folder/'scene.json');gp['clock']['times_s']=times.tolist();save(folder/'geometry-policy.json',gp)
    manifest['files_sha256']['geometry-policy.json']=sha256(folder/'geometry-policy.json');save(folder/'package.json',manifest)
    manifest['sampled_scene_conditions_pass']=False;save(folder/'package.json',manifest)
    package=tmp_path/'source-with-policy.zip'
    with zipfile.ZipFile(package,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n in manifest['files_sha256']:z.write(folder/n,n)
        z.write(folder/'package.json','package.json')
    actual=observations(scene,times,events,asset)
    if transform is not None:transform(actual)
    engine=tmp_path/'engine';engine.write_bytes(b'explicit-engine-test-double')
    def fake(command,**kwargs):
        p=Path(command[-1]);save(p,wire(p.parent,actual));return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runtime.subprocess,'run',fake)
    target=tmp_path/'runtime';selected=configured or {n:('extracted' if i%2==0 else 'embedded') for i,n in enumerate(scene.actors)}
    result=runtime.run(package,target,selected,engine=engine)
    return target,result,actual,scene,times


@pytest.mark.parametrize('mode',[None,'embedded','extracted','mixed'])
def test_all_selected_surfaces_and_rigid_objects_match_every_raw_frame(tmp_path,monkeypatch,mode):
    folder,result,actual,scene,times=source(tmp_path,monkeypatch);before=sha256(folder/'observations.npz')
    staged=capture.stage(folder,sha256(folder/'result.json'),tmp_path/'compact',mode=mode)
    value=capture.load(tmp_path/'compact',staged['receipt_sha256']);chosen=staged['mode']
    assert staged['arrays_roundtrip_exact'] and not staged['quality_approved'] and not staged['physics_verified']
    assert set(value.meta['actors'])==set(scene.actors) and set(value.meta['objects'])==set(scene.objects)
    for name,actor in scene.actors.items():
        observed=actual['modes'][chosen]['actors'][name];canonical=ImportedSceneSkin(actor['rig'],observed);skin=AffineSkin(observed)
        for t,frame in zip(times,actual['modes'][chosen]['frames']):
            np.testing.assert_allclose(value.actor_vertices(name,float(t)),skin.positions(frame['actors'][name])[canonical.mapping],rtol=0,atol=1e-12)
        points=value.actor_points(name,np.array([0,0]),times[[1,0,1]])
        np.testing.assert_array_equal(points[0],points[2]);assert points.shape==(3,2,3)
    for name in scene.objects:
        p,r=value.object_poses(name,times)
        expected=matrices([f['objects'][name] for f in actual['modes'][chosen]['frames']])
        np.testing.assert_array_equal(p,expected[:,:3,3]);np.testing.assert_allclose(r,expected[:,:3,:3],rtol=0,atol=1e-12)
    assert sha256(folder/'observations.npz')==before
    with pytest.raises(ValueError,match='Fresh'):capture.stage(folder,sha256(folder/'result.json'),tmp_path/'compact',mode=mode)


def test_fractional_unorm16_weights_preserve_outer_translation_once(tmp_path,monkeypatch):
    folder,_,actual,scene,times=source(tmp_path,monkeypatch,fractional=True)
    staged=capture.stage(folder,sha256(folder/'result.json'),tmp_path/'compact')
    value=capture.load(tmp_path/'compact',staged['receipt_sha256']);name='B';p=value.meta['actors'][name]['prefix']
    assert np.any(abs(value.arrays[p+'_weights'].sum(axis=1)-1)>1e-6)
    world=value.arrays[p+'_world'][-1]
    wrong=np.einsum('vkij,vkj,vk->vi',world[value.arrays[p+'_nodes'],:3,:],value.arrays[p+'_points'],value.arrays[p+'_weights'])
    assert float(abs(wrong-value.actor_vertices(name,float(times[-1]))).max())>1e-6
    raw=actual['modes']['mixed'];canonical=ImportedSceneSkin(scene.actors[name]['rig'],raw['actors'][name])
    expected=AffineSkin(raw['actors'][name]).positions(raw['frames'][-1]['actors'][name])[canonical.mapping]
    np.testing.assert_allclose(value.actor_vertices(name,float(times[-1])),expected,rtol=0,atol=1e-12)


def test_third_actor_and_multiple_mesh_primitives_are_not_dropped(tmp_path,monkeypatch):
    folder,_,_,scene,_=source(tmp_path,monkeypatch,third=True,multi=True)
    staged=capture.stage(folder,sha256(folder/'result.json'),tmp_path/'compact')
    value=capture.load(tmp_path/'compact',staged['receipt_sha256'])
    assert list(value.meta['actors'])==['A','B','C']
    for name,actor in scene.actors.items():
        assert len(actor['rig'].primitives)>1
        assert value.meta['actors'][name]['vertices']==sum(len(p['positions']) for p in actor['rig'].primitives)


def test_unrecorded_configured_mask_never_claims_selected_export_coverage(tmp_path,monkeypatch):
    folder,_,_,_,_=source(tmp_path,monkeypatch,configured={'A':'embedded','B':'extracted'})
    with pytest.raises(ValueError,match='no exact captured mode'):capture.stage(folder,sha256(folder/'result.json'),tmp_path/'unsupported')
    staged=capture.stage(folder,sha256(folder/'result.json'),tmp_path/'explicit',mode='embedded')
    assert not staged['matches_export_configuration']


@pytest.mark.parametrize('artifact',['capture.json','capture.npz','source-scene.json','source-policy.json','implementation/native_runtime_surface_capture.py'])
def test_changed_capture_snapshots_or_code_reject(tmp_path,monkeypatch,artifact):
    folder,_,_,_,_=source(tmp_path,monkeypatch);out=tmp_path/'compact'
    staged=capture.stage(folder,sha256(folder/'result.json'),out)
    p=out/artifact;p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='changed|required'):capture.load(out,staged['receipt_sha256'])


def test_rebinding_outer_metadata_and_receipt_does_not_replace_original_pin(tmp_path,monkeypatch):
    folder,_,_,_,_=source(tmp_path,monkeypatch);out=tmp_path/'compact'
    staged=capture.stage(folder,sha256(folder/'result.json'),out)
    meta=read(out/'capture.json');meta['physics_verified']=True;save(out/'capture.json',meta)
    receipt=read(out/'receipt.json');receipt['files_sha256']['capture.json']=sha256(out/'capture.json');save(out/'receipt.json',receipt)
    with pytest.raises(ValueError,match='Pinned surface receipt'):capture.load(out,staged['receipt_sha256'])


@pytest.mark.parametrize('fault',['world','skeleton','mesh','object'])
def test_npz_rebinding_cannot_disagree_with_raw_captured_transforms(tmp_path,monkeypatch,fault):
    folder,result,_,_,_=source(tmp_path,monkeypatch)
    with np.load(folder/'observations.npz',allow_pickle=False) as stored:arrays={k:stored[k] for k in stored.files}
    key={'world':'mixed_actor_0_extracted_world','skeleton':'mixed_actor_0_skeleton_world','mesh':'mixed_actor_0_mesh_world','object':'mixed_object_0_world'}[fault]
    arrays[key][1,...,0,3]+=.01;np.savez_compressed(folder/'observations.npz',**arrays)
    result['files_sha256']['observations.npz']=sha256(folder/'observations.npz');save(folder/'result.json',result)
    with pytest.raises(ValueError,match='raw frames'):capture.stage(folder,sha256(folder/'result.json'),tmp_path/'invalid')


def test_missing_arrays_budget_and_off_clock_queries_reject(tmp_path,monkeypatch):
    folder,_,_,_,_=source(tmp_path,monkeypatch);out=tmp_path/'compact'
    staged=capture.stage(folder,sha256(folder/'result.json'),out);value=capture.load(out,staged['receipt_sha256'])
    for time in [True,float('nan'),-.1,99.,.0123456789]:
        with pytest.raises(ValueError):value.actor_vertices('A',time)
    with pytest.raises(ValueError):value.actor_vertices('unknown',0.)
    with pytest.raises(ValueError):value.actor_points('A',np.array([999999]),[0.])
    with pytest.raises(ValueError):value.object_poses('unknown',[0.])
    monkeypatch.setattr(capture,'ARRAY_LIMIT',4)
    with pytest.raises(ValueError,match='budget'):capture.stage(folder,sha256(folder/'result.json'),tmp_path/'over-budget')


def test_object_basis_projection_is_reported_and_nonrigid_objects_reject():
    world=np.repeat(np.eye(4)[None],3,axis=0);world[:,0,0]+=1e-7
    rotation,error=capture._rigid(world)
    assert 0<error<capture.OBJECT_TOLERANCE and np.array_equal(rotation,np.repeat(np.eye(3)[None],3,axis=0))
    world[:,0,0]=1.1
    with pytest.raises(ValueError,match='not rigid'):capture._rigid(world)


def test_sealed_arrays_and_query_metadata_cannot_be_accidentally_edited(tmp_path,monkeypatch):
    folder,_,_,_,_=source(tmp_path,monkeypatch);out=tmp_path/'compact'
    staged=capture.stage(folder,sha256(folder/'result.json'),out);value=capture.load(out,staged['receipt_sha256'])
    assert staged['source_scene_conditions_pass'] is False and value.meta['source_scene_conditions_pass'] is False
    with pytest.raises(TypeError):value.arrays['times_s']=np.array([0.,2.])
    with pytest.raises(ValueError):value.times[0]=.1
    expected=value.actor_vertices('A',0.)
    metadata=value.meta;metadata['actors']['A']['mesh_nodes'].clear()
    np.testing.assert_array_equal(value.actor_vertices('A',0.),expected)


def test_distinct_mesh_worlds_and_failed_runtime_diagnostics_are_preserved(tmp_path,monkeypatch):
    from test_native_scene_engine import serialized
    def transform(actual):
        for entry in actual['modes'].values():
            for observed in entry['actors'].values():observed['meshes'][1]['node']='mesh-extra'
            frames=list(entry['frames'])+list(entry['previews'])
            frames.extend(c['scene'] for c in entry['events'])
            for trace in entry['traces'].values():frames.extend(c['scene'] for c in trace)
            for frame in frames:
                for actor in frame['actors'].values():
                    local=np.eye(4);local[:3,3]=[.25,.1,-.15]
                    actor['mesh_world']['mesh-extra']=serialized(matrices(actor['mesh_world']['mesh'])@local)
        # Mesh-node placement is intentionally supported by the comparator;
        # introduce a separate actual object-pose defect to test failed evidence.
        actual['modes']['mixed']['frames'][-1]['objects']['item'][3][0]+=.02
    folder,result,actual,scene,times=source(tmp_path,monkeypatch,multi=True,transform=transform)
    assert result['all_sampled_runtime_conditions_pass'] is False
    staged=capture.stage(folder,sha256(folder/'result.json'),tmp_path/'compact')
    value=capture.load(tmp_path/'compact',staged['receipt_sha256'])
    assert staged['source_runtime_conditions_pass'] is False and not staged['quality_approved']
    for name,actor in scene.actors.items():
        assert len(value.meta['actors'][name]['mesh_nodes'])==2
        raw=actual['modes']['mixed'];skin=ImportedSceneSkin(actor['rig'],raw['actors'][name]);affine=AffineSkin(raw['actors'][name])
        for i,t in enumerate(times):
            expected=affine.positions(raw['frames'][i]['actors'][name])[skin.mapping]
            np.testing.assert_allclose(value.actor_vertices(name,float(t)),expected,rtol=0,atol=1e-12)
