"""Actor-only full-clock authoring, replay and portable packaging; engine doubles.

Numerical Python stages run unchanged. A mocked subprocess supplies complete
native observations; these tests do not claim actual Godot or human quality.
"""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_scene_authoring_job as author
import studio_native_scene as studio
import studio_native_scene_game as game
import verify_native_actor_scene_engine as replay
from native_scene_contacts import SceneContacts
from native_scene_engine import run as actor_run
from native_scene_geometry import policy_for
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import read, save, sha256
from test_native_scene_geometry import closed_fixture, policy
from test_native_scene_engine import mock_actor


def fixture(tmp_path, monkeypatch, *, partner=True, failed=True):
    monkeypatch.setattr(action_worker_lock, 'ROOT', tmp_path/'worker-lock')
    source, contacts, spec = closed_fixture(tmp_path)
    actor = SceneContacts(spec, tmp_path).actors['A']
    point = actor['rig'].vertices(actor['sampler'].sample(1.))[0].tolist()
    spec['contacts'][0].update(mode='touch', interval_s=[1.,1.], limits=dict(position_m=1e-6))
    spec['contacts'][0]['target']['points_m'] = [point]
    if failed: spec['contacts'][0]['target']['points_m'][0][0] += .02
    if partner:
        spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
        spec['actors']['B']['placement']['translation_m'] = [3.,0.,0.]
        row = copy.deepcopy(spec['contacts'][0]); row['id'] = 'partner-touch'
        row['target'] = dict(space='actor', actor='B', vertices=copy.deepcopy(row['vertices']), reduction='individual')
        spec['contacts'].append(row)
    save(contacts, spec)
    pp = tmp_path/'policy.json'; save(pp, policy(contacts, mode='native-and-frame-populations', planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-5.))))
    engine = tmp_path/'engine'; engine.write_bytes(b'explicit mocked engine')
    def execute(command, **kwargs):
        request = read(command[-2]); cases = []
        for case in request['cases']:
            rig = RigAsset.load(case['path']); sampler = NativeSupportSampler(rig.document, rig.binary, case['animation_index'])
            row = mock_actor(rig, sampler, request['sample_times_s'], path=case['path']); row['id'] = case['id']; cases.append(row)
            Path(case['animation_output']).write_bytes(b'explicit mocked actor resource')
        save(command[-1], dict(engine=dict(string='explicit-test-double'), cases=cases, objects=[]))
        return SimpleNamespace(returncode=0)
    import subprocess
    monkeypatch.setattr(subprocess, 'run', execute)
    return source, contacts, pp, engine


@pytest.mark.parametrize('partner,failed', [(False,False),(False,True),(True,True)])
def test_full_actor_only_authoring_replay_keeps_unnarrowed_clock_and_failures(tmp_path, monkeypatch, partner, failed):
    source, contacts, pp, engine = fixture(tmp_path, monkeypatch, partner=partner, failed=failed)
    before = {str(p):sha256(p) for p in (source,contacts,pp,engine)}
    recipe = tmp_path/'recipe.json'; author.plan(contacts, pp, engine, recipe)
    result = author.run(recipe, tmp_path/'job'); out = tmp_path/'job'
    assert [s['id'] for s in result['stages']] == ['source-contacts','actors-engine','replay']
    assert not any((out/n).exists() for n in ('objects-source','objects-common','objects-engine','combined-engine'))
    assert result['sampled_conditions_pass'] is (not failed and not partner)
    assert result['source_contact_conditions_pass'] is (not failed and not partner)
    assert all(result['artifacts'][k] is None for k in ('objects_glb','object_animation_resource','combined_audit','common_policy'))
    assert result['samples'] == len(read(out/'actors-engine/request.json')['sample_times_s'])
    assert result['samples'] > 900 and read(out/'replay/result.json')['all_replayed_observations_exact']
    report = read(out/'actors-engine/geometry.json')
    assert len(report['samples']) == result['samples'] and report['samples'][0]['actor_objects'] == []
    assert len(report['samples'][0]['actor_pairs']) == int(partner)
    assert len(report['samples'][0]['world_planes']) == 1+int(partner)
    assert before == {p:sha256(p) for p in before}
    assert not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('fault', ['raw','request','resource','log','native-array','contact-array','geometry','archive','snapshot','missing-script','missing-resource','decision','plane-rebound'])
