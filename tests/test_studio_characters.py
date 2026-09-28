import copy
import json
import sys
import threading
import shutil
import zipfile
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_characters as chars
from action_studio_server import allowed_file,Handler
from strep import ROOT,read,save,sha256


@pytest.fixture
def store(tmp_path,monkeypatch):
    monkeypatch.setattr(chars,'ASSETS',tmp_path/'characters')
    monkeypatch.setattr(chars,'JOBS',tmp_path/'jobs')
    return (ROOT/'assets/characters/cesium-man/CesiumMan.glb').read_bytes()


def test_local_import_preserves_bytes_and_recognizes_only_exact_fixture(store):
    asset=chars.import_bytes(store,'../../CesiumMan.glb')
    assert asset['name']=='CesiumMan.glb' and asset['recognized_fixture']
    assert sha256(chars.ASSETS/asset['id']/'character.glb')==asset['id']
    assert len(asset['profile']['mapping'])==19
    assert asset['profile']['axis_alignment_xyzw']['LeftFoot']==[0,0,0,1]
    assert chars.import_bytes(store,'renamed.glb')['name']=='CesiumMan.glb'
    assert len(chars.list_assets())==1


def test_unreal_style_mapping_suggestions_remain_unambiguous():
    names=['pelvis','spine_02','spine_03','neck_01','Head','upperarm_l','lowerarm_l','hand_l',
        'upperarm_r','lowerarm_r','hand_r','thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r']
    inventory=dict(nodes=[dict(index=i,name=name,skin_joint=True) for i,name in enumerate(names)])
    mapping=chars.suggest_mapping(inventory)
    assert len(mapping)==19 and mapping['Chest']==2 and mapping['LeftToeBase']==14
    inventory['nodes'].append(dict(index=19,name='spine_02',skin_joint=True))
    assert 'Spine2' not in chars.suggest_mapping(inventory)


def test_profiles_are_immutable_and_hash_bound(store):
    asset=chars.import_bytes(store,'character.glb');profile=asset['profile']
    first=chars.save_profile(dict(asset_id=asset['id'],profile=profile))
    changed=copy.deepcopy(profile);changed['world_offset_m']=[0,.1,0]
    second=chars.save_profile(dict(asset_id=asset['id'],profile=changed))
    assert first['profile_id']!=second['profile_id']
    assert read(chars.profile_path(asset['id'],first['profile_id']))['world_offset_m']==[0,0,0]
    assert chars.details(asset['id'])['profile_id']==second['profile_id']
    bad=copy.deepcopy(profile);bad['character_sha256']='0'*64
    with pytest.raises(ValueError,match='checksum'):chars.save_profile(dict(asset_id=asset['id'],profile=bad))
    bad=copy.deepcopy(profile);bad['mapping']['LeftHand']=bad['mapping']['RightHand']
    with pytest.raises(ValueError,match='distinct'):chars.save_profile(dict(asset_id=asset['id'],profile=bad))


@pytest.mark.parametrize('value',['../x','a'*63,'A'*64,None])
def test_character_identifiers_cannot_escape_storage(store,value):
    with pytest.raises(ValueError):chars.asset_folder(value)


def test_invalid_upload_does_not_leave_partial_character(store,monkeypatch):
    with pytest.raises(ValueError):chars.import_bytes(b'not glb','character.glb')
    assert chars.list_assets()==[]
    assert not list(chars.ASSETS.glob('_incoming*'))
    monkeypatch.setattr(chars,'MAX_UPLOAD',16)
    with pytest.raises(ValueError,match='32 MiB'):chars.import_bytes(store,'big.glb')


def test_rig_job_pins_source_and_rejects_path_or_profile_mismatch(store):
    asset=chars.import_bytes(store,'character.glb');saved=chars.save_profile(dict(asset_id=asset['id'],profile=asset['profile']))
    payload=dict(asset_id=asset['id'],profile_id=saved['profile_id'],kind='transfer',motion_url='/files/action-jobs/body-holdout-seed77/takes/wave-seed-77/motion.npz')
    request,source,profile=chars.validate_job(payload,allowed_file)
    assert request['source_motion_sha256']==sha256(source)
    assert sha256(profile)==saved['profile_id']
    for url in ['/files/rig-jobs/../../models/motion.npz','http://example.com/motion.npz','/files/action-jobs/absent/motion.npz']:
        with pytest.raises(ValueError):chars.validate_job({**payload,'motion_url':url},allowed_file)
    with pytest.raises(ValueError):chars.validate_job({**payload,'kind':'neutral'},allowed_file)


