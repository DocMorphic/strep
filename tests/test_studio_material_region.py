"""Actual tiny animated GLB -> complete picked triangles -> portable bundle."""
import copy
import hashlib
import json
import io
import shutil
import sys
import threading
import subprocess
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_rig_material_patch import fixture,unsigned
from gltf_tools import write_glb
from rig_asset import RigAsset
from strep import read,save,sha256
from material_patch_bundle import verify
import studio_material_region as regions
import studio_material_patch as loader
import action_studio_server as server
import action_worker_lock


def setup(tmp_path,monkeypatch):
    a,b=fixture(tmp_path/'reports/rig-jobs/fixture',animated=True)
    rig=RigAsset.load(a);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    doc['meshes'][0]['primitives'][0]['indices']=unsigned(doc,binary,np.asarray([[0,1,2],[0,2,3]]).reshape(-1),'SCALAR')
    write_glb(a,doc,binary);profile=read(b);profile['character_sha256']=sha256(a);save(b,profile)
    monkeypatch.setattr(regions,'ROOT',tmp_path);monkeypatch.setattr(loader,'ROOT',tmp_path)
    (tmp_path/'scripts').mkdir()
    for name in set(regions.METHODS+loader.METHODS):shutil.copyfile(Path(regions.__file__).parent/name,tmp_path/'scripts'/name)
    text=b.read_text(encoding='utf8');url='/files/rig-jobs/fixture/transfer/character.glb'
    p=dict(schema=regions.SCHEMA,actor=dict(glb=url,sha256=sha256(a)),profile_json=text,
        profile_sha256=hashlib.sha256(text.encode()).hexdigest(),patch_id='picked-left',role='LeftHand',
        vertices=[[6,0,2],[6,0,0],[6,0,1]],selector=dict(include_children=True,minimum_weight=1.,
        minimum_twice_area_m2=1e-12,maximum_faces=512,maximum_vertices=256))
    return p,lambda u:a if u==url else None,a


def save_preview(p,resolver):
    result=regions.preview(p,resolver,'preview')
    return result,dict(schema=regions.SCHEMA,id=result['id'],preview_sha256=result['result_sha256'])


def test_end_to_end_bundle_load_preserves_animation_and_explicit_point_order(tmp_path,monkeypatch):
    p,resolver,a=setup(tmp_path,monkeypatch);before=sha256(a)
    preview,request=save_preview(p,resolver)
    assert preview['request']==p and preview['patch']['face_references']==[[6,0,0]]
    assert preview['patch']['vertices']==[[6,0,0],[6,0,1],[6,0,2]]
    saved=regions.save_region(request,resolver,'saved')
    folder=regions.folder_for('saved','material-region-bundles')
    assert verify(folder,expected_result_sha256=saved['result_sha256'])['status']=='complete'
    assert sha256(folder/'input/character.glb')==sha256(a)==before
    assert (folder/'input/rig-profile.json').read_bytes()==p['profile_json'].encode()
    loaded=loader.load(dict(schema=loader.SCHEMA,actor=p['actor'],bundle=saved['bundle'],result_sha256=saved['result_sha256'],
                           patch_id=saved['patch_id'],vertex_indices=[2,0,1],reduction='individual'),resolver)
    assert loaded['patch']['vertices']==p['vertices'] and saved['faces']==1 and saved['vertices']==3
    assert saved['explicit_triangle_selection'] and saved['anatomical_review_pending']
    assert not any(saved[k] for k in ('animation_edited','motion_contacts_measured','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'))


@pytest.mark.parametrize('fault',['schema','extra','profile-text','profile-hash','profile-size','profile-array','patch-id','role',
    'empty','duplicate','boolean','unknown-vertex','partial','dangling','ownership','disconnected','degenerate',
    'child-boolean','weight-boolean','weight-high','face-budget','vertex-budget','character','remote'])
def test_bad_or_incomplete_selections_reject_and_never_save_bundle(tmp_path,monkeypatch,fault):
    p,resolver,a=setup(tmp_path,monkeypatch)
    if fault=='schema':p['schema']='other'
    elif fault=='extra':p['automatic_palm']=True
    elif fault=='profile-text':p['profile_json']='invalid'
    elif fault=='profile-hash':p['profile_sha256']='0'*64
    elif fault=='profile-size':p['profile_json']=' '*131073
    elif fault=='profile-array':p['profile_json']='[]';p['profile_sha256']=hashlib.sha256(b'[]').hexdigest()
    elif fault=='patch-id':p['patch_id']='../outside'
    elif fault=='role':p['role']='Unknown'
    elif fault=='empty':p['vertices']=[]
    elif fault=='duplicate':p['vertices']=[[6,0,0]]*3
    elif fault=='boolean':p['vertices'][0][0]=True
    elif fault=='unknown-vertex':p['vertices'][0]=[99,0,0]
    elif fault=='partial':p['vertices']=[[6,0,0],[6,0,1],[6,0,3]]
    elif fault=='dangling':p['vertices'].append([6,1,0])
    elif fault=='ownership':p['role']='RightHand'
    elif fault=='disconnected':p['vertices'] += [[7,0,i] for i in range(3)]
    elif fault=='degenerate':
        rig=RigAsset.load(a);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
        doc['meshes'][0]['primitives'][0]['indices']=unsigned(doc,binary,[0,1,2,0,0,1],'SCALAR')
        write_glb(a,doc,binary);p['actor']['sha256']=sha256(a)
        v=json.loads(p['profile_json']);v['character_sha256']=p['actor']['sha256'];p['profile_json']=json.dumps(v)
        p['profile_sha256']=hashlib.sha256(p['profile_json'].encode()).hexdigest()
    elif fault=='child-boolean':p['selector']['include_children']=1
    elif fault=='weight-boolean':p['selector']['minimum_weight']=True
    elif fault=='weight-high':p['selector']['minimum_weight']=1.01
    elif fault=='face-budget':p['selector']['maximum_faces']=513
    elif fault=='vertex-budget':p['selector']['maximum_vertices']=257
    elif fault=='character':a.write_bytes(a.read_bytes()+b'x')
    else:p['actor']['glb']='https://example.test/character.glb'
    with pytest.raises((ValueError,OSError)):regions.preview(p,resolver,'bad')
    folder=regions.folder_for('bad')
    if folder.exists():
        assert read(folder/'pipeline.json')['status']=='failed'
        assert not (folder/'result.json').exists()
    assert not regions.folder_for('bad','material-region-bundles').exists()


