"""Whole-clock actor-only runtime contracts with explicit engine test doubles."""
import copy
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import zipfile
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_game_tracks import setup
from test_native_scene_runtime import observations
from native_scene_contacts import SceneContacts
from native_scene_game_tracks import export
from strep import read,save,sha256
import native_scene_runtime as runtime


def fixture(tmp_path, *, partner=True):
    source,spec,_,times,request,_,_=setup(tmp_path)
    spec['objects']={}
    if not partner:
        spec['actors'].pop('B');request['actors'].pop('B')
        spec['contacts']=[r for r in spec['contacts'] if r['actor']=='A']
    for row in spec['contacts']:
        row['target']=dict(space='world',points_m=[[0.,0.,0.]])
    if partner: spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=copy.deepcopy(spec['contacts'][0]['vertices']),reduction='individual')
    scene=SceneContacts(spec,tmp_path)
    times=np.unique(np.concatenate([times]+[c[2] for c in scene.actors['A']['sampler'].channels]))
    folder=tmp_path/'game';folder.mkdir();(folder/'actors').mkdir();(folder/'animations').mkdir()
    portable=copy.deepcopy(spec)
    for i,name in enumerate(scene.actors):
        shutil.copyfile(source,folder/f'actors/{i}.glb');portable['actors'][name]['glb']=f'actors/{i}.glb'
        (folder/f'animations/{name}.res').write_bytes(b'explicit test-double native resource')
    save(folder/'scene.json',portable)
    report,_=scene.evaluate();worlds={n:np.array([a['sampler'].sample(t)[a['rig'].joints] for t in times]) for n,a in scene.actors.items()}
    tracks=tmp_path/'tracks';export(scene,request,times,worlds,report,tracks,source_spec=spec,portable_scene_sha256=sha256(folder/'scene.json'),contact_report_sha256='a'*64)
    for name in ('root-motion.json','root-observations.npz','contacts.json','events.json'):shutil.copyfile(tracks/name,folder/name)
    shutil.copyfile(tracks/'request.json',folder/'game-tracks-request.json')
    manifest=dict(schema='strep-native-scene-game-package-v1',files_sha256={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()},
        selected_animations={n:0 for n in scene.actors},original_selected=True,quality_approved=False,release_approved=False,
        physics_verified=False,animation_runtime_playback_verified=False,root_removed_from_character_clips=False,
        root_application_mode='reference-only-motion-remains-embedded')
    save(folder/'package.json',manifest)
    package=tmp_path/'game.zip'
    with zipfile.ZipFile(package,'x') as archive:
        for p in folder.rglob('*'):
            if p.is_file():archive.write(p,p.relative_to(folder).as_posix())
    config,scene,times,events=runtime.configure(folder,manifest,{n:'extracted' for n in scene.actors})
    actual=observations(scene,times,events,SimpleNamespace(channels=[]))
    return folder,package,manifest,config,scene,times,events,actual


@pytest.mark.parametrize('partner',[False,True])
def test_complete_actor_only_clock_root_modes_and_callbacks(tmp_path,partner):
    _,_,_,config,scene,times,events,actual=fixture(tmp_path,partner=partner)
    assert config['objects'] is None
    result,arrays=runtime.compare(scene,times,events,actual,object_asset=None)
    assert result['all_sampled_runtime_conditions_pass'] and result['samples']==len(times)
    assert all(m['objects']=={} and m['callbacks']==4 and m['callback_scenarios']==4 for m in result['modes'].values())
    assert not any('_object_' in name for name in arrays)


@pytest.mark.parametrize('fault',['frame-prop','preview-prop','callback-prop','fake-channel','partial-partner','missing-frame'])
def test_actor_only_runtime_never_invents_props_or_drops_participants(tmp_path,fault):
    _,_,_,_,scene,times,events,actual=fixture(tmp_path);mode=actual['modes']['mixed']
    if fault=='frame-prop':mode['frames'][0]['objects']['ghost']=[]
    elif fault=='preview-prop':mode['previews'][0]['objects']['ghost']=[]
    elif fault=='callback-prop':mode['events'][0]['scene']['objects']['ghost']=[]
    elif fault=='fake-channel':mode['object_channels'].append({})
    elif fault=='partial-partner':mode['actors'].pop('B')
    else:mode['frames'].pop()
    with pytest.raises(ValueError):runtime.compare(scene,times,events,actual,object_asset=None)


@pytest.mark.parametrize('path',['objects.glb','animations/objects.res'])
def test_actor_only_package_rejects_extra_prop_resources(tmp_path,path):
    folder,_,manifest,_,scene,_,_,_=fixture(tmp_path)
    (folder/path).write_bytes(b'fake prop');manifest['files_sha256'][path]=sha256(folder/path)
    with pytest.raises(ValueError,match='synthetic object'):runtime.configure(folder,manifest,{n:'embedded' for n in scene.actors})


def test_actor_only_worker_preserves_full_package_and_rejection_failure(tmp_path,monkeypatch):
    _,package,_,_,scene,times,_,actual=fixture(tmp_path)
    engine=tmp_path/'engine';engine.write_bytes(b'explicit engine double')
    def execute(command,**kwargs):save(command[-1],actual);return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runtime.subprocess,'run',execute)
    before=sha256(package);out=tmp_path/'runtime'
    result=runtime.run(package,out,{n:'extracted' for n in scene.actors},engine=engine)
    assert result['samples']==len(times) and result['all_sampled_runtime_conditions_pass'] and sha256(package)==before
    assert read(out/'project/runtime-v1/scene-runtime.json')['objects'] is None
    with zipfile.ZipFile(out/'runtime-assets.zip') as archive:
        assert 'objects.glb' not in archive.namelist() and 'animations/objects.res' not in archive.namelist()
        assert archive.read('actors/0.glb')==(out/'project/actors/0.glb').read_bytes()
    assert not result['quality_approved'] and not result['real_time_playback_verified']
