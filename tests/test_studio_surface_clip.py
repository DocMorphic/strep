"""Adapter/transport fixtures; no socket, production asset or realism approval."""
import copy
import io
import json
from pathlib import Path
import sys
import threading
import uuid
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_surface_clip_jobs as jobs
import studio_surface_clip_routes as routes
from strep import read,save,sha256


def payload():
    return dict(schema='strep-studio-surface-clip-v1',source_job='fixture',variant='input',source_sha256='a'*64,
        root=0,rotations=[1,2,3],angles_degrees=[45.,45.,45.],contacts=[],
        limits=dict(root_horizontal_m=.15,root_vertical_m=.75,floor_depth_m=.005,contact_error_m=.02,root_step_m=.025,rotation_step_degrees=5.),
        end_policy='preserve',acknowledge_changed_end=False,maximum_windows=1,soft_seconds=120)


@pytest.fixture
def store(tmp_path,monkeypatch):
    # Keep nested core/attempt paths below legacy Windows path limits.
    short=Path(__file__).resolve().parents[1]/'.cache'/'sct'/uuid.uuid4().hex[:8]
    short.mkdir(parents=True,exist_ok=False)
    monkeypatch.setattr(jobs,'ROOT',short)
    return short


@pytest.mark.parametrize('fault',['unknown','root','duplicate','angle','nan','contact_ref','contact_time','end_ack','windows','seconds','hash','job'])
def test_invalid_requests_do_not_create_jobs(store,fault):
    p=payload()
    if fault=='unknown':p['extra']=1
    elif fault=='root':p['root']=True
    elif fault=='duplicate':p['rotations']=[1,1,3]
    elif fault=='angle':p['angles_degrees'][0]=0
    elif fault=='nan':p['limits']['floor_depth_m']=float('nan')
    elif fault.startswith('contact'):
        p['contacts']=[dict(vertex=[6,0,0],target_m=[0,0,0],start_time_s=0,end_time_s=1)]
        if fault=='contact_ref':p['contacts'][0]['vertex'][0]=False
        else:p['contacts'][0]['end_time_s']=-1
    elif fault=='end_ack':p['end_policy']='edit'
    elif fault=='windows':p['maximum_windows']=21
    elif fault=='seconds':p['soft_seconds']=121
    elif fault=='hash':p['source_sha256']='x'
    else:p['source_job']='../escape'
    with pytest.raises(ValueError):jobs.prepare(p)
    assert not (store/'reports').exists()


def test_request_binding_stale_ticket_and_implementation(store,monkeypatch):
    folder=jobs.prepare(payload());status=jobs.review(folder.name)
    assert status['can_continue'] and status['status']=='ready'
    with pytest.raises(ValueError,match='progress changed'):jobs.launch(folder,{'bad':'ticket'})
    assert not (folder/'attempts').exists()
    monkeypatch.setattr(jobs,'methods',lambda:{'changed.py':'a'*64})
    with pytest.raises(ValueError,match='Implementation changed'):jobs.launch(folder)
    assert jobs.review(folder.name)['status']=='ready'
    p=read(folder/'request.json');p['root']=1;save(folder/'request.json',p)
    with pytest.raises(ValueError,match='request changed'):jobs.review(folder.name)


def publish_fixture(folder):
    attempt=folder/'attempts'/('b'*32);attempt.mkdir(parents=True)
    save(attempt/'request.json',{})
    save(folder/'active.json',dict(path=attempt.relative_to(folder).as_posix(),sha256=sha256(attempt/'request.json')))
    clip=folder/'original.glb';clip.write_bytes(b'fixture bytes, not a real GLB')
    result=dict(request_sha256=sha256(folder/'request.json'),summary=dict(status='checkpointed'),duration_s=1.,
        original_selected=True,quality_approved=False,release_approved=False,
        files=dict(original=dict(path='original.glb',sha256=sha256(clip),label='Original clip')))
    save(attempt/'result.json',result);save(attempt/'guard/pipeline.json',dict(status='complete'))
    save(attempt/'resource-replay.json',dict(status='complete',all_archived_bindings_match=True,pipeline_sha256=sha256(attempt/'guard/pipeline.json')))
    receipt=dict(result_sha256=sha256(attempt/'result.json'),pipeline_sha256=sha256(attempt/'guard/pipeline.json'),replay_sha256=sha256(attempt/'resource-replay.json'))
    save(attempt/'publication.json',receipt)
    return attempt,result,receipt


def test_verified_download_and_preview_identity(store):
    folder=jobs.prepare(payload());attempt,_,_=publish_fixture(folder)
    status=jobs.review(folder.name);assert status['can_continue'] and status['original_selected']
    url=status['downloads'][0]['url'];assert jobs.served_file(url)==folder/'original.glb'
    descriptor=jobs.descriptor(folder.name,attempt.name)
    assert descriptor['versions'][0]['preview_url']==url and not descriptor['quality_approved']
    (folder/'original.glb').write_bytes(b'changed')
    with pytest.raises(ValueError,match='artifact changed'):jobs.served_file(url)


