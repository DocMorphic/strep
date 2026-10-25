"""Source/history transport fixtures, not numerical or engine acceptance."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import surface_clip_scene_source as bridge
import studio_surface_clip_jobs as jobs
import studio_surface_clip_routes as routes
import studio_native_scene as scenes
from strep import read,save,sha256
from test_studio_surface_clip import payload,publish_fixture,handler
from test_studio_native_scene import setup


def completed(tmp_path,monkeypatch,*,edit=False):
    draft,path,resolver=setup(tmp_path,monkeypatch,edit=edit)
    monkeypatch.setattr(jobs,'ROOT',tmp_path)
    p=payload();p['source_sha256']=sha256(path)
    folder=jobs.prepare(p);attempt,r,receipt=publish_fixture(folder)
    (folder/'original.glb').write_bytes(path.read_bytes());(folder/'candidate.glb').write_bytes(path.read_bytes())
    r['files']['original']['sha256']=sha256(path)
    r['files']['candidate']=dict(path='candidate.glb',sha256=sha256(path),label='Candidate')
    r['duration_s']=draft['scene']['duration_s']
    r['summary']=dict(status='complete_numerical_candidate',whole_clip_sampled=True,total_keys=11,validated_through=10,finalized_through=10,
        transition_review_required=True,quality_approved=False,release_approved=False)
    save(attempt/'result.json',r);receipt['result_sha256']=sha256(attempt/'result.json');save(attempt/'publication.json',receipt)
    m=bridge.metadata(folder.name,attempt.name)
    for a in draft['scene']['actors'].values():a.update(glb=m['source_url'],sha256=m['glb_sha256'],animation_index=0)
    return folder,attempt,draft,m


def test_metadata_and_complete_portable_history(tmp_path,monkeypatch):
    folder,attempt,draft,m=completed(tmp_path,monkeypatch);before=copy.deepcopy(draft)
    dest=tmp_path/'history';receipt=bridge.snapshot(draft,dest);record=bridge.verify(draft,dest,receipt)
    assert draft==before and record['original_clips_included'] and not record['scene_contacts_applied']
    assert len(record['parents'])==1 and set(record['selection'])==set(draft['scene']['actors'])
    assert len(receipt['files_sha256'])==8
    files=bridge.package_files(dest,receipt);assert len(files)==9
    assert any(name.endswith('/original.glb') for name in files)
    assert any(name.endswith('/request.json') for name in files)
    assert m['root_node']==payload()['root'] and m['transition_review_required'] and not m['quality_approved']


@pytest.mark.parametrize('fault',['checkpoint','unresolved','population','last','finalized','last_type','final_type','approval','duration','source','index','hash','rejected','query'])
def test_unusable_or_changed_selection_rejected(tmp_path,monkeypatch,fault):
    folder,attempt,draft,m=completed(tmp_path,monkeypatch);r=read(attempt/'result.json');a=next(iter(draft['scene']['actors'].values()))
    if fault in ('checkpoint','unresolved'):r['summary']['status']='checkpointed' if fault=='checkpoint' else 'unresolved'
    elif fault=='population':r['summary']['whole_clip_sampled']=False
    elif fault=='last':r['summary']['validated_through']=9
    elif fault=='finalized':r['summary']['finalized_through']=9
    elif fault in ('last_type','final_type'):
        r['summary'].update(total_keys=2,validated_through=1,finalized_through=1)
        r['summary']['validated_through' if fault=='last_type' else 'finalized_through']=True
    elif fault=='approval':r['summary']['quality_approved']=True
    elif fault=='duration':r['duration_s']=0
    elif fault=='source':r['files']['original']['sha256']='a'*64
    elif fault=='index':a['animation_index']=True
    elif fault=='hash':a['sha256']='e'*64
    elif fault=='rejected':a['glb']=a['glb'].replace('candidate.glb','rejected.glb')
    else:a['glb']+='?other=1'
    save(attempt/'result.json',r);p=read(attempt/'publication.json');p['result_sha256']=sha256(attempt/'result.json');save(attempt/'publication.json',p)
    with pytest.raises(ValueError):bridge.plan(draft)


@pytest.mark.parametrize('fault',['original','settings','summary','copy','extra','receipt','selection'])
def test_history_tampering_rejected(tmp_path,monkeypatch,fault):
    folder,attempt,draft,m=completed(tmp_path,monkeypatch);dest=tmp_path/'history';receipt=bridge.snapshot(draft,dest)
    if fault=='original':(folder/'original.glb').write_bytes(b'changed')
    elif fault=='settings':p=read(folder/'request.json');p['limits']['floor_depth_m']=.1;save(folder/'request.json',p)
    elif fault=='summary':p=read(attempt/'result.json');p['summary']['transition_review_required']=False;save(attempt/'result.json',p)
    elif fault=='copy':next(dest.rglob('original.glb')).write_bytes(b'changed')
    elif fault=='extra':(dest/'extra.json').write_text('{}')
    elif fault=='receipt':receipt['files_sha256']={}
    else:next(iter(draft['scene']['actors'].values()))['sha256']='0'*64
    with pytest.raises(ValueError):bridge.verify(draft,dest,receipt)


def test_scene_snapshot_and_game_methods_keep_history(tmp_path,monkeypatch):
    folder,attempt,draft,m=completed(tmp_path,monkeypatch)
    resolver=lambda url:jobs.served_file(url)
    dest=scenes.folder_for('surface-scene');p=scenes.prepare(draft,dest,resolver)
    assert p['surface_correction_lineage'] and scenes.frozen(dest)==p
    assert set(bridge.METHODS)<=set(p['implementation_sha256'])
    from studio_native_scene_game import source_method_names
    from native_scene_contacts import SceneContacts
    scene=SceneContacts(read(dest/'contacts.json'),dest)
    assert set(bridge.METHODS)<=set(source_method_names(scene,dest))
    record=read(dest/'surface-correction-lineage/record.json');assert record['transition_review_required']
    p.pop('surface_correction_lineage');save(dest/'prepared.json',p)
    with pytest.raises(ValueError,match='history selection'):scenes.frozen(dest)


def test_metadata_route_uses_publication_validation(tmp_path,monkeypatch):
    folder,attempt,draft,m=completed(tmp_path,monkeypatch)
    h=handler();h.path=f'/api/surface-clip-jobs/{folder.name}/attempt/{attempt.name}/scene-source'
    assert routes.dispatch_get(h) and h.responses[-1][0]==200
    (folder/'candidate.glb').write_bytes(b'changed')
    h=handler();h.path=f'/api/surface-clip-jobs/{folder.name}/attempt/{attempt.name}/scene-source'
    assert routes.dispatch_get(h) and h.responses[-1][0]==400


def test_history_survives_scene_and_game_archives(tmp_path,monkeypatch):
    # Real preparation/packaging/receipts, with explicitly mocked engine outputs.
    import zipfile
    import test_studio_native_scene_game as fixture
    import studio_native_scene_game as game
    folder,attempt,draft,m=completed(tmp_path,monkeypatch,edit=True)
    monkeypatch.setattr(fixture,'source_setup',lambda *_:(draft,folder/'candidate.glb',jobs.served_file))
    payload,source=fixture.setup(tmp_path,monkeypatch)
    dest=game.folder_for('surface-game');game.prepare(payload,dest);game.run(dest)
    history=read(source/'surface-correction-lineage/record.json')
    with zipfile.ZipFile(source/'assets.zip') as scene_zip,zipfile.ZipFile(dest/'game-assets.zip') as game_zip:
        names=['surface-corrections/'+name for name in ['record.json',*history['files_sha256']]]
        assert len(names)==9
        for name in names:
            assert scene_zip.read(name)==game_zip.read(name)==(source/'surface-correction-lineage'/name.removeprefix('surface-corrections/')).read_bytes()
        manifest=read(dest/'package.json')
        assert set(names)<=set(manifest['files_sha256']) and not manifest['quality_approved'] and not manifest['release_approved']
