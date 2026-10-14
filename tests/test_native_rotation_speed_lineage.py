"""Portable authored speed intent, fresh replay, ancestors and package bytes."""
from pathlib import Path
import sys,copy,shutil,zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_correction_lineage as lineage
import studio_native_scene as scenes
import studio_native_scene_fit as corrections
import studio_native_scene_game as games
from native_rotation_speed_policy import policy_for,METHODS as SPEED_METHODS
from native_rotation_speed_fit import audit_scene_speed_outputs
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from strep import read,save,sha256
from test_native_rotation_speed_integration import speed_draft


def completed(tmp_path,monkeypatch,maximum=10,geometry=True):
    payload,source,resolver=speed_draft(tmp_path,monkeypatch,maximum)
    if not geometry:payload['draft']['geometry']['planes']={}
    job=corrections.folder_for('speed');corrections.prepare(payload,job,resolver);corrections.run(job)
    m=corrections.manifest('speed');draft=copy.deepcopy(payload['draft'])
    for name,row in m['actors'].items():draft['scene']['actors'][name].update(glb=row['candidate_url'],sha256=row['candidate_sha256'])
    return payload,job,m,draft


@pytest.mark.parametrize('maximum',[0,10])
def test_portable_policy_replays_exported_speeds_with_original_source_and_bounds(tmp_path,monkeypatch,maximum):
    payload,job,m,draft=completed(tmp_path,monkeypatch,maximum)
    before={n:sha256(job/n) for n in ('prepared.json','completion.json','rotation-speed-policy.json','fit/result.json')}
    folder=tmp_path/'portable';receipt=lineage.snapshot(draft,folder);record=lineage.verify(draft,folder,receipt)
    base=folder/'jobs/speed';digest=sha256(base/'original-scene.json');policy=read(base/'rotation-speed-policy.json')
    assert policy['contacts_sha256']==digest and policy['tracks']==payload['rotation_speed_limits']
    scene=SceneContacts(read(base/'original-scene.json'),base);edits=SceneEdits(read(base/'permissions.json'),scene,digest)
    limits,_,_=policy_for(policy,edits,digest)
    _,replay=audit_scene_speed_outputs(edits,limits,{'A':base/'candidate/actor-0.glb'})
    assert replay==read(base/'rotation-speed-audit.json')==m['rotation_speed_audit']
    row=record['jobs']['speed'];assert row['rotation_speed_conditions_pass'] is replay['passed']
    assert row['authored_rotation_speed_policy_sha256']==before['rotation-speed-policy.json']
    assert sha256(base/'rotation-speed-lower-bounds.npz')==sha256(job/'fit/rotation-speed-lower-bounds.npz')
    assert before=={n:sha256(job/n) for n in before}
    assert not any(str(tmp_path) in p.read_text() for p in folder.rglob('*.json'))


def test_failed_geometry_and_changed_context_do_not_inherit_parent_approval(tmp_path,monkeypatch):
    _,_,m,draft=completed(tmp_path,monkeypatch,geometry=False)
    assert not m['geometry_conditions_pass']
    draft['scene']['actors']['A']['placement']['translation_m']=[0,1,0]
    folder=tmp_path/'changed';receipt=lineage.snapshot(draft,folder);r=lineage.verify(draft,folder,receipt)
    row=r['jobs']['speed'];assert row['sampled_geometry_conditions_pass'] is False
    assert row['rotation_speed_conditions_pass'] is m['rotation_speed_conditions_pass']
    assert not row['correction_scene_context_preserved'] and r['numerical_decisions_apply_to_parent_job_only']
    assert not row['quality_approved'] and not r['release_approved']


def test_promoted_current_limits_preserve_context_but_do_not_rewrite_history(tmp_path,monkeypatch):
    from native_scene_export_speed import promote
    payload,_,_,draft=completed(tmp_path,monkeypatch)
    staged=promote(draft,payload['rotation_speed_limits'])
    record,_,_=lineage.plan(staged)
    assert record['jobs']['speed']['correction_scene_context_preserved']
    changed=copy.deepcopy(staged);changed['rotation_speed_limits'][0]['maximum_degrees_per_second']=11
    record,_,_=lineage.plan(changed)
    assert not record['jobs']['speed']['correction_scene_context_preserved']
    assert record['jobs']['speed']['authored_rotation_speed_policy_sha256']==sha256(corrections.folder_for('speed')/'rotation-speed-policy.json')
    assert not record['quality_approved']


