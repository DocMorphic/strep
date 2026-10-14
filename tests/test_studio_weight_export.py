"""Full numeric Studio/package path with synthetic engine observations only."""
from pathlib import Path
from types import SimpleNamespace
import copy,sys,zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene as studio
import studio_native_scene_game as game
import audit_conditioned_skin_fidelity as fidelity
from native_scene_weight_export import MODE
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for
from native_scene_game_tracks import crossed
from native_scene_authoring_job import validated
from strep import read,save,sha256
from test_studio_native_scene import setup
from test_native_object_scene_engine import producers


def completed(tmp_path,monkeypatch,*,fidelity_pass=True,weight_export=True):
    fixture=tmp_path/'engine-fixture';fixture.mkdir();producers(fixture,monkeypatch)
    draft,source,resolver=setup(tmp_path,monkeypatch,True)
    if weight_export:draft['skin_weight_export']=MODE
    if not fidelity_pass:
        compare=fidelity.compare
        def shifted(original,conditioned,index,placement,times,observed):
            return compare(original,conditioned,index,placement,times,lambda t:observed(t)+[.0002,0,0])
        monkeypatch.setattr(fidelity,'compare',shifted)
    folder=studio.folder_for('weighted');studio.prepare(draft,folder,resolver);studio.run(folder)
    return folder,source,draft


def test_ordinary_object_fit_packages_byte_identical_actor_copies(tmp_path,monkeypatch):
    folder,source,_=completed(tmp_path,monkeypatch,weight_export=False)
    result=studio.manifest(folder.name)
    assert result['sampled_conditions_pass'] and 'skin_weight_export' not in result
    active=read(read(folder/'authoring/result.json')['artifacts']['active_contacts'])
    assert Path(active['actors']['A']['glb'])!=folder/'input/actor-0.glb'
    with zipfile.ZipFile(folder/'assets.zip') as archive:
        assert archive.read('actors/0.glb')==source.read_bytes()
        assert 'skin-weight-export.json' not in archive.namelist()


def test_weight_export_preserves_current_speed_policy_and_strict_recipe(tmp_path,monkeypatch):
    from test_studio_scene_export_speed import speed_draft
    draft,_,resolver=speed_draft(tmp_path,monkeypatch);draft['skin_weight_export']=MODE
    folder=studio.folder_for('speed-and-weight');prepared=studio.prepare(draft,folder,resolver)
    value,paths,_,_=validated(folder/'recipe.json')
    assert value['schema']=='strep-native-scene-authoring-job-v3' and prepared['rotation_speed_requested']
    assert paths['rotation_speed_policy']==folder/'rotation-speed-policy.json'
    assert studio.frozen(folder)==prepared and not (folder/'authoring').exists()
    value['skin_weight_export']='automatic';save(folder/'recipe.json',value)
    with pytest.raises(ValueError):validated(folder/'recipe.json')


def test_contact_revision_keeps_export_choice_as_protected_intent(tmp_path,monkeypatch):
    from native_contact_revision import apply,validate
    draft,_,_=setup(tmp_path,monkeypatch,False);draft['skin_weight_export']=MODE
    contact=draft['scene']['contacts'][0];refs=copy.deepcopy(contact['vertices']);refs[0][2]+=1
    edits=[dict(id=contact['id'],source=dict(glb_sha256=draft['scene']['actors'][contact['actor']]['sha256'],vertices=refs,reduction=contact['reduction']),partner=None)]
    revised=apply(draft,edits);revised['contact_revision']=dict(schema='strep-native-contact-revision-v1',baseline=draft,edits=edits)
    assert validate(revised)[0]['skin_weight_export']==MODE
    revised.pop('skin_weight_export')
    with pytest.raises(ValueError):validate(revised)


@pytest.mark.parametrize('mode',[True,False,None,'automatic','unsupported'])
def test_invalid_export_choice_rejects_before_preparing(tmp_path,monkeypatch,mode):
    draft,_,resolver=setup(tmp_path,monkeypatch);draft['skin_weight_export']=mode
    folder=studio.folder_for('invalid')
    with pytest.raises(ValueError):studio.prepare(draft,folder,resolver)
    assert not folder.exists()


