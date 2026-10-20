"""Actual API geometry/landmark round trips, including transformed instances."""
import hashlib
import numpy as np
import pytest
from test_studio_prop_routes import handler,imported
from test_static_prop_asset import fixture
import studio_props as props
import action_studio_server as server
from gltf_tools import write_glb
from build_desktop import render,ROOT


def test_complete_canonical_geometry_roundtrip(imported):
    raw,asset,payload=imported
    h=handler('/api/props/'+asset['id']+'/geometry');h.do_GET()
    code,geometry=h.responses[0];assert code==200
    vertices=np.asarray(geometry['vertices_m'],dtype='<f8');faces=np.asarray(geometry['faces'],dtype='<i8')
    assert hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest()==asset['geometry_sha256']
    np.testing.assert_array_equal(np.asarray(payload['barycentric'])@vertices[faces[payload['face']]],props.surface_preview(payload)['position_m'])
    assert props.bounded_path(asset['id'],'prop.glb').read_bytes()==raw


def test_transformed_instances_keep_distinct_faces(tmp_path,monkeypatch):
    monkeypatch.setattr(props,'ASSETS',tmp_path/'store')
    doc,binary=fixture();doc['nodes']=[dict(mesh=0,translation=[2,3,4]),dict(mesh=0,scale=[-2,3,1])];doc['scenes'][0]['nodes']=[0,1]
    path=tmp_path/'object.glb';write_glb(path,doc,binary);asset=props.import_bytes(path.read_bytes(),'two.glb')
    geometry=props.preview_geometry(asset['id']);assert geometry['faces']==[[0,1,2],[3,4,5]]
    np.testing.assert_array_equal(geometry['vertices_m'],[[2,3,4],[3,3,4],[2,4,4],[0,0,0],[-2,0,0],[0,3,0]])
    for face,normal in [(0,[0,0,1]),(1,[0,0,-1])]:
        payload=dict(asset_id=asset['id'],geometry_sha256=asset['geometry_sha256'],face=face,barycentric=[.2,.3,.5])
        point=props.surface_preview(payload);np.testing.assert_array_equal(point['winding_normal'],normal)
        saved=props.save_grip(dict(**payload,label='Grip'))
        download=handler(saved['url']);download.do_GET()
        assert download.statuses==[200] and download.wfile.getvalue()==props.served_file(saved['url']).read_bytes()
        assert props.grip(asset['id'],saved['grip_id'])==saved['selection']


@pytest.mark.parametrize('suffix',['/geometry?x=1','/geometry/extra','/geometry#fragment'])
def test_geometry_requires_exact_path(imported,suffix):
    _,asset,_=imported;h=handler('/api/props/'+asset['id']+suffix);h.do_GET();assert h.responses[0][0]==400


def test_geometry_rejects_changed_source_and_remote_host(imported,monkeypatch):
    raw,asset,_=imported;url='/api/props/'+asset['id']+'/geometry'
    h=handler(url,**{'Host':'remote.example'});h.do_GET();assert h.responses[0][0]==403
    props.bounded_path(asset['id'],'prop.glb').write_bytes(raw+b'changed')
    h=handler(url);h.do_GET();assert h.responses[0][0]==400


def test_built_panel_and_public_modules_are_available():
    page=render();assert page.count('id="propGripPanel"')==1
    assert page.count('mountPropGripEditor()).catch')==1
    for name in ['prop-grip-editor.mjs','prop-grip-viewer.mjs']:
        assert server.allowed_file('/'+name)==ROOT/'scripts'/name
    assert server.allowed_file('/prop-grip-editor.mjs/extra') is None
