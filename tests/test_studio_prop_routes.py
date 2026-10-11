"""In-process real Studio dispatch with generated GLB bytes; no socket/UI."""
from pathlib import Path
from types import SimpleNamespace
import io,json,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(1,str(Path(__file__).resolve().parent))
import action_studio_server as server
import studio_props as props
from test_static_prop_asset import fixture
from gltf_tools import write_glb


def handler(path,body=b'',mime='application/json',**headers):
    h=server.Handler.__new__(server.Handler);h.path=path
    h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':mime,'Content-Length':str(len(body)),**headers}
    h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768','localhost:8768'})
    h.rfile=io.BytesIO(body);h.responses=[];h.respond=lambda code,value:h.responses.append((code,value))
    h.statuses=[];h.output_headers={};h.wfile=io.BytesIO()
    h.send_response=lambda code:h.statuses.append(code)
    h.send_header=lambda name,value:h.output_headers.update({name:value})
    h.end_headers=lambda:None
    return h


@pytest.fixture
def imported(tmp_path,monkeypatch):
    monkeypatch.setattr(props,'ASSETS',tmp_path/'assets')
    doc,binary=fixture();source=tmp_path/'source.glb';write_glb(source,doc,binary);raw=source.read_bytes()
    h=handler('/api/props/import',raw,'application/octet-stream',**{'X-Filename':'..%2FBox.glb','X-License-Note':'Self-created%20fixture'})
    h.do_POST();assert h.responses[0][0]==201
    asset=h.responses[0][1]
    return raw,asset,dict(asset_id=asset['id'],geometry_sha256=asset['geometry_sha256'],face=0,barycentric=[.25,.25,.5])


def test_import_detail_landmark_save_read_and_download_use_original_source(imported):
    raw,asset,payload=imported
    assert asset['name']=='Box.glb' and asset['license_note']=='Self-created fixture'
    assert not asset['scene_solver_integrated'] and not asset['quality_approved']
    assert server.allowed_file(asset['glb_url']).read_bytes()==raw
    download=handler(asset['glb_url']);download.do_GET()
    assert download.statuses==[200] and download.wfile.getvalue()==raw
    assert int(download.output_headers['Content-Length'])==len(raw)
    get=handler('/api/props/'+asset['id']);get.do_GET();assert get.responses==[(200,asset)]
    preview=handler('/api/props/surface-preview',json.dumps(payload).encode());preview.do_POST()
    assert preview.responses[0][0]==200 and preview.responses[0][1]['position_m']==[.25,.5,0]
    assert not preview.responses[0][1]['contact_verified']
    save=handler('/api/props/grips',json.dumps(dict(**payload,label='Left hand')).encode());save.do_POST()
    assert save.responses[0][0]==201;record=save.responses[0][1]
    get=handler('/api/props/'+asset['id']+'/grips/'+record['grip_id']);get.do_GET()
    assert get.responses==[(200,record['selection'])]
    assert json.loads(server.allowed_file(record['url']).read_bytes())==record['selection']
    download=handler(record['url']);download.do_GET()
    assert download.statuses==[200] and json.loads(download.wfile.getvalue())==record['selection']


@pytest.mark.parametrize('path',['/api/props/import','/api/props/surface-preview','/api/props/grips'])
@pytest.mark.parametrize('fault',['host','origin','type'])
def test_transport_gate_rejects_before_read_or_store(path,fault,monkeypatch):
    class NoRead:
        def read(self,*_):raise AssertionError('Rejected transport read a body')
    def forbidden(*_):raise AssertionError('Rejected transport touched the asset store')
    for name in ('import_bytes','surface_preview','save_grip'):monkeypatch.setattr(props,name,forbidden)
    h=handler(path,b'{}','application/octet-stream' if path.endswith('import') else 'application/json');h.rfile=NoRead()
    if fault=='host':h.headers['Host']='remote.example:8768'
    elif fault=='origin':h.headers['Origin']='https://remote.example'
    else:h.headers['Content-Type']='text/plain'
    h.do_POST();assert h.responses[0][0]==(415 if fault=='type' else 403)


@pytest.mark.parametrize('fault',['empty','large','negative','bad-length','chunked','incomplete','duplicate','nan','extra'])
def test_invalid_bounded_json_never_saves_a_grip(imported,fault):
    _,asset,payload=imported;body=json.dumps(dict(**payload,label='Hand')).encode()
    h=handler('/api/props/grips',body)
    if fault=='empty':h.headers['Content-Length']='0'
    elif fault=='large':h.headers['Content-Length']='16385'
    elif fault=='negative':h.headers['Content-Length']='-1'
    elif fault=='bad-length':h.headers['Content-Length']='other'
    elif fault=='chunked':h.headers['Transfer-Encoding']='chunked'
    elif fault=='incomplete':h.headers['Content-Length']=str(len(body)+1)
    elif fault=='duplicate':body=b'{"asset_id":"x","asset_id":"y"}'
    elif fault=='nan':body=b'{"value":NaN}'
    else:body=json.dumps(dict(**payload,label='Hand',unknown=True)).encode()
    if fault in ('duplicate','nan','extra'):h.rfile=io.BytesIO(body);h.headers['Content-Length']=str(len(body))
    h.do_POST();assert h.responses[0][0]==400 and props.details(asset['id'])['grip_ids']==[]


@pytest.mark.parametrize('fault',['too-large','incomplete','invalid'])
def test_bad_binary_upload_creates_no_store_entry(tmp_path,monkeypatch,fault):
    monkeypatch.setattr(props,'ASSETS',tmp_path/'assets');h=handler('/api/props/import',b'bad','application/octet-stream')
    if fault=='too-large':h.headers['Content-Length']=str(props.MAX_BYTES+1)
    elif fault=='incomplete':h.headers['Content-Length']='4'
    h.do_POST();assert h.responses[0][0]==400
    assert not props.ASSETS.exists() or not list(props.ASSETS.iterdir())


@pytest.mark.parametrize('suffix',['?extra=1','/grips/unknown','/inventory.json','/../escape'])
def test_get_requires_exact_asset_or_grip_selection(imported,suffix):
    _,asset,_=imported;h=handler('/api/props/'+asset['id']+suffix);h.do_GET();assert h.responses[0][0]==400


def test_mutated_payload_is_not_served_or_reused(imported):
    raw,asset,payload=imported;props.bounded_path(asset['id'],'prop.glb').write_bytes(raw+b'changed')
    h=handler('/api/props/'+asset['id']);h.do_GET();assert h.responses[0][0]==400
    with pytest.raises(ValueError):server.allowed_file(asset['glb_url'])
    download=handler(asset['glb_url']);download.do_GET();assert download.responses[0][0]==400
    h=handler('/api/props/import',raw,'application/octet-stream');h.do_POST();assert h.responses[0][0]==400


def test_get_keeps_loopback_gate_before_store(imported,monkeypatch):
    _,asset,_=imported
    def forbidden(*_):raise AssertionError('Rejected host accessed prop data')
    monkeypatch.setattr(props,'details',forbidden)
    h=handler('/api/props/'+asset['id'],**{'Host':'remote.example:8768'});h.do_GET()
    assert h.responses[0][0]==403
