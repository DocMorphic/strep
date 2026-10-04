"""Real CPU corrections, portable provenance and source/intent integrity."""
import copy
from pathlib import Path
import sys
import zipfile
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_correction_lineage as lineage
import studio_native_scene_fit as corrections
import studio_native_scene as scenes
from strep import read,save,sha256
from test_studio_native_scene_fit import setup,revised


def completed(tmp_path,monkeypatch,*,partner=False,revision=False):
    payload,source,resolver=setup(tmp_path,monkeypatch)
    if partner:
        payload['draft']['scene']['actors']['B']=copy.deepcopy(payload['draft']['scene']['actors']['A'])
        payload['draft']['scene']['actors']['B']['placement']['translation_m']=[3,0,0]
    if revision:revised(payload)
    job=corrections.folder_for('first');corrections.prepare(payload,job,resolver);corrections.run(job)
    m=corrections.manifest('first');draft=copy.deepcopy(payload['draft']);draft.pop('contact_revision',None)
    for name,row in m['actors'].items():draft['scene']['actors'][name].update(glb=row['candidate_url'],sha256=row['candidate_sha256'])
    return payload,job,m,draft


def test_portable_caps_clips_permissions_and_partner_population(tmp_path,monkeypatch):
    payload,job,m,draft=completed(tmp_path,monkeypatch,partner=True)
    before={n:sha256(job/n) for n in ('prepared.json','completion.json','fit/result.json')}
    folder=tmp_path/'lineage';receipt=lineage.snapshot(draft,folder);record=lineage.verify(draft,folder,receipt)
    assert record['selection']['A']['selected_role']=='proposal' and record['selection']['B']['selected_role']=='unchanged'
    assert record['jobs']['first']['correction_scene_context_preserved'] and record['quality_approved'] is False
    from native_scene_contacts import SceneContacts
    from native_scene_edit import SceneEdits
    from native_scene_geometry import policy_for
    base=folder/'jobs/first';original=SceneContacts(read(base/'original-scene.json'),base)
    proposed=SceneContacts(read(base/'candidate-scene.json'),base)
    assert set(original.actors)==set(proposed.actors)=={'A','B'}
    digest=sha256(base/'original-scene.json')
    SceneEdits(read(base/'permissions.json'),original,digest)
    policy_for(read(base/'geometry-policy.json'),original,digest)
    with np.load(base/'source-rate-caps.npz') as a,np.load(job/'fit/source-rate-caps.npz') as b:
        assert a.files==b.files
        for n in a.files:assert a[n].dtype==b[n].dtype and np.array_equal(a[n],b[n])
    assert before=={n:sha256(job/n) for n in before}
    assert not any(str(tmp_path) in p.read_text() for p in folder.rglob('*.json'))


def test_changed_scene_context_does_not_inherit_parent_checks(tmp_path,monkeypatch):
    payload,job,m,draft=completed(tmp_path,monkeypatch)
    draft['scene']['actors']['Renamed']=draft['scene']['actors'].pop('A');draft['scene']['contacts'][0]['actor']='Renamed'
    draft['geometry']['limits']['penetration_m']=.001
    receipt=lineage.snapshot(draft,tmp_path/'lineage');r=lineage.verify(draft,tmp_path/'lineage',receipt)
    assert r['selection']['Renamed']['correction_actor']=='A'
    assert not r['jobs']['first']['correction_scene_context_preserved']
    assert r['numerical_decisions_apply_to_parent_job_only'] and not r['quality_approved']


def test_selecting_original_keeps_its_role_and_exact_hash(tmp_path,monkeypatch):
    payload,job,m,draft=completed(tmp_path,monkeypatch)
    draft['scene']['actors']['A'].update(glb=m['actors']['A']['original_url'],sha256=m['actors']['A']['original_sha256'])
    r,files,bindings=lineage.plan(draft)
    assert r['selection']['A']['selected_role']=='original' and r['selection']['A']['selected_sha256']==payload['draft']['scene']['actors']['A']['sha256']
    assert not r['jobs']['first']['correction_scene_context_preserved']


def test_fresh_patch_revision_keeps_prior_intent_on_portable_candidate(tmp_path,monkeypatch):
    payload,job,m,draft=completed(tmp_path,monkeypatch,revision=True)
    folder=tmp_path/'lineage';receipt=lineage.snapshot(draft,folder);record=lineage.verify(draft,folder,receipt)
    prior=record['jobs']['first']['prior_intents'];assert len(prior)==1
    before=read(folder/'jobs/first'/prior[0]['scene_file']);candidate=read(folder/'jobs/first/candidate-scene.json')
    assert before['actors']==candidate['actors']
    assert before['contacts']==payload['draft']['contact_revision']['baseline']['scene']['contacts']
    assert prior[0]['measured_pass'] is read(job/'original-intent-audit/result.json')['passed']


