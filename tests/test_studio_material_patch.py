"""Tiny portable-region imports; no HTTP listener, animation worker or engine."""
import copy
import io
import json
from pathlib import Path
import sys
import shutil
import threading
from types import SimpleNamespace
from contextlib import contextmanager
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_material_patch_bundle import author, target_from, move
from strep import read, sha256
import studio_material_patch as studio
import action_studio_server as server
import action_worker_lock


def setup(tmp_path, monkeypatch):
    root=tmp_path/'reports'; root.mkdir()
    a,b,_,parent,_=author(root)
    target,profile=target_from(a,b,root/'animated')
    folder=root/'regions'; move(parent,target,profile,folder)
    monkeypatch.setattr(studio, 'ROOT', tmp_path)
    # Actual method bytes stay rooted in the unchanged project scripts.
    (tmp_path/'scripts').mkdir()
    for name in studio.METHODS:
        shutil.copyfile(Path(studio.__file__).parent/name,tmp_path/'scripts'/name)
    url='/files/rig-jobs/test/transfer/character.glb'
    payload=dict(schema=studio.SCHEMA,actor=dict(glb=url,sha256=sha256(target)),bundle='regions',
                 result_sha256=sha256(folder/'result.json'),patch_id='left-surface',
                 vertex_indices=[2,0,1],reduction='individual')
    return payload,lambda value:target if value==url else None,folder,target


def test_real_transferred_bundle_and_explicit_order_are_preserved(tmp_path,monkeypatch):
    p,resolver,folder,target=setup(tmp_path,monkeypatch); before=copy.deepcopy(p)
    result=studio.load(p,resolver); patch=read(folder/'patches/left-surface.json')
    assert p==before and result['request']==p
    assert result['patch']['vertices']==[patch['vertices'][i] for i in [2,0,1]]
    assert result['binding']['source']==patch['source']
    assert result['patch']['glb_sha256']==sha256(target)
    assert result['explicit_vertex_correspondence'] and result['anatomical_review_pending']
    assert not any(result[k] for k in ('animation_edited','motion_contacts_measured','engine_executed',
                                     'human_reviewed','quality_approved','training_admitted','release_approved'))
    p['reduction']='centroid'; assert studio.load(p,resolver)['patch']['reduction']=='centroid'


@pytest.mark.parametrize('fault',['schema','extra','actor-extra','hash','result-hash','bundle-absolute',
    'bundle-traversal','bundle-empty','bundle-backslash','patch','empty','bool','duplicate','negative',
    'out-of-range','too-many','automatic','remote','query','unserved','changed-actor','changed-patch','wrong-clip'])
def test_rejects_invalid_bindings_without_writes(tmp_path,monkeypatch,fault):
    p,resolver,folder,target=setup(tmp_path,monkeypatch)
    if fault=='schema': p['schema']='other'
    elif fault=='extra': p['quality_approved']=True
    elif fault=='actor-extra': p['actor']['auto']=True
    elif fault=='hash': p['actor']['sha256']='0'*64
    elif fault=='result-hash': p['result_sha256']='0'*64
    elif fault=='bundle-absolute': p['bundle']=str(folder)
    elif fault=='bundle-traversal': p['bundle']='../regions'
    elif fault=='bundle-empty': p['bundle']=''
    elif fault=='bundle-backslash': p['bundle']='a\\regions'
    elif fault=='patch': p['patch_id']='missing'
    elif fault=='empty': p['vertex_indices']=[]
    elif fault=='bool': p['vertex_indices']=[True]
    elif fault=='duplicate': p['vertex_indices']=[0,0]
    elif fault=='negative': p['vertex_indices']=[-1]
    elif fault=='out-of-range': p['vertex_indices']=[3]
    elif fault=='too-many': p['vertex_indices']=list(range(257))
    elif fault=='automatic': p['reduction']='automatic'
    elif fault=='remote': p['actor']['glb']='https://example.test/a.glb'
    elif fault=='query': p['actor']['glb']+='?x=1'
    elif fault=='unserved': resolver=lambda _:None
    elif fault=='changed-actor': target.write_bytes(target.read_bytes()+b'x')
    elif fault=='changed-patch': (folder/'patches/left-surface.json').write_text('{}')
    else:
        original=folder.parent/'authored/input/character.glb'
        p['actor']['sha256']=sha256(original); resolver=lambda _:original
    before={str(f):sha256(f) for f in folder.parent.rglob('*') if f.is_file()}
    with pytest.raises((ValueError,OSError)): studio.load(p,resolver)
    assert before=={str(f):sha256(f) for f in folder.parent.rglob('*') if f.is_file()}


def test_source_mutation_during_verify_rejects(tmp_path,monkeypatch):
    p,resolver,folder,target=setup(tmp_path,monkeypatch); real=studio.verify
    def mutate(*args,**kwargs):
        result=real(*args,**kwargs); target.write_bytes(target.read_bytes()+b'x'); return result
    monkeypatch.setattr(studio,'verify',mutate)
    with pytest.raises(ValueError,match='changed'):studio.load(p,resolver)


def test_complete_file_budget_rejects_before_verifier(tmp_path,monkeypatch):
    p,resolver,folder,_=setup(tmp_path,monkeypatch)
    for i in range(513): (folder/str(i)).write_bytes(b'')
    monkeypatch.setattr(studio,'verify',lambda *a,**k:pytest.fail('Budget must reject before verification'))
    with pytest.raises(ValueError,match='budget'):studio.load(p,resolver)


def handler(payload):
    h=server.Handler.__new__(server.Handler); h.path='/api/native-scene-material-patch'
    data=json.dumps(payload).encode(); h.rfile=io.BytesIO(data)
    h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(data))}
    h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},job_lock=threading.Lock())
    h.responses=[]; h.respond=lambda status,value:h.responses.append((status,value)); return h


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('valid',200)])
def test_memory_handler_gates_and_exclusive_lock(tmp_path,monkeypatch,fault,expected):
    p,resolver,_,_=setup(tmp_path,monkeypatch); monkeypatch.setattr(server,'allowed_file',resolver)
    h=handler(p); entries=[]
    @contextmanager
    def lock():
        entries.append('lock')
        if fault=='busy': raise RuntimeError('Production worker busy')
        yield
    monkeypatch.setattr(action_worker_lock,'worker_lock',lock)
    if fault=='host': h.headers['Host']='remote.test'
    elif fault=='origin':h.headers['Origin']='http://remote.test'
    elif fault=='type': h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    h.do_POST(); assert h.responses[0][0]==expected
    assert entries==(['lock'] if fault in ('busy','valid') else [])
