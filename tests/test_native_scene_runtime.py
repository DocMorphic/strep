"""ZIP/source/clock/whole-scene checks with explicit model-free engine doubles."""
import copy,json,shutil,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_game_tracks import setup as tracks_setup
from test_native_scene_engine import mock_actor,serialized
from native_scene_contacts import SceneContacts
from native_scene_game_tracks import export,event_plan,crossed
from native_object_asset import export as export_object,ObjectAsset
from strep import read,save,sha256
import native_scene_runtime as runtime


def fixture(tmp_path):
    source,spec,scene,times,request,report,worlds=tracks_setup(tmp_path)
    folder=tmp_path/'game';folder.mkdir();(folder/'actors').mkdir();(folder/'animations').mkdir()
    export_object(scene,folder/'objects.glb');asset=ObjectAsset(folder/'objects.glb')
    times=np.unique(np.concatenate([times]+[c[2] for c in scene.actors['A']['sampler'].channels]+[np.array(c['times_s']) for c in asset.channels]))
    spec=copy.deepcopy(spec)
    for i,(name,actor) in enumerate(scene.actors.items()):
        shutil.copyfile(source,folder/f'actors/{i}.glb');spec['actors'][name]['glb']=f'actors/{i}.glb'
        (folder/f'animations/{name}.res').write_bytes(b'Explicit test-double native resource')
    (folder/'animations/objects.res').write_bytes(b'Explicit test-double object resource')
    save(folder/'scene.json',spec)
    worlds={name:np.array([actor['sampler'].sample(t)[actor['rig'].joints] for t in times]) for name,actor in scene.actors.items()}
    source_spec=copy.deepcopy(spec)
    for name in source_spec['actors']:source_spec['actors'][name]['glb']=str(source)
    tracks=tmp_path/'tracks';export(scene,request,times,worlds,report,tracks,source_spec=source_spec,portable_scene_sha256=sha256(folder/'scene.json'),contact_report_sha256='a'*64)
    for name in ('root-motion.json','root-observations.npz','contacts.json','events.json'):shutil.copyfile(tracks/name,folder/name)
    shutil.copyfile(tracks/'request.json',folder/'game-tracks-request.json')
    files={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()}
    manifest=dict(schema='strep-native-scene-game-package-v1',files_sha256=files,selected_animations={n:0 for n in scene.actors},
        original_selected=True,quality_approved=False,release_approved=False,physics_verified=False,animation_runtime_playback_verified=False,
        root_removed_from_character_clips=False,root_application_mode='reference-only-motion-remains-embedded')
    save(folder/'package.json',manifest)
    package=tmp_path/'game.zip'
    with zipfile.ZipFile(package,'x',compression=zipfile.ZIP_DEFLATED) as stored:
        for p in folder.rglob('*'):
            if p.is_file():stored.write(p,p.relative_to(folder).as_posix())
    config,scene,times,events=runtime.configure(folder,manifest,{n:'extracted' for n in scene.actors})
    return folder,package,manifest,config,scene,times,events,asset