@pytest.mark.parametrize('mode',['resume','fresh'])
def test_complete_ancestor_closure_keeps_original_caps(tmp_path,monkeypatch,mode):
    payload,job,m,draft=completed(tmp_path,monkeypatch)
    if mode=='resume':
        payload['resume_from']='first'
        old_url=payload['draft']['scene']['actors']['A']['glb'];source=Path(read(job/'prepared.json')['sources']['A']['path'])
        resolver=lambda url:source if url==old_url else None
    else:
        payload['draft']=draft;resolver=lambda url:corrections.served_file(url.removeprefix('/files/'))
    second=corrections.folder_for('second');corrections.prepare(payload,second,resolver);corrections.run(second)
    current=corrections.manifest('second');draft=copy.deepcopy(payload['draft'])
    for name,row in current['actors'].items():draft['scene']['actors'][name].update(glb=row['candidate_url'],sha256=row['candidate_sha256'])
    receipt=lineage.snapshot(draft,tmp_path/'lineage');record=lineage.verify(draft,tmp_path/'lineage',receipt)
    assert set(record['jobs'])=={'first','second'}
    assert record['jobs']['second']['resume_from']==('first' if mode=='resume' else None)
    assert sha256(tmp_path/'lineage/jobs/first/source-rate-caps.npz')==sha256(job/'fit/source-rate-caps.npz')


@pytest.mark.parametrize('fault',['caps','original','candidate','permissions','record','drop','extra','parent','selection'])
def test_changed_lineage_or_parent_evidence_is_rejected(tmp_path,monkeypatch,fault):
    payload,job,m,draft=completed(tmp_path,monkeypatch);folder=tmp_path/'lineage';receipt=lineage.snapshot(draft,folder)
    paths={'caps':'jobs/first/source-rate-caps.npz','original':'jobs/first/source/actor-0.glb',
        'candidate':'jobs/first/candidate/actor-0.glb','permissions':'jobs/first/permissions.json','record':'record.json'}
    if fault in paths:(folder/paths[fault]).write_bytes(b'changed')
    elif fault=='drop':receipt['files_sha256'].pop('jobs/first/source-rate-caps.npz')
    elif fault=='extra':(folder/'extra.txt').write_text('unbound')
    elif fault=='parent':(job/'fit/probes/final/A.glb').write_bytes(b'changed')
    else:draft['scene']['actors']['A']['sha256']='0'*64
    with pytest.raises((ValueError,OSError)):lineage.verify(draft,folder,receipt)


@pytest.mark.parametrize('url',[lineage.PREFIX+'../clip.glb',lineage.PREFIX+'job/input/../clip.glb',lineage.PREFIX+'job/clip.glb?x=1',lineage.PREFIX+'job/%2e%2e/clip.glb'])
def test_unsafe_origin_urls_reject(url):
    with pytest.raises(ValueError):lineage.origin(url)


def test_scene_package_includes_complete_source_bound_lineage(tmp_path,monkeypatch):
    payload,job,m,draft=completed(tmp_path,monkeypatch)
    engine=tmp_path/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe';engine.parent.mkdir(parents=True);engine.write_bytes(b'mocked; not run')
    scene_folder=scenes.folder_for('scene');prepared=scenes.prepare(draft,scene_folder,lambda url:corrections.served_file(url.removeprefix('/files/')))
    assert 'native_correction_lineage.py' in prepared['implementation_sha256']
    assert scenes.frozen(scene_folder)==prepared
    assets=scene_folder/'authoring/actors-engine';assets.mkdir(parents=True);(assets/'A-animation.res').write_bytes(b'mocked resource')
    result=dict(artifacts=dict(active_contacts=str(scene_folder/'contacts.json')),sampled_conditions_pass=False)
    save(scene_folder/'authoring/result.json',result);scenes.package(scene_folder,prepared,result)
    with zipfile.ZipFile(scene_folder/'assets.zip') as z:
        extracted=tmp_path/'extracted';z.extractall(extracted)
        for name,path in lineage.package_files(scene_folder/'correction-lineage',prepared['correction_lineage']).items():
            assert z.read(name)==path.read_bytes()
        assert 'corrections/record.json' in read(extracted/'package.json')['files_sha256']
    assert 'correction-lineage/record.json' in scenes.download_names(prepared)
    dropped=read(scene_folder/'prepared.json');dropped['correction_lineage']=None;save(scene_folder/'prepared.json',dropped)
    with pytest.raises(ValueError):scenes.frozen(scene_folder)
    with pytest.raises(ValueError):scenes.frozen(scene_folder,current_methods=False)


def test_only_old_ordinary_scene_archives_accept_missing_lineage_method(tmp_path,monkeypatch):
    from test_studio_native_scene import setup as scene_setup
    draft,source,resolver=scene_setup(tmp_path,monkeypatch)
    folder=scenes.folder_for('legacy');scenes.prepare(draft,folder,resolver)
    p=read(folder/'prepared.json');p.pop('correction_lineage');p['implementation_sha256'].pop('native_correction_lineage.py');save(folder/'prepared.json',p)
    assert scenes.frozen(folder,current_methods=False)==p
    with pytest.raises(ValueError):scenes.frozen(folder)


def test_only_old_ordinary_game_archives_accept_missing_lineage_method(tmp_path,monkeypatch):
    import studio_native_scene_game as games
    from test_studio_native_scene_game import setup as game_setup
    payload,source=game_setup(tmp_path,monkeypatch)
    folder=games.folder_for('legacy');games.prepare(payload,folder)
    p=read(folder/'prepared.json');p.pop('correction_lineage_included');p['implementation_sha256'].pop('native_correction_lineage.py');save(folder/'prepared.json',p)
    assert games.frozen(folder,current_methods=False)[0]==p
    with pytest.raises(ValueError):games.frozen(folder)