@pytest.mark.parametrize('fidelity_pass',[True,False])
def test_full_scene_and_zip_use_derivatives_keep_originals_and_gate_fidelity(tmp_path,monkeypatch,fidelity_pass):
    folder,source,draft=completed(tmp_path,monkeypatch,fidelity_pass=fidelity_pass)
    result=studio.manifest(folder.name)
    assert result['original_reference_fidelity_pass'] is fidelity_pass
    assert result['sampled_conditions_pass'] is fidelity_pass
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert {d['url'].split('/weighted/')[1] for d in result['downloads']}==studio.download_names(read(folder/'prepared.json'))
    with zipfile.ZipFile(folder/'assets.zip') as archive:
        manifest=read(folder/'exports/package.json')
        assert set(archive.namelist())==set(manifest['files_sha256'])|{'package.json'}
        assert archive.read('originals/actors/0.glb')==source.read_bytes()
        assert archive.read('actors/0.glb')==(folder/'authoring/skin-A/proposal.glb').read_bytes()
        assert archive.read('actors/0.glb')!=source.read_bytes()
        target=tmp_path/'portable';archive.extractall(target)
    scene=SceneContacts(read(target/'scene.json'),target)
    policy_for(read(target/'geometry-policy.json'),scene,sha256(target/'scene.json'))
    receipt=read(target/'skin-weight-export.json')
    assert receipt['original_reference_fidelity_pass'] is fidelity_pass and receipt['animation_changed'] is False
    assert receipt['portable_scene_sha256']==sha256(target/'scene.json')
    assert read(target/'scene.json')['contacts']==draft['scene']['contacts']
    for n,h in manifest['files_sha256'].items():assert sha256(target/n)==h
    assert validated(folder/'recipe.json')[0]['schema']=='strep-native-scene-authoring-job-v3'
    before=(folder/'completion.json').read_bytes();(folder/'authoring/original-fidelity/observations.npz').write_bytes(b'tampered')
    with pytest.raises(ValueError):studio.manifest(folder.name)
    assert (folder/'completion.json').read_bytes()==before


def test_weighted_game_package_keeps_exact_assets_and_uses_derivative_root_identity(tmp_path,monkeypatch):
    folder,source,_=completed(tmp_path,monkeypatch);monkeypatch.setattr(game,'ROOT',tmp_path)
    metadata=game.metadata(folder.name)
    assert metadata['actors']['A']['glb_sha256']==sha256(folder/'authoring/skin-A/proposal.glb')
    assert metadata['actors']['A']['glb_sha256']!=sha256(source)
    payload=dict(scene_job=folder.name,source_result_sha256=metadata['source_result_sha256'],request=dict(
        schema='strep-native-scene-game-tracks-v1',actors={n:dict(root_node=a['joints'][0]['node']) for n,a in metadata['actors'].items()},
        markers=[dict(id='meeting',name='meeting',actor='A',time_s=1.,confirmed=True)]))
    def events(command,**kwargs):
        import numpy as np
        request=read(command[-2]);value=read(request['events_path']);clock=np.frombuffer(bytes.fromhex(value['clock']['bytes_hex']),dtype='<f8');traces={}
        for scenario in request['scenarios']:
            fired=[];previous=None
            for index in scenario['indices']:
                current=float(clock[index]);fired.extend(crossed(value,previous,current));previous=current
            traces[scenario['id']]=fired
        save(command[-1],dict(engine=dict(string='synthetic event fixture'),traces=traces,invalid_rejected=True,malformed_configs_rejected=True,malformed_config_cases=6))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(game.subprocess,'run',events)
    output=game.folder_for('weighted-game');game.prepare(payload,output);result=game.run(output)
    assert game.manifest(output.name)['scene_sampled_conditions_pass'] is True
    assert result['root_samples_pass'] and not result['animation_runtime_playback_verified']
    roots=read(output/'tracks/root-motion.json')
    assert roots['actors']['A']['character_glb_sha256']==metadata['actors']['A']['glb_sha256']
    with zipfile.ZipFile(folder/'assets.zip') as scene_zip,zipfile.ZipFile(output/'game-assets.zip') as game_zip:
        for name in scene_zip.namelist():
            destination='source-package.json' if name=='package.json' else name
            assert scene_zip.read(name)==game_zip.read(destination)
    assert read(output/'package.json')['sampled_scene_conditions_pass'] is True
    assert read(output/'package.json')['skin_weight_export']==MODE
    assert game.manifest(output.name)['original_reference_fidelity_pass'] is True
