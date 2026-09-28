import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pack_local_gltf import pack
from rig_asset import read_asset


def fixture(folder):
    (folder/'a.bin').write_bytes(bytes(range(12)))
    (folder/'b.bin').write_bytes(bytes(range(16,32)))
    (folder/'eye.png').write_bytes(b'\x89PNG\r\n\x1a\nunchanged test image payload')
    value=dict(asset={'version':'2.0'},buffers=[dict(uri='a.bin',byteLength=12),dict(uri='b.bin',byteLength=16)],
        bufferViews=[dict(buffer=0,byteOffset=4,byteLength=8),dict(buffer=1,byteOffset=0,byteLength=16)],
        nodes=[dict(name='unchanged',translation=[0,1,0])],scenes=[dict(nodes=[0])],scene=0,
        images=[dict(uri='eye.png',mimeType='image/png')])
    source=folder/'model.gltf';source.write_text(json.dumps(value));return source,value


def test_pack_preserves_all_buffer_views_and_node_definitions(tmp_path):
    source,value=fixture(tmp_path);before=source.read_bytes();output=tmp_path/'model.glb'
    report=pack(source,output);doc,blob=read_asset(output)
    assert source.read_bytes()==before and doc['nodes']==value['nodes']
    assert report['buffer_views_verified']==2 and report['images_embedded']==1
    for i,data in enumerate([bytes(range(4,12)),bytes(range(16,32)),(tmp_path/'eye.png').read_bytes()]):
        view=doc['bufferViews'][i]
        assert blob[view['byteOffset']:view['byteOffset']+view['byteLength']]==data
    with pytest.raises(ValueError,match='already exists'):pack(source,output)


@pytest.mark.parametrize('uri',['../outside.bin','https://example.com/a.bin','file:///a.bin','%2e%2e/outside.bin'])
def test_pack_rejects_external_or_traversing_resources(tmp_path,uri):
    source,value=fixture(tmp_path);value['buffers'][0]['uri']=uri;source.write_text(json.dumps(value))
    with pytest.raises(ValueError):pack(source,tmp_path/'result.glb')
    assert not (tmp_path/'result.glb').exists()


def test_explicit_resource_repair_is_recorded_and_original_unchanged(tmp_path):
    source,value=fixture(tmp_path);value['images'][0]['uri']='broken.png';source.write_text(json.dumps(value));before=source.read_bytes()
    with pytest.raises(ValueError,match='missing'):pack(source,tmp_path/'result.glb')
    report=pack(source,tmp_path/'result.glb',{'broken.png':'eye.png'})
    assert report['resource_overrides']=={'broken.png':'eye.png'} and source.read_bytes()==before