@pytest.mark.parametrize('fault',['escape','result','pipeline','replay','approval','request'])
def test_publication_rejects_bad_bindings(store,fault):
    folder=jobs.prepare(payload());attempt,result,receipt=publish_fixture(folder)
    if fault=='escape':result['files']['original']['path']='../escape.glb'
    elif fault=='approval':result['quality_approved']=True
    elif fault=='request':result['request_sha256']='0'*64
    elif fault=='pipeline':save(attempt/'guard/pipeline.json',dict(status='failed'))
    elif fault=='replay':
        replay=read(attempt/'resource-replay.json');replay['status']='failed';save(attempt/'resource-replay.json',replay)
        receipt['replay_sha256']=sha256(attempt/'resource-replay.json')
    if fault in ('escape','approval','request','result'):
        result['duration_s']=2.;save(attempt/'result.json',result)
        if fault!='result':receipt['result_sha256']=sha256(attempt/'result.json')
    save(attempt/'publication.json',receipt)
    with pytest.raises(ValueError):jobs.publication(folder,attempt.name)


def handler(body=b'{}',**headers):
    h=SimpleNamespace(path='/api/surface-clip-jobs',headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(body)),**headers},
        server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},job_lock=threading.Lock(),worker=None),rfile=io.BytesIO(body),responses=[])
    h.respond=lambda code,value:h.responses.append((code,value))
    return h


@pytest.mark.parametrize('fault,code',[('host',403),('origin',403),('type',415),('duplicate',400),('nan',400),('chunked',400),('large',400),('busy',409)])
def test_route_rejects_before_prepare(store,monkeypatch,fault,code):
    import action_studio_server as server
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(jobs,'prepare',lambda p:pytest.fail('Rejected request reached storage'))
    h=handler(json.dumps(payload()).encode())
    if fault=='host':h.headers['Host']='example.com'
    elif fault=='origin':h.headers['Origin']='http://example.com'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='chunked':h.headers['Transfer-Encoding']='chunked'
    elif fault=='large':h.headers['Content-Length']=str(1024**2+1)
    elif fault in ('duplicate','nan'):
        body=b'{"a":1,"a":2}' if fault=='duplicate' else b'{"a":NaN}'
        h.rfile=io.BytesIO(body);h.headers['Content-Length']=str(len(body))
    assert routes.dispatch_post(h) and h.responses[0][0]==code


def test_real_handler_dispatches_create_continue_list_and_assets(store,monkeypatch):
    import action_studio_server as server
    monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    launched=[]
    monkeypatch.setattr(jobs,'launch',lambda folder,ticket=None:launched.append((folder,ticket)))
    h=handler(json.dumps(payload()).encode());server.Handler.do_POST(h);assert h.responses[0][0]==202
    folder=launched[0][0];ticket=jobs.review(folder.name)['ticket']
    h=handler(json.dumps(ticket).encode());h.path+=f'/{folder.name}/continue';server.Handler.do_POST(h)
    assert h.responses[0][0]==202 and launched[-1]==(folder,ticket)
    h=handler();server.Handler.do_GET(h);assert h.responses[0][1]['jobs'][0]['id']==folder.name
    for name in ('surface-clip-editor.mjs','surface-clip-viewer.mjs','surface-clip-viewer.html'):
        assert server.allowed_file('/'+name).is_file()


def test_real_adapter_snapshots_exact_mesh_and_runs_core(store,monkeypatch):
    # Resolver is a fixture. Preparation, exported GLB, audit and continuation are real.
    from test_native_support import fixture
    from gltf_tools import append_accessor,write_glb
    import numpy as np
    import studio_native_support
    import surface_clip_job
    path,rig,_,_=fixture(store)
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    clock=append_accessor(doc,binary,np.linspace(0,.02,11),'SCALAR')
    for sampler in doc['animations'][0]['samplers']:sampler['input']=clock
    write_glb(path,doc,binary);original=path.read_bytes()
    monkeypatch.setattr(studio_native_support,'source',lambda *_:(None,None,None,{'root_node':0},path))
    p=payload();p['source_sha256']=sha256(path);p['contacts']=[dict(vertex=[6,0,0],target_m=[-.22,.19,-.02],start_time_s=.010123,end_time_s=.010125)]
    p['limits']['contact_error_m']=1.
    folder=jobs.prepare(p);attempt=folder/'attempts'/('c'*32);attempt.mkdir(parents=True)
    jobs.execute(folder,attempt)
    core=jobs.core_folder(folder);bound=surface_clip_job.request_for(core)
    assert bound['clip']['contacts'][0]['vertex']==0 and bound['clip']['contacts'][0]['start_time_s']==.010123
    result=read(attempt/'result.json');assert result['summary']['status']=='checkpointed'
    assert result['summary']['validated_through']>0 and 'candidate' in result['files']
    first=result['summary']['validated_through']
    monkeypatch.setattr(studio_native_support,'source',lambda *_:pytest.fail('Continuation reloaded mutable source'))
    second=folder/'attempts'/('d'*32);second.mkdir();jobs.execute(folder,second)
    assert read(second/'result.json')['summary']['validated_through']>first
    assert path.read_bytes()==original and (core/'initial.glb').read_bytes()==original