def test_actor_replay_rejects_changed_or_incomplete_evidence(tmp_path, monkeypatch, fault):
    _, contacts, pp, engine = fixture(tmp_path, monkeypatch, partner=False)
    out = tmp_path/'actor'; actor_run(contacts,out,geometry_policy=pp,engine=engine,playback_mode='native-authoring')
    names={'raw':'engine-output.json','request':'request.json','resource':'A-animation.res','log':'engine.log',
        'native-array':'native-observations.npz','contact-array':'imported-contact-observations.npz','geometry':'geometry.json',
        'archive':'implementation/native_scene_engine.py'}
    if fault in names:
        p=out/names[fault];p.write_bytes(p.read_bytes()+b'changed')
    elif fault=='snapshot': next((out/'input').glob('*.glb')).write_bytes(b'changed')
    elif fault=='missing-script':
        value=read(out/'raw-engine-receipt.json');value['executed_scripts_sha256'].pop('native_godot_preview.gd');save(out/'raw-engine-receipt.json',value)
        result=read(out/'result.json');result['raw_engine_receipt_sha256']=sha256(out/'raw-engine-receipt.json');save(out/'result.json',result)
    elif fault=='plane-rebound':
        geometry=read(out/'geometry.json');geometry['samples'][0]['world_planes'][0]['maximum_depth_m']=.001;save(out/'geometry.json',geometry)
        result=read(out/'result.json');result['geometry_sha256']=sha256(out/'geometry.json');save(out/'result.json',result)
    else:
        result=read(out/'result.json')
        if fault=='missing-resource':result['animation_resources_sha256']={}
        else:result['all_sampled_conditions_pass']=True
        save(out/'result.json',result)
    with pytest.raises((ValueError,OSError)): replay.run(contacts,pp,out,tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


def test_actor_only_studio_job_package_and_game_source(tmp_path, monkeypatch):
    inputs=tmp_path/'reports/rig-jobs/input';inputs.mkdir(parents=True)
    source, contacts, pp, engine=fixture(inputs,monkeypatch)
    monkeypatch.setattr(studio,'ROOT',tmp_path)
    installed=tmp_path/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe';installed.parent.mkdir(parents=True);installed.write_bytes(engine.read_bytes())
    draft=dict(schema='strep-studio-native-scene-v1',scene=read(contacts),geometry=read(pp),object_edit=None)
    draft['geometry'].pop('schema');draft['geometry'].pop('contacts_sha256')
    url='/files/rig-jobs/input/'+source.name
    for actor in draft['scene']['actors'].values():actor['glb']=url
    before=copy.deepcopy(draft);folder=studio.folder_for('actor-only')
    studio.prepare(draft,folder,lambda selected:source if selected==url else None)
    result=studio.run(folder);manifest=studio.manifest(folder.name)
    assert manifest['status']=='complete' and not manifest['sampled_conditions_pass']
    assert set(result['downloads'])==studio.download_names(read(folder/'prepared.json'))
    assert all('objects-' not in key for key in result['downloads'])
    assert len(game.source(folder.name)[6])==manifest['samples']
    report,path=game.measured_contacts(folder,SceneContacts(read(folder/'contacts.json'),folder))
    assert report==read(folder/'authoring/actors-engine/result.json')['imported_contacts']
    with zipfile.ZipFile(folder/'assets.zip') as archive:
        assert set(archive.namelist())=={'scene.json','geometry-policy.json','package.json','actors/0.glb','actors/1.glb','animations/A.res','animations/B.res'}
        assert archive.read('actors/0.glb')==source.read_bytes()
        portable=tmp_path/'portable';archive.extractall(portable)
    value=read(portable/'scene.json');assert value['objects']=={} and value['contacts']==before['scene']['contacts']
    portable_scene=SceneContacts(value,portable);policy_for(read(portable/'geometry-policy.json'),portable_scene,sha256(portable/'scene.json'))
    assert draft==before and studio.served_file('native-scene-jobs/actor-only/assets.zip')==folder/'assets.zip'


def test_object_edit_cannot_be_applied_to_actor_only_scene(tmp_path,monkeypatch):
    _, contacts, pp, engine=fixture(tmp_path,monkeypatch,partner=False)
    edit=tmp_path/'edit.json';save(edit,{})
    with pytest.raises(ValueError,match='Object edits require'): author.plan(contacts,pp,engine,tmp_path/'recipe.json',edit)
    assert not (tmp_path/'recipe.json').exists()