def observations(scene,times,events,asset):
    actual=dict(engine=dict(string='explicit-test-double'),modes={},bootstrap=dict(parent_ready_listener=True,
        initial_event_ids=[e['id'] for e in crossed(events,None,float(times[-1])) if e['sample_index']==0],frames=4,valid_clock=True))
    for mode in ('embedded','extracted','mixed'):
        actors={};frames=[]
        for name,actor in scene.actors.items():
            data=mock_actor(actor['rig'],actor['sampler'],times)
            from native_godot_payload import payload
            native=payload(actor['rig'],actor['sampler'],'')
            data['channels']=[dict(path='Skeleton:'+c['bone'],type={'translation':1,'rotation':2,'scale':3}[c['path']],times_s=c['times_s'],values=c['values']) for c in native['channels']]
            actors[name]=data
        previous={}
        for t in times:
            frame=dict(pose_time_s=float(t),playback_time_s=float(t),actors={},objects={},root_deltas={})
            for index,(name,actor) in enumerate(scene.actors.items()):
                rig=actor['rig'];reader=actor['sampler'];p,r=actor['placement'];placement=np.eye(4);placement[:3,:3]=r;placement[:3,3]=p
                root=rig.joints[0];anchor=reader.sample(0.)[root];motion=reader.sample(t)[root]@np.linalg.inv(anchor)
                delta=np.eye(4) if name not in previous else np.linalg.inv(previous[name])@motion;previous[name]=motion
                extract=mode=='extracted' or mode=='mixed' and index%2==0
                names=[rig.document['nodes'][n]['name'] for n in rig.joints];order=[rig.joints[names.index(n)] for n in actors[name]['bone_names']]
                world=placement@reader.sample(t)[order]
                frame['actors'][name]=dict(time_s=float(t),bones=[serialized(v) for v in world],actor_world=serialized(placement@motion if extract else placement),
                    root_motion=serialized(motion),root_delta=serialized(delta),root_in_actor=serialized(anchor if extract else reader.sample(t)[root]))
                outer=placement@motion if extract else placement
                frame['actors'][name].update(skeleton_world=serialized(outer),
                    mesh_world={m['node']:serialized(outer) for m in actors[name]['meshes']})
                frame['root_deltas'][name]=serialized(delta)
            for name in scene.objects:
                p,r=asset.object_poses(name,[t]);matrix=np.eye(4);matrix[:3,:3]=r[0];matrix[:3,3]=p[0];frame['objects'][name]=serialized(matrix)
            frames.append(frame)
        callbacks=[dict(event=copy.deepcopy(e),scene=copy.deepcopy(frames[e['sample_index']])) for e in crossed(events,None,float(times[-1]))]
        preview=[copy.deepcopy(frames[i]) for i in [0,len(times)-1,len(times)//2,len(times)-1,0,0]]
        for f in preview:f['playback_time_s']=float(times[-1])
        object_channels=[dict(target_name=c['node_name'],path=c['node_name'],type={'translation':1,'rotation':2,'scale':3}[c['path']],times_s=copy.deepcopy(c['times_s']),values=copy.deepcopy(c['values'])) for c in asset.channels]
        actual['modes'][mode]=dict(actors=actors,object_channels=object_channels,frames=frames,events=callbacks,previews=preview,
            traces={id:copy.deepcopy(callbacks) for id in ('whole-clip','skipped','repeated')},
            invalid_rejected=True,late_participant_rejected=True,reentrant_rejected=True,malformed_configs_rejected=True,malformed_configs=7)
    return actual


def test_whole_scene_native_keys_marker_callbacks_and_array_populations(tmp_path):
    folder,package,manifest,config,scene,times,events,asset=fixture(tmp_path)
    with zipfile.ZipFile(package) as stored:assert runtime.package_members(stored)==manifest
    actual=observations(scene,times,events,asset);result,arrays=runtime.compare(scene,times,events,actual,object_asset=asset)
    assert result['all_sampled_runtime_conditions_pass'] and result['samples']==len(times)
    assert set(result['modes'])=={'embedded','extracted','mixed'}
    assert all(m['callbacks']==4 and m['callback_scenarios']==4 for m in result['modes'].values())
    assert all(value.dtype==np.dtype('<f8') for value in arrays.values())
    assert config['objects']['names']==['item'] and all(e['extract'] for e in config['actors'])


@pytest.mark.parametrize('fault',['pose','object','preview-object','callback-pose','callback-object','binding','reentrant','invalid-clock','object-key-value'])
def test_failed_numerics_or_rejection_evidence_retains_all_samples(tmp_path,fault):
    _,_,_,_,scene,times,events,asset=fixture(tmp_path);actual=observations(scene,times,events,asset);mode=actual['modes']['extracted']
    if fault=='pose':mode['frames'][-1]['actors']['A']['bones'][0][3][0]+=.02
    if fault=='object':mode['frames'][-1]['objects']['item'][3][0]+=.02
    if fault=='preview-object':mode['previews'][-1]['objects']['item'][3][0]+=.02
    if fault=='callback-pose':mode['traces']['whole-clip'][1]['scene']['actors']['B']['bones'][0][3][0]+=.02
    if fault=='callback-object':mode['traces']['whole-clip'][1]['scene']['objects']['item'][3][0]+=.02
    if fault=='binding':mode['late_participant_rejected']=False
    if fault=='reentrant':mode['reentrant_rejected']=False
    if fault=='invalid-clock':mode['invalid_rejected']=False
    if fault=='object-key-value':mode['object_channels'][0]['values'][0][0]+=.02
    result,arrays=runtime.compare(scene,times,events,actual,object_asset=asset)
    assert not result['all_sampled_runtime_conditions_pass'] and len(arrays['times_s'])==len(times)


@pytest.mark.parametrize('fault',['actor','object','clock','callback-late','callback-count','contact-dispatched','object-key-time','object-key-count',
    'boot-initial','boot-ready','boot-clock','boot-process'])
def test_partial_or_wrong_clock_populations_reject(tmp_path,fault):
    _,_,_,_,scene,times,events,asset=fixture(tmp_path);actual=observations(scene,times,events,asset);mode=actual['modes']['mixed']
    if fault=='actor':mode['actors'].pop('B')
    if fault=='object':mode['frames'][0]['objects'].clear()
    if fault=='clock':mode['frames'].pop()
    if fault=='callback-late':mode['traces']['whole-clip'][1]['scene']['pose_time_s']=float(times[-1])
    if fault=='callback-count':mode['events'].pop()
    if fault=='contact-dispatched':mode['events'][0]['event']['kind']='contact_intent'
    if fault=='object-key-time':mode['object_channels'][0]['times_s'][0]=.01
    if fault=='object-key-count':mode['object_channels'][0]['times_s'].pop()
    if fault=='boot-initial':actual['bootstrap']['initial_event_ids']=[]
    if fault=='boot-ready':actual['bootstrap']['parent_ready_listener']=False
    if fault=='boot-clock':actual['bootstrap']['valid_clock']=False
    if fault=='boot-process':actual['bootstrap']['frames']=0
    with pytest.raises(ValueError):runtime.compare(scene,times,events,actual,object_asset=asset)


@pytest.mark.parametrize('fault',['modes','root','scene-hash','event-confirmation','contact-dispatch','actor-selection','partial-root'])
def test_original_intent_binding_and_explicit_root_modes(tmp_path,fault):
    folder,_,manifest,_,_,_,_,_=fixture(tmp_path);modes={'A':'embedded','B':'extracted'}
    if fault=='modes':modes.pop('B')
    if fault=='root':r=read(folder/'root-motion.json');r['actors']['A']['root_node']=999;save(folder/'root-motion.json',r)
    if fault=='scene-hash':r=read(folder/'root-motion.json');r['portable_scene_sha256']='0'*64;save(folder/'root-motion.json',r)
    if fault=='event-confirmation':r=read(folder/'events.json');r['events'][0]['timing_confirmed']=False;save(folder/'events.json',r)
    if fault=='contact-dispatch':r=read(folder/'contacts.json');r['contacts'][0]['runtime_dispatch_allowed']=True;save(folder/'contacts.json',r)
    if fault=='actor-selection':manifest['selected_animations']['A']=1
    if fault=='partial-root':r=read(folder/'game-tracks-request.json');r['actors']['A']['root_node']=1;save(folder/'game-tracks-request.json',r)
    with pytest.raises(ValueError):runtime.configure(folder,manifest,modes)


@pytest.mark.parametrize('name',['../outside','/absolute','C:/drive','runtime\\file','a/./b','a//b','package.json'])
def test_zip_paths_and_duplicate_entries_reject_before_extraction(tmp_path,name):
    _,package,_,_,_,_,_,_=fixture(tmp_path);changed=tmp_path/'changed.zip';shutil.copyfile(package,changed)
    with zipfile.ZipFile(changed,'a') as archive:
        if name=='package.json':
            with pytest.warns(UserWarning,match='Duplicate name'):archive.writestr(name,b'test')
        else:archive.writestr(name,b'test')
    with zipfile.ZipFile(changed) as archive:
        with pytest.raises(ValueError):runtime.package_members(archive)


def test_full_worker_packaging_preserves_original_entries_and_failed_conditions(tmp_path,monkeypatch):
    _,package,_,_,scene,times,events,asset=fixture(tmp_path);actual=observations(scene,times,events,asset)
    actual['modes']['extracted']['frames'][-1]['objects']['item'][3][0]+=.02
    engine=tmp_path/'engine';engine.write_bytes(b'explicit-engine-double')
    def fake(command,**kwargs):save(command[-1],actual);return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runtime.subprocess,'run',fake);source_hash=sha256(package)
    out=tmp_path/'runtime';result=runtime.run(package,out,{'A':'extracted','B':'embedded'},engine=engine)
    assert result['status']=='complete' and not result['all_sampled_runtime_conditions_pass']
    assert not result['quality_approved'] and not result['physics_verified'] and not result['release_approved']
    assert result['source_bytes_unchanged'] and result['arrays_roundtrip_exact'] and sha256(package)==source_hash
    with zipfile.ZipFile(package) as original,zipfile.ZipFile(out/'runtime-assets.zip') as final:
        for name in original.namelist():assert original.read(name)==final.read('source-game-package.json' if name=='package.json' else name)
        assert 'runtime-v1/godot_native_scene_player.gd' in final.namelist()
        assert json.loads(final.read('package.json'))['finite_scene_controller_verified'] is False
    before=sha256(out/'pipeline.json')
    with pytest.raises(ValueError,match='Fresh'):runtime.run(package,out,{'A':'extracted','B':'embedded'},engine=engine)
    assert sha256(out/'pipeline.json')==before


def test_engine_failure_preserves_pipeline_and_original_package(tmp_path,monkeypatch):
    _,package,_,_,_,_,_,_=fixture(tmp_path);engine=tmp_path/'engine';engine.write_bytes(b'engine-double');before=sha256(package)
    monkeypatch.setattr(runtime.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=2))
    out=tmp_path/'failed'
    with pytest.raises(ValueError,match='Actual complete scene'):runtime.run(package,out,{'A':'embedded','B':'embedded'},engine=engine)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists() and sha256(package)==before