def test_character_files_are_served_only_inside_allowed_roots():
    assert allowed_file('/files/character-assets/'+'a'*64+'/character.glb')
    assert allowed_file('/files/rig-jobs/example/transfer/character.glb')
    assert allowed_file('/files/character-assets/../../models/private.json') is None
    assert allowed_file('/files/rig-jobs/example/supervisor.log') is None


def test_optional_contact_draft_failure_keeps_valid_transfer(tmp_path,monkeypatch):
    """A rig without optional toe mappings can transfer, even with cleanup on."""
    from rig_studio_job import neutral,run
    import action_worker_lock
    # Exercise the real lock in isolated test storage, never contend with a
    # user's long-running Studio job or overwrite its lock file.
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    folder=tmp_path/'job';source=folder/'source';source.mkdir(parents=True)
    character=ROOT/'assets/characters/cesium-man/CesiumMan.glb'
    shutil.copyfile(character,source/'character.glb')
    profile=read(character.parent/'rig-profile-v2.json')
    for role in ('LeftToeBase','RightToeBase'):
        profile['mapping'].pop(role)
        profile['axis_alignment_xyzw'].pop(role,None)
    save(source/'rig-profile.json',profile)
    neutral(source/'motion.npz')
    save(folder/'request.json',dict(kind='transfer',asset_id=sha256(character),
        profile_id=sha256(source/'rig-profile.json'),source_motion_sha256=sha256(source/'motion.npz'),
        label='Optional toe mapping regression',correct_contacts=True))
    run(folder)
    result=read(folder/'result.json')
    assert read(folder/'pipeline.json')['status']=='complete'
    assert result['correction_status']=='unsupported'
    assert set(result['variants'])=={'transfer'}
    assert result['variants']['transfer']['root_track'].endswith('/transfer/root-motion.json')
    assert 'toe-base' in result['note']
    with zipfile.ZipFile(folder/'character-animation.zip') as archive:
        assert archive.read('transfer/character.glb')==(folder/'transfer/character.glb').read_bytes()
        assert 'correction-unavailable.json' in archive.namelist()


def test_ground_inspection_is_attached_only_to_matching_export(store):
    folder=chars.JOBS/'fixture';(folder/'transfer').mkdir(parents=True)
    save(folder/'request.json',dict(label='Test',asset_id='a'*64,kind='transfer'))
    save(folder/'pipeline.json',dict(status='complete'))
    result=dict(variants=dict(transfer=dict(sha256='b'*64)))
    save(folder/'result.json',result)
    save(folder/'transfer/ground-audit.json',dict(glb_sha256='b'*64,worst_floor=dict(depth_m=.04,frame=9),
        foot_envelope_support=[dict(hover_max_m=.1,worst_hover_frame=7)],sole_draft_error=None))
    inspection=chars.jobs()[0]['result']['variants']['transfer']['ground_inspection']
    assert inspection['worst_floor_frame']==9 and inspection['worst_hover_frame']==7
    result['variants']['transfer']['sha256']='c'*64;save(folder/'result.json',result)
    assert 'ground_inspection' not in chars.jobs()[0]['result']['variants']['transfer']


def test_http_import_checks_origin_and_rejects_invalid_glb(store):
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);host=f'127.0.0.1:{server.server_port}'
    server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        client=HTTPConnection(host)
        client.request('POST','/api/characters/import',body=store,headers={'Content-Type':'application/octet-stream','Origin':'https://example.com'})
        response=client.getresponse();assert response.status==403;response.read();client.close()
        client=HTTPConnection(host)
        client.request('POST','/api/characters/import',body=b'bad',headers={'Content-Type':'application/octet-stream','Origin':'http://'+host})
        response=client.getresponse();assert response.status==400;response.read();client.close()
        client=HTTPConnection(host)
        client.request('POST','/api/characters/import',body=store,headers={'Content-Type':'application/octet-stream','Origin':'http://'+host,'X-Filename':'uploaded.glb'})
        response=client.getresponse();assert response.status==201
        body=json.loads(response.read());assert body['name']=='uploaded.glb'
        client.close()
    finally:
        server.shutdown();server.server_close();thread.join()
