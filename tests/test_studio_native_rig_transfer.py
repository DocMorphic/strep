"""Generated characters, offline HTTP stubs, and explicit engine doubles."""
import copy
from pathlib import Path
import shutil
import sys
import zipfile
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_rig_transfer as studio
import studio_characters as chars
import action_studio_server as server
import audit_native_rig_transfer as engine
from native_engine_clock import clock_wire
from native_godot_payload import payload as native_payload
from rig_asset import RigAsset,array
from gltf_tools import write_glb,append_accessor
from test_native_rig_transfer import pair
from test_native_scene_engine import mock_actor,serialized
from test_studio_native_scene import handler
from strep import save,read,sha256


def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(server,'ROOT',tmp_path)
    # Keep hashed profile paths below Windows' legacy 260-character limit in
    # pytest's long per-test directory; production keeps its existing store.
    monkeypatch.setattr(chars,'ASSETS',tmp_path/'c')
    import action_worker_lock
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    a,ap,b,bp=pair(tmp_path/'fixtures');source=RigAsset.load(a);doc=copy.deepcopy(source.document);binary=bytearray(source.binary)
    for sampler in doc['animations'][0]['samplers']:sampler['input']=append_accessor(doc,binary,array(doc,binary,sampler['input'])*.1,'SCALAR')
    write_glb(a,doc,binary);p=read(ap);p['character_sha256']=sha256(a);save(ap,p)
    request=dict(animation_index=0,rate=120)
    for side,glb,profile in [('source',a,ap),('target',b,bp)]:
        metadata=chars.import_bytes(glb.read_bytes(),side+'.glb');saved=chars.save_profile(dict(asset_id=metadata['id'],profile=read(profile)))
        request.update({side+'_asset_id':metadata['id'],side+'_profile_id':saved['profile_id']})
    return request