@pytest.mark.parametrize('fault',['binding','patch','selection','request','input','method','extra-file','source','approval'])
def test_reviewed_save_rejects_changed_preview_before_bundle_creation(tmp_path,monkeypatch,fault):
    p,resolver,a=setup(tmp_path,monkeypatch);preview,request=save_preview(p,resolver);folder=regions.folder_for('preview')
    if fault=='binding':request['preview_sha256']='0'*64
    elif fault=='patch':save(folder/'patch.json',{})
    elif fault=='selection':save(folder/'selection.json',{})
    elif fault=='request':v=read(folder/'request.json');v['role']='RightHand';save(folder/'request.json',v)
    elif fault=='input':(folder/'input/rig-profile.json').write_bytes(b'{}')
    elif fault=='method':(tmp_path/'scripts/studio_material_region.py').write_bytes(b'changed')
    elif fault=='extra-file':(folder/'unreviewed.json').write_bytes(b'{}')
    elif fault=='source':a.write_bytes(a.read_bytes()+b'x')
    else:
        v=read(folder/'result.json');v['quality_approved']=True;save(folder/'result.json',v);request['preview_sha256']=sha256(folder/'result.json')
    with pytest.raises((ValueError,OSError)):regions.save_region(request,resolver,'rejected')
    assert not regions.folder_for('rejected','material-region-bundles').exists()


def test_fresh_paths_and_safe_names_are_required(tmp_path,monkeypatch):
    p,resolver,_=setup(tmp_path,monkeypatch);_,request=save_preview(p,resolver)
    with pytest.raises(ValueError,match='Fresh'):regions.preview(p,resolver,'preview')
    regions.save_region(request,resolver,'saved')
    with pytest.raises(ValueError,match='Fresh'):regions.save_region(request,resolver,'saved')
    for bad in ('../escape','',True,'a/b'):
        with pytest.raises(ValueError):regions.folder_for(bad)


def test_actual_python_receipts_pass_browser_contract(tmp_path,monkeypatch):
    p,resolver,_=setup(tmp_path,monkeypatch);preview,request=save_preview(p,resolver)
    saved=regions.save_region(request,resolver,'saved')
    payload=tmp_path/'receipts.json';save(payload,dict(preview=preview,saved=saved,request=p))
    module=(Path(regions.__file__).parent/'material-region-author.mjs').as_uri()
    code="import {readFileSync} from 'node:fs'; import {checkedAuthorPreview,checkedAuthorSave} from "+json.dumps(module)+"; const v=JSON.parse(readFileSync(process.argv[1],'utf8')); checkedAuthorSave(v.saved,checkedAuthorPreview(v.preview,v.request));"
    result=subprocess.run(['node','--input-type=module','-e',code,str(payload)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('fault,status',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('valid',201)])
def test_memory_handler_snapshot_gates_without_listener(tmp_path,monkeypatch,fault,status):
    p,resolver,_=setup(tmp_path,monkeypatch);monkeypatch.setattr(server,'allowed_file',resolver)
    h=server.Handler.__new__(server.Handler);h.path='/api/native-scene-material-region-preview';data=json.dumps(p).encode()
    h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(data))}
    h.rfile=io.BytesIO(data);h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},job_lock=threading.Lock())
    responses=[];h.respond=lambda s,v:responses.append((s,v));calls=[]
    @contextmanager
    def lock():
        calls.append('lock')
        if fault=='busy':raise RuntimeError('busy')
        yield
    monkeypatch.setattr(action_worker_lock,'worker_lock',lock)
    if fault=='host':h.headers['Host']='remote'
    elif fault=='origin':h.headers['Origin']='http://remote'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    h.do_POST();assert responses[0][0]==status
    assert calls==(['lock'] if fault in ('busy','valid') else [])
    if fault=='valid':
        preview=responses[0][1];body=dict(schema=regions.SCHEMA,id=preview['id'],preview_sha256=preview['result_sha256'])
        data=json.dumps(body).encode();h.path='/api/native-scene-material-region-save';h.rfile=io.BytesIO(data);h.headers['Content-Length']=str(len(data))
        h.do_POST();assert responses[-1][0]==201 and responses[-1][1]['vertices']==3
