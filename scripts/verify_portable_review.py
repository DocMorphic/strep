"""Verify a relocated reviewer packet against original motion and its sealed ZIP."""
import argparse
import hashlib
from pathlib import Path
import urllib.request
from urllib.parse import quote
import zipfile
from strep import read,save,sha256,now
from gltf_tools import read_glb
from review_session import scrub


def verify(packet,key_path,archive,base_url,output):
    packet=Path(packet).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(packet):raise ValueError('Write new organizer evidence outside immutable packet')
    manifest=read(packet/'manifest.json');key=read(key_path);inventory=read(packet/'package-integrity.json')['files']
    assert key['packet_id']==manifest['packet_id'] and key['manifest_sha256']==sha256(packet/'manifest.json')
    actual={p.relative_to(packet).as_posix() for p in packet.rglob('*') if p.is_file()}
    assert actual==set(inventory)|{'package-integrity.json'}
    for name,digest in inventory.items():
        path=(packet/name).resolve()
        assert path.is_relative_to(packet) and sha256(path)==digest
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==actual and len(z.namelist())==len(actual) and z.testzip() is None
        for name in actual:
            assert hashlib.sha256(z.read(name)).hexdigest()==sha256(packet/name)
    by={c['id']:c for c in key['cases']};assert len(by)==len(manifest['cases'])==len(key['cases'])
    checked=[]
    for case in manifest['cases']:
        mapping=by[case['id']];source=Path(mapping['source']);path=packet/case['path']
        assert sha256(source)==mapping['source_sha256']
        assert sha256(path)==mapping['review_sha256']==case['sha256']
        doc,binary=read_glb(source);expected=scrub(doc)
        for a in expected.get('animations',[]):a['name']='Motion'
        for s in expected.get('scenes',[]):s['name']='Character'
        actual_doc,actual_binary=read_glb(path)
        assert actual_doc==expected and actual_binary==binary
        with urllib.request.urlopen(base_url.rstrip('/')+'/'+quote(case['path']),timeout=30) as response:
            assert hashlib.sha256(response.read()).hexdigest()==case['sha256']
        checked.append(case['id'])
    modules=['viewer.html','manifest.json','runtime/three/build/three.module.js','runtime/three/build/three.core.js',
             'runtime/three/examples/jsm/loaders/GLTFLoader.js','runtime/three/examples/jsm/controls/OrbitControls.js',
             'runtime/soma-preview-skin.js']
    for name in modules:
        with urllib.request.urlopen(base_url.rstrip('/')+'/'+name,timeout=30) as response:
            assert hashlib.sha256(response.read()).hexdigest()==inventory[name]
    result=dict(at=now(),packet_id=manifest['packet_id'],archive_sha256=sha256(archive),files_verified=len(inventory),
                archive_members_match=True,source_motion_payloads_unchanged=len(checked),http_clips_verified=len(checked),
                http_runtime_files_verified=len(modules),relocated_packet=str(packet),human_reviews_collected=0,
                quality_approved=False,scope='Artifact/transport verification only; no real reviewer scores or cleanup evidence.')
    save(output,result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('packet',type=Path);p.add_argument('key',type=Path)
    p.add_argument('archive',type=Path);p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(verify(a.packet,a.key,a.archive,a.url,a.output))
