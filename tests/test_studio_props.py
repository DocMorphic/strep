"""Generated local prop-store fixtures; no real assets or scene solver."""
import hashlib,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(1,str(Path(__file__).resolve().parent))
import studio_props as store
from test_static_prop_asset import fixture
from gltf_tools import write_glb


@pytest.fixture
def upload(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'ASSETS',tmp_path/'assets')
    path=tmp_path/'source.glb';document,binary=fixture();write_glb(path,document,binary)
    raw=path.read_bytes();result=store.import_bytes(raw,'../Box.glb','Self-created test fixture')
    payload=dict(asset_id=result['id'],geometry_sha256=result['geometry_sha256'],face=0,barycentric=[.25,.25,.5])
    return raw,result,payload


def test_import_preserves_payload_and_scale(upload):
    raw,result,_=upload
    assert result['id']==hashlib.sha256(raw).hexdigest() and result['name']=='Box.glb'
    assert store.served_file(result['glb_url']).read_bytes()==raw
    assert result['inventory']['source_scale_retained']
    assert result['license_note_source']=='User supplied; rights not verified'
    assert not result['scene_solver_integrated'] and not result['quality_approved'] and not result['release_approved']


def test_duplicate_import_retains_original_metadata(upload):
    raw,result,_=upload
    repeated=store.import_bytes(raw,'Renamed.glb','New license assertion')
    assert repeated==result


def test_grip_roundtrip_is_immutable_and_source_bound(upload):
    _,result,payload=upload
    preview=store.surface_preview(payload);assert preview['position_m']==[.25,.5,0]
    saved=store.save_grip(dict(**payload,label='Left hand'))
    assert store.grip(result['id'],saved['grip_id'])==saved['selection']
    raw=store.served_file(saved['url']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==saved['grip_id']
    assert store.save_grip(dict(**payload,label='Left hand'))==saved
    different=store.save_grip({**payload,'label':'Right hand','barycentric':[.5,.5,0]})
    assert different['grip_id']!=saved['grip_id']
    assert store.grip(result['id'],saved['grip_id'])==saved['selection']
    assert sorted(store.details(result['id'])['grip_ids'])==sorted([saved['grip_id'],different['grip_id']])
    assert not preview['contact_verified'] and not preview['outward_normal_verified']


@pytest.mark.parametrize('identifier',['../escape','A'*64,'a'*63,'a'*65,False,None])
def test_invalid_identifiers_rejected(identifier):
    with pytest.raises(ValueError):store.details(identifier)


@pytest.mark.parametrize('url',['/files/prop-assets/../../token','https://example.com/file',
    '/files/prop-assets/'+'a'*64+'/prop.glb?x=1','/files/prop-assets/'+'a'*64+'/inventory.json'])
def test_serving_is_allowlisted(url):
    assert store.served_file(url) is None


def test_corrupted_asset_cannot_be_reused_or_served(upload):
    raw,result,payload=upload;path=store.bounded_path(result['id'],'prop.glb')
    path.write_bytes(raw+b'changed')
    with pytest.raises(ValueError):store.details(result['id'])
    with pytest.raises(ValueError):store.import_bytes(raw,'Prop.glb')
    with pytest.raises(ValueError):store.surface_preview(payload)


def test_corrupted_grip_rejected(upload):
    _,result,payload=upload;saved=store.save_grip(dict(**payload,label='Hand'))
    path=store.bounded_path(result['id'],f'grips/{saved["grip_id"]}.json')
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):store.served_file(saved['url'])


def test_hashed_false_landmark_rejected(upload):
    _,result,payload=upload;saved=store.save_grip(dict(**payload,label='Hand'))
    record={**saved['selection'],'position_m':[100,100,100]}
    raw=json.dumps(record).encode();digest=hashlib.sha256(raw).hexdigest()
    store.bounded_path(result['id'],f'grips/{digest}.json').write_bytes(raw)
    with pytest.raises(ValueError):store.grip(result['id'],digest)


def test_geometry_and_inventory_change_rejected(upload):
    _,result,payload=upload
    with pytest.raises(ValueError):store.surface_preview({**payload,'geometry_sha256':'0'*64})
    path=store.bounded_path(result['id'],'inventory.json');inventory=json.loads(path.read_bytes())
    inventory['bounds_max_m']=[2,2,2];path.write_text(json.dumps(inventory),encoding='utf-8')
    with pytest.raises(ValueError):store.surface_preview(payload)


@pytest.mark.parametrize('label',['','   ',120*'x'+'x',123])
def test_bad_grip_labels_rejected(upload,label):
    with pytest.raises(ValueError):store.save_grip(dict(**upload[2],label=label))


def test_upload_failure_keeps_store_empty(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'ASSETS',tmp_path/'assets')
    with pytest.raises(ValueError):store.import_bytes(b'Invalid GLB','Prop.glb')
    assert not list(store.ASSETS.iterdir())


def test_partial_write_failure_removes_only_new_upload(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'ASSETS',tmp_path/'assets')
    path=tmp_path/'source.glb';document,binary=fixture();write_glb(path,document,binary)
    sentinel=tmp_path/'sentinel';sentinel.write_bytes(b'keep')
    def fail(*args):raise OSError('simulated metadata write failure')
    monkeypatch.setattr(store,'save',fail)
    with pytest.raises(OSError):store.import_bytes(path.read_bytes(),'Prop.glb')
    assert sentinel.read_bytes()==b'keep' and not list(store.ASSETS.iterdir())
