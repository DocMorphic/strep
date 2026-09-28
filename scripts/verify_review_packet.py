"""Verify neutral review copies against their organizer key, without human ratings."""
import argparse,hashlib,urllib.request
from pathlib import Path
from strep import read,save,sha256,now,ROOT
from gltf_tools import read_glb
from review_session import scrub

def verify(packet,key_path):
    packet=Path(packet).resolve();key=read(key_path);manifest=read(packet/'manifest.json')
    assert key['packet_id']==manifest['packet_id'] and key['manifest_sha256']==sha256(packet/'manifest.json')
    by={c['id']:c for c in key['cases']};assert len(by)==len(manifest['cases'])==len(key['cases'])
    rows=[]
    for case in manifest['cases']:
        source=by[case['id']];path=packet/case['path'];original=Path(source['source'])
        assert sha256(original)==source['source_sha256'] and sha256(path)==source['review_sha256']==case['sha256']
        doc,binary=read_glb(original);expected=scrub(doc)
        for a in expected.get('animations',[]):a['name']='Motion'
        for s in expected.get('scenes',[]):s['name']='Character'
        actual,payload=read_glb(path);assert actual==expected and payload==binary
        url='http://127.0.0.1:8767/'+path.relative_to(ROOT).as_posix()
        with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
        assert hashlib.sha256(data).hexdigest()==case['sha256']
        rows.append(dict(id=case['id'],review_sha256=case['sha256'],motion_payload_unchanged=True,http_bytes_match=True))
    result=dict(created_at=now(),checks_passed=True,cases=rows,human_reviews_collected=0,quality_approved=False,
        scope='Review copies remove extras and replace animation/scene labels only. Entire remaining glTF document and binary payload equal source. No reviewer scores or cleanup evidence created.')
    save(packet/'copy-verification.json',result);print(dict(verified=len(rows),quality_approved=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('packet',type=Path);p.add_argument('key',type=Path);a=p.parse_args();verify(a.packet,a.key)