@pytest.mark.parametrize('fault',['policy','audit','preflight','lower-bounds','drop','extra','rebound-policy'])
def test_speed_lineage_artifacts_cannot_be_changed_dropped_or_rebound(tmp_path,monkeypatch,fault):
    _,_,_,draft=completed(tmp_path,monkeypatch);folder=tmp_path/'portable';receipt=lineage.snapshot(draft,folder)
    names={'policy':'rotation-speed-policy.json','audit':'rotation-speed-audit.json',
        'preflight':'rotation-speed-preflight.json','lower-bounds':'rotation-speed-lower-bounds.npz'}
    if fault in names:(folder/'jobs/speed'/names[fault]).write_bytes(b'changed')
    elif fault=='drop':receipt['files_sha256'].pop('jobs/speed/rotation-speed-audit.json')
    elif fault=='extra':(folder/'unbound.json').write_text('{}')
    else:
        path=folder/'jobs/speed/rotation-speed-policy.json';p=read(path);p['tracks'][0]['maximum_degrees_per_second']=11;save(path,p)
        receipt['files_sha256']['jobs/speed/rotation-speed-policy.json']=sha256(path)
        record=read(folder/'record.json');record['files_sha256']=receipt['files_sha256'];save(folder/'record.json',record)
        receipt['record_sha256']=sha256(folder/'record.json')
    with pytest.raises(ValueError):lineage.verify(draft,folder,receipt)


def test_speed_ancestor_retained_when_latest_correction_omits_speed_policy(tmp_path,monkeypatch):
    payload,_,_,draft=completed(tmp_path,monkeypatch)
    payload['schema']='strep-studio-native-scene-fit-v1';payload.pop('rotation_speed_limits');payload['draft']=draft
    folder=corrections.folder_for('ordinary');corrections.prepare(payload,folder,lambda url:corrections.served_file(url.removeprefix('/files/')));corrections.run(folder)
    m=corrections.manifest('ordinary')
    for name,row in m['actors'].items():draft['scene']['actors'][name].update(glb=row['candidate_url'],sha256=row['candidate_sha256'])
    target=tmp_path/'portable';receipt=lineage.snapshot(draft,target);record=lineage.verify(draft,target,receipt)
    assert set(record['jobs'])=={'speed','ordinary'}
    assert 'rotation_speed_policy' in record['jobs']['speed'] and 'rotation_speed_policy' not in record['jobs']['ordinary']
    assert set(SPEED_METHODS)<=set(scenes.method_names(draft))


def test_scene_and_game_packages_keep_complete_speed_evidence(tmp_path,monkeypatch):
    _,_,_,draft=completed(tmp_path,monkeypatch)
    engine=tmp_path/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe';engine.parent.mkdir(parents=True);engine.write_bytes(b'mocked; not run')
    folder=scenes.folder_for('scene');prepared=scenes.prepare(draft,folder,lambda url:corrections.served_file(url.removeprefix('/files/')))
    assert set(SPEED_METHODS)<=set(prepared['implementation_sha256']) and scenes.frozen(folder)==prepared
    actors=folder/'authoring/actors-engine';actors.mkdir(parents=True);(actors/'A-animation.res').write_bytes(b'mocked resource')
    result=dict(artifacts=dict(active_contacts=str(folder/'contacts.json'),active_policy=str(folder/'geometry-policy.json')),sampled_conditions_pass=False)
    save(folder/'authoring/result.json',result);scenes.package(folder,prepared,result)
    game=tmp_path/'game';game.mkdir();shutil.copyfile(folder/'assets.zip',game/'source-assets.zip')
    assert set(SPEED_METHODS)<=set(games.source_method_names(SceneContacts(read(folder/'contacts.json'),folder),folder))
    # Exercise package transport only: these placeholders are not imported,
    # executed, or presented as valid engine/root/event evidence.
    (game/'tracks').mkdir();(game/'implementation').mkdir()
    for name in ('root-motion.json','root-observations.npz','contacts.json','events.json','request.json'):(game/'tracks'/name).write_bytes(b'fixture transport bytes')
    for name in ('godot_scene_game_events.gd','native_engine_clock.gd'):(game/'implementation'/name).write_bytes(b'fixture transport bytes')
    games.combine_package(game,dict(all_root_samples_pass=False),dict(gameplay_event_dispatch_verified=False),result)
    expected=lineage.package_files(folder/'correction-lineage',prepared['correction_lineage'])
    with zipfile.ZipFile(folder/'assets.zip') as scene_zip,zipfile.ZipFile(game/'game-assets.zip') as game_zip:
        for name,path in expected.items():assert scene_zip.read(name)==game_zip.read(name)==path.read_bytes()
        manifest=read(game/'package.json');assert not manifest['sampled_scene_conditions_pass'] and not manifest['release_approved']
        assert 'corrections/jobs/speed/rotation-speed-policy.json' in manifest['files_sha256']
    broken=read(folder/'prepared.json');broken['implementation_sha256'].pop(SPEED_METHODS[0]);save(folder/'prepared.json',broken)
    with pytest.raises(ValueError,match='Complete Studio scene methods'):scenes.frozen(folder)