def engine_double(transfer,output):
    folder,report,source,target,tp,prepared,keys,rig,index,root=engine.bound_candidate(transfer)
    output=Path(output);output.mkdir();files=('report.json','character.glb','target-transforms.npz')+tuple(report['input_snapshots_sha256'])
    for n in files:shutil.copyfile(folder/n,output/n)
    resource=output/'animation.res';resource.write_bytes(b'Explicit saved-resource double; never engine evidence')
    times=np.sort(np.concatenate([keys.astype(float)]+[keys[:-1].astype(float)+f*np.diff(keys.astype(float)) for f in (.25,.5,.75)]))
    placement=np.eye(4);placement[:3,:3]=Rotation.from_euler('yxz',[-37,9,13],degrees=True).as_matrix();placement[:3,3]=[2.,-.3,1.]
    sampler=engine.NativeSupportSampler(rig.document,rig.binary,index);actual=mock_actor(rig,sampler,times)
    native=native_payload(rig,sampler,'');actual['channels']=[dict(path='Skeleton:'+c['bone'],type={'translation':1,'rotation':2,'scale':3}[c['path']],times_s=c['times_s'],values=c['values']) for c in native['channels']]
    anchor=sampler.sample(0.)[root];poses=placement@np.array([sampler.sample(t)[rig.joints] for t in times])
    transforms=np.array([sampler.sample(t)[root]@np.linalg.inv(anchor) for t in times]);deltas=np.concatenate([np.eye(4)[None],np.linalg.inv(transforms[:-1])@transforms[1:]])
    names=[rig.document['nodes'][n]['name'] for n in rig.joints];order=[names.index(n) for n in actual['bone_names']]
    for mode in ('embedded','extracted'):
        actual[mode]=[dict(time_s=float(t),bones=[serialized(v) for v in poses[i,order]],root_motion=serialized(transforms[i]),
            actor_world=serialized(placement@transforms[i] if mode=='extracted' else placement),root_delta=serialized(deltas[i]),
            root_in_actor=serialized(anchor if mode=='extracted' else sampler.sample(t)[root])) for i,t in enumerate(times)]
    actual['preview']=[copy.deepcopy(actual['extracted'][i]) for i in (0,len(times)-1,len(times)//2,0)]
    actual.update(invalid_rejected=True,malformed_bindings_rejected=True,malformed_bindings=10,engine=dict(string='explicit engine double'))
    save(output/'runtime-engine.json',actual);save(output/'runtime-request.json',dict(glb=str(output/'character.glb'),animation_resource=str(resource),
        animation_index=index,root_bone=rig.document['nodes'][root]['name'],clock=clock_wire(times),placement=placement.tolist()))
    result,arrays=engine.runtime.evaluate(rig,sampler,times,placement,actual);np.savez_compressed(output/'observations.npz',**arrays)
    result.update(schema='strep-native-rig-transfer-engine-v1',input_sha256={n:sha256(folder/n) for n in files},animation_resource_sha256=sha256(resource),
        implementation_sha256={n:sha256(engine.ROOT/'scripts'/n) for n in engine.METHODS},raw_engine_sha256=sha256(output/'runtime-engine.json'),observations_sha256=sha256(output/'observations.npz'),
        source_bytes_unchanged=True,original_selected=True,quality_approved=False,contact_verified=False,physics_verified=False,release_approved=False)
    save(output/'result.json',result)
    for n in ('prepare','runtime'):save(output/(n+'.log.terminal.json'),dict(pid=-1,exit_code=0,owned_tree_stopped=True))
    return result


def complete(tmp_path,monkeypatch):
    request=setup(tmp_path,monkeypatch);folder=studio.folder_for('job');studio.prepare(request,folder)
    monkeypatch.setattr(engine,'run',engine_double);studio.run(folder)
    return folder,request


def test_complete_native_clock_preserved_and_explicit_import_rebinds_profile(tmp_path,monkeypatch):
    folder,request=complete(tmp_path,monkeypatch)
    inputs={p:sha256(p) for side in ('source','target') for p in chars.asset_folder(request[side+'_asset_id']).rglob('*') if p.is_file()}
    m=studio.manifest('job');assert len(m['downloads'])==8 and m['sampled_runtime_conditions_pass'] and not m['contact_verified']
    assert m['output_animation_index']==1 and m['previews'][1]['animation_count']==2 and m['previews'][0]['animation_index']==0
    assert len(chars.list_assets())==2
    imported=studio.import_candidate(dict(job='job',result_sha256=m['result_sha256']))
    assert len(chars.list_assets())==3 and imported['asset_id']==sha256(folder/'transfer/character.glb')
    profile=read(chars.profile_path(imported['asset_id'],imported['profile_id']))
    assert profile==read(folder/'edit-profile.json') and not profile['axis_alignment_xyzw'] and profile['world_offset_m']==[0,0,0]
    assert all(sha256(p)==h for p,h in inputs.items())
    assert studio.served_file('native-transfer-jobs/job/input/source.glb') is None
    with pytest.raises(ValueError,match='Fresh'):studio.run(folder)


@pytest.mark.parametrize('fault',['extra','missing','same','boolean-index','boolean-rate','rate','hash','profile-hash','saved-profile'])
def test_bad_or_stale_request_rejects_before_job(tmp_path,monkeypatch,fault):
    request=setup(tmp_path,monkeypatch)
    if fault=='extra':request['contacts']=True
    elif fault=='missing':request.pop('source_profile_id')
    elif fault=='same':request.update(target_asset_id=request['source_asset_id'],target_profile_id=request['source_profile_id'])
    elif fault=='boolean-index':request['animation_index']=False
    elif fault=='boolean-rate':request['rate']=True
    elif fault=='rate':request['rate']=30
    elif fault=='hash':request['source_asset_id']='0'*64
    elif fault=='profile-hash':request['target_profile_id']='0'*64
    else:save(chars.asset_folder(request['target_asset_id'])/'active-profile.json',dict(id='0'*64))
    folder=studio.folder_for('bad')
    with pytest.raises((ValueError,OSError)):studio.prepare(request,folder)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['snapshot','request','method','original'])
def test_prepared_drift_keeps_failed_state(tmp_path,monkeypatch,fault):
    request=setup(tmp_path,monkeypatch);folder=studio.folder_for('bad');studio.prepare(request,folder)
    p={'snapshot':folder/'input/source.glb','request':folder/'request.json','method':folder/'implementation/studio_native_rig_transfer.py',
        'original':chars.asset_folder(request['target_asset_id'])/'character.glb'}[fault]
    p.write_bytes(p.read_bytes()+b' changed')
    with pytest.raises((ValueError,OSError)):studio.run(folder)
    assert studio.manifest('bad')['downloads']==[] and read(folder/'pipeline.json')['status']=='failed'


@pytest.mark.parametrize('fault',['recipe','clock','observation','edit-profile','quality','zip'])
def test_rehashed_completed_payloads_reject(tmp_path,monkeypatch,fault):
    folder,_=complete(tmp_path,monkeypatch)
    if fault=='recipe':p=folder/'result.json';v=read(p);v['request']['animation_index']=1;save(p,v)
    elif fault=='clock':p=folder/'audit/runtime-request.json';v=read(p);v['animation_index']=0;save(p,v)
    elif fault=='observation':p=folder/'audit/runtime-engine.json';v=read(p);v['extracted'][0]['bones'][0][3][0]+=.01;save(p,v)
    elif fault=='edit-profile':p=folder/'edit-profile.json';v=read(p);v['world_offset_m']=[1,0,0];save(p,v)
    elif fault=='quality':p=folder/'audit/result.json';v=read(p);v['quality_approved']=True;save(p,v)
    else:(folder/'candidate.zip').write_bytes(b'Invalid ZIP')
    r=read(folder/'result.json');r['files_sha256']={n:sha256(folder/n) for n in r['files_sha256']};r['artifacts_sha256']={n:sha256(folder/n) for n in r['artifacts_sha256']};save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
    with pytest.raises((ValueError,zipfile.BadZipFile)):studio.manifest('job')
    assert studio.served_file('native-transfer-jobs/job/transfer/character.glb') is None


def test_offline_routes_modules_and_build(tmp_path,monkeypatch):
    request=setup(tmp_path,monkeypatch)
    for url in ('/api/native-transfer-jobs','/api/native-transfer-character?id='+request['source_asset_id']):
        h=handler({},url);h.do_GET();assert h.responses[-1][0]==200
    h=handler({},'/api/native-transfer-review?id=a&id=b');h.do_GET();assert h.responses[-1][0]==400
    for file in ('native-transfer-editor.mjs','native-transfer-viewer.mjs','native-transfer-viewer.html','native-preview-policy.mjs'):
        assert server.allowed_file('/'+file)==tmp_path/'scripts'/file
    from build_desktop import render
    page=render();assert page.count('id="nativeTransferPanel"')==1 and '__NATIVE_TRANSFER_EDITOR__' not in page and 'createNativeTransferEditor({api,post,onImported:' in page


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409),('valid',202)])
def test_offline_post_gates_and_worker(tmp_path,monkeypatch,fault,expected):
    request=setup(tmp_path,monkeypatch);h=handler(request,'/api/native-transfer-assets');calls=[]
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(server.subprocess,'Popen',lambda argv,**kw:calls.append((argv,kw)) or SimpleNamespace(poll=lambda:None))
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:assert Path(calls[0][0][1]).name=='studio_native_rig_transfer.py' and calls[0][1]['env']['HF_HUB_OFFLINE']=='1'


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('busy',409),('worker',409),('invalid',400),('valid',201)])
def test_offline_import_route_gates_before_library_mutation(tmp_path,monkeypatch,fault,expected):
    setup(tmp_path,monkeypatch);calls=[]
    payload=dict(job='job',result_sha256='a'*64)
    h=handler(payload,'/api/native-transfer-import')
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy')
    monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    def imported(p):
        if fault=='invalid':raise ValueError('Completed candidate required')
        calls.append(p);return dict(asset_id='b'*64,profile_id='c'*64,quality_approved=False)
    monkeypatch.setattr(studio,'import_candidate',imported)
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==expected
    assert calls==([payload] if fault=='valid' else []) and len(chars.list_assets())==2


def test_worker_identity_rejects_foreign_process_before_transfer(tmp_path,monkeypatch):
    request=setup(tmp_path,monkeypatch);folder=studio.folder_for('foreign');studio.prepare(request,folder)
    save(folder/'worker.json',dict(pid=-1,created_at=0.))
    with pytest.raises(ValueError,match='another process'):studio.run(folder)
    assert not (folder/'transfer').exists()


def test_character_metadata_requires_saved_mapping_and_reports_source_corrections(tmp_path,monkeypatch):
    request=setup(tmp_path,monkeypatch);asset=request['source_asset_id']
    meta=studio.character_metadata(asset);assert meta['source_profile_ready'] and meta['clips'][0]['supported']
    profile=read(chars.profile_path(asset,request['source_profile_id']));profile['world_offset_m']=[.1,0,0]
    chars.save_profile(dict(asset_id=asset,profile=profile))
    assert not studio.character_metadata(asset)['source_profile_ready']
    (chars.asset_folder(asset)/'active-profile.json').unlink()
    with pytest.raises(ValueError,match='Save this character mapping'):studio.character_metadata(asset)
