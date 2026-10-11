"""Actual Studio scene/game build with final saved resources, generated rigs only."""
from pathlib import Path
import copy,json,os,shutil,sys,zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene as studio
import studio_native_scene_game as game
import action_worker_lock
from strep import read,sha256
from test_native_engine_rotation_speed import make_scene


@pytest.mark.parametrize('maximum',[200,100])
def test_actual_studio_build_gates_and_packages_exact_export_resource(tmp_path,monkeypatch,maximum):
    executable=os.environ.get('STREP_TEST_GODOT')
    if not executable:pytest.skip('Pinned real engine required')
    monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(game,'ROOT',tmp_path);monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    source_folder=tmp_path/'reports/rig-jobs/input';source_folder.mkdir(parents=True)
    contacts,_,_=make_scene(source_folder);spec=read(contacts)
    source=source_folder/'source.glb';url='/files/rig-jobs/input/source.glb';spec['actors']['A']['glb']=url
    engine=tmp_path/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe';engine.parent.mkdir(parents=True)
    shutil.copyfile(executable,engine)
    if os.name!='nt':engine.chmod(0o755)
    draft=dict(schema='strep-studio-native-scene-v2',scene=spec,geometry=dict(clock=dict(mode='explicit',times_s=[0.,1.,2.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes={}),object_edit=None,
        rotation_speed_limits=[dict(actor='A',node=0,maximum_degrees_per_second=maximum)])
    folder=studio.folder_for('scene');studio.prepare(draft,folder,lambda candidate:source if candidate==url else None)
    try:studio.run(folder)
    except Exception:
        for path in folder.rglob('engine.log'):print(path.relative_to(folder),path.read_text(encoding='utf-8'))
        raise
    review=studio.manifest('scene');result=read(folder/'authoring/result.json');speed=read(folder/'authoring/rotation-speed-engine/result.json')
    assert review['status']=='complete' and review['rotation_speed_requested']
    assert result['combined_conditions_pass'] and review['rotation_speed_conditions_pass'] is (maximum==200)
    assert review['sampled_conditions_pass'] is (maximum==200)
    assert speed['saved_animation_resources_used'] and speed['tracks'][0]['comparisons']==4
    raw=read(folder/'authoring/rotation-speed-engine/raw-engine-receipt.json')
    final_resource=folder/'authoring/actors-engine/A-animation.res'
    assert raw['animation_resources_sha256']['A']==sha256(final_resource)
    with zipfile.ZipFile(folder/'assets.zip') as package:
        exported=json.loads(package.read('rotation-speed-policy.json'))
        assert exported['tracks']==draft['rotation_speed_limits']
        import hashlib
        assert exported['contacts_sha256']==hashlib.sha256(package.read('scene.json')).hexdigest()
        assert hashlib.sha256(package.read('animations/A.res')).hexdigest()==raw['animation_resources_sha256']['A']
        assert json.loads(package.read('package.json'))['sampled_conditions_pass'] is (maximum==200)
    payload=dict(scene_job='scene',source_result_sha256=review['result_sha256'],request=dict(schema='strep-native-scene-game-tracks-v1',actors=dict(A=dict(root_node=0)),markers=[]))
    game_folder=game.folder_for('game');game.prepare(payload,game_folder);game.run(game_folder)
    game_review=game.manifest('game');assert game_review['scene_sampled_conditions_pass'] is (maximum==200)
    with zipfile.ZipFile(game_folder/'game-assets.zip') as package:
        assert json.loads(package.read('rotation-speed-policy.json'))==exported
        assert hashlib.sha256(package.read('animations/A.res')).hexdigest()==raw['animation_resources_sha256']['A']
        assert json.loads(package.read('package.json'))['sampled_scene_conditions_pass'] is (maximum==200)
    print('ACTUAL_STUDIO_EXPORT_SPEED',maximum,speed['tracks'][0]['maximum_observed_degrees_per_second'],review['sampled_conditions_pass'],game_review['scene_sampled_conditions_pass'])
