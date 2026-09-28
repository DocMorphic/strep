"""Embed a local glTF and its buffers/images without changing rig or geometry."""
import argparse
import copy
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit
from gltf_tools import write_glb
from rig_asset import read_asset
from strep import sha256,save


def pack(source,output,resource_overrides=None):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Output already exists; preserve previous assets')
    original=json.loads(source.read_text(encoding='utf-8-sig'));document=copy.deepcopy(original)
    if document.get('asset',{}).get('version')!='2.0':raise ValueError('glTF 2.0 required')
    records={source.name:sha256(source)};overrides=resource_overrides or {};used_overrides={}
    def resource(uri):
        if not isinstance(uri,str):raise ValueError('External local URI required')
        original_uri=uri
        uri=overrides.get(uri,uri)
        if uri!=original_uri:used_overrides[original_uri]=uri
        parsed=urlsplit(uri)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or '\\' in uri:
            raise ValueError('Only relative local resource paths supported')
        path=(source.parent/unquote(parsed.path)).resolve()
        if not path.is_relative_to(source.parent) or not path.is_file():
            raise ValueError('Resource escapes source folder or is missing')
        records[path.relative_to(source.parent).as_posix()]=sha256(path)
        return path.read_bytes()
    binary=bytearray();starts=[];buffers=[]
    def append(data):
        while len(binary)%4:binary.append(0)
        start=len(binary);binary.extend(data);return start
    for buffer in document.get('buffers',[]):
        data=resource(buffer.get('uri'))
        if len(data)!=buffer.get('byteLength'):raise ValueError('Buffer length differs from declaration')
        starts.append(append(data));buffers.append(data)
    if not buffers:raise ValueError('At least one buffer required')
    for view in document.get('bufferViews',[]):
        number=view['buffer'];offset=view.get('byteOffset',0);length=view['byteLength']
        if type(number) is not int or not 0<=number<len(buffers) or offset<0 or length<0 or offset+length>len(buffers[number]):
            raise ValueError('Invalid bufferView bounds')
        view.update(buffer=0,byteOffset=starts[number]+offset)
    images=[]
    for image in document.get('images',[]):
        if 'uri' not in image:continue
        if 'bufferView' in image:raise ValueError('Image combines URI and bufferView')
        data=resource(image.pop('uri'))
        mime='image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else None
        if mime is None or image.get('mimeType',mime)!=mime:raise ValueError('Only consistent PNG/JPEG images supported')
        offset=append(data);image.update(bufferView=len(document.setdefault('bufferViews',[])),mimeType=mime)
        document['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=len(data)))
        images.append((image['bufferView'],data))
    if set(overrides)!=set(used_overrides):raise ValueError('Unused resource override')
    document['buffers']=[dict(byteLength=len(binary))]
    output.parent.mkdir(parents=True,exist_ok=True)
    write_glb(output,document,binary)
    decoded,blob=read_asset(output)
    # Compare every original bufferView byte; all attributes, inverse binds and
    # animation data remain untouched, including representations not evaluated here.
    for before,after in zip(original.get('bufferViews',[]),decoded.get('bufferViews',[])):
        start=before.get('byteOffset',0);data=buffers[before['buffer']][start:start+before['byteLength']]
        offset=after['byteOffset']
        if blob[offset:offset+after['byteLength']]!=data:raise ValueError('Packed bufferView changed')
    for number,data in images:
        view=decoded['bufferViews'][number];start=view['byteOffset']
        if blob[start:start+view['byteLength']]!=data:raise ValueError('Packed image changed')
    for key in ('nodes','skins','meshes','animations','materials','textures','accessors','scenes','scene'):
        if decoded.get(key)!=original.get(key):raise ValueError('Packing changed '+key)
    report=dict(source=str(source),source_sha256=sha256(source),resources=records,glb_sha256=sha256(output),
        buffer_views_verified=len(original.get('bufferViews',[])),images_embedded=len(images),resource_overrides=used_overrides,
        implementation_sha256=sha256(__file__),scope='Container packing only; rig, mesh, skin, material and animation definitions/data unchanged.')
    save(output.with_suffix('.packing.json'),report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(pack(args.source,args.output))
