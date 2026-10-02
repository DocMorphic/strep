"""Explicit Studio preparation retains original/version bindings and evidence."""
from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_studio_native_support import setup
from rig_asset import RigAsset
from gltf_tools import write_glb,append_accessor
from strep import read,save,sha256
import studio_native_support as studio
import native_support_rigid_input as preparation


def rounded(setup,monkeypatch,*,scale=1.0000004,far=False):
    monkeypatch.setattr(preparation,'ROOT',setup.root)
    rig=RigAsset.load(setup.source);doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
    doc['nodes'][0]['scale']=[scale,1.,1.]
    if far:doc['meshes'][0]['primitives'][0]['attributes']['POSITION']=append_accessor(doc,data,[[1000,.19,0],[1001,.19,0],[1000,.19,.1]],'VEC3')
    write_glb(setup.source,doc,data);setup.spec['glb_sha256']=sha256(setup.source)
    body=copy.deepcopy(setup.body);body['prepare_rigid_input']=True
    return body


def completed(setup,monkeypatch):
    body=rounded(setup,monkeypatch);folder=studio.folder_for('prepared')
    studio.prepare(body,folder);studio.run(folder)
    return folder,setup.root/'reports/native-support-rigid-prepared',setup.root/'reports/native-support-fit-prepared'


def test_metadata_exposes_static_eligibility_without_claiming_geometry_approval(setup,monkeypatch):
    rounded(setup,monkeypatch);data=studio.metadata('parent','transfer')
    assert data['primitive_count']==1 and data['rigid_preparation']['eligible']
    assert data['rigid_preparation']['static_node_changes']==1 and data['rigid_preparation']['geometry_check_pending']
    assert not data['quality_approved']


@pytest.mark.parametrize('choice',[1,0,'true',None,{},[]])
def test_preparation_mode_must_be_an_explicit_boolean(setup,choice):
    body=copy.deepcopy(setup.body);body['prepare_rigid_input']=choice
    with pytest.raises(ValueError,match='choice'):studio.validate_request(body)


@pytest.mark.parametrize('scale',[1.,1.000001])
def test_ineligible_or_unnecessary_conversion_is_not_accepted(setup,monkeypatch,scale):
    body=rounded(setup,monkeypatch,scale=scale)
    with pytest.raises(ValueError,match='eligible'):studio.validate_request(body)


def test_actual_worker_keeps_original_and_distinct_prepared_input_visible(setup,monkeypatch):
    folder,prepared,fit=completed(setup,monkeypatch);original=sha256(setup.source)
    review=studio.manifest('prepared');p=review['preparation']
    assert p['original_sha256']==original==sha256(folder/'source.glb')==sha256(prepared/'input.glb')
    assert p['prepared_sha256']==sha256(prepared/'prepared.glb')==sha256(fit/'input.glb')
    assert p['original_sha256']!=p['prepared_sha256'] and 0<p['maximum_vertex_distance_m']<1e-5
    assert review['versions'][0]['id']=='original.glb' and review['versions'][1]['label']=='Prepared input'
    assert len(review['versions'])==7 and review['retained_input'] and not review['quality_approved']
    assert read(folder/'draft.json')==setup.spec
    expected=copy.deepcopy(setup.spec);expected['glb_sha256']=p['prepared_sha256']
    assert read(folder/'prepared-draft.json')==expected
    assert studio.served_file('native-support-jobs/prepared/original.glb')==folder/'source.glb'
    assert studio.served_file('native-support-jobs/prepared/rigid-comparison.json')==prepared/'comparison.json'
    assert studio.served_file('native-support-jobs/prepared/rigid-preparation.json')==prepared/'result.json'
    for name in ('prepared.glb','source.glb','preparation-binding.json','implementation/native_support_rigid_input.py'):
        assert studio.served_file('native-support-jobs/prepared/'+name) is None


@pytest.mark.parametrize('fault',['original','prepared','draft','binding','comparison','result','method','runtime'])
def test_changed_preparation_cannot_be_reviewed_or_served(setup,monkeypatch,fault):
    folder,prepared,fit=completed(setup,monkeypatch)
    path={'original':folder/'source.glb','prepared':prepared/'prepared.glb','draft':folder/'prepared-draft.json',
        'binding':folder/'preparation-binding.json','comparison':prepared/'comparison.json',
        'result':prepared/'result.json','method':prepared/'implementation/native_support_rigid_input.py','runtime':folder/'numerical-runtime.json'}[fault]
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):studio.manifest('prepared')
    assert studio.served_file('native-support-jobs/prepared/original.glb') is None
    assert studio.listing()['jobs'][0]['status']=='failed'


def test_rebinding_a_prepared_draft_cannot_change_original_authoring_bounds(setup,monkeypatch):
    folder,prepared,fit=completed(setup,monkeypatch)
    spec=read(folder/'prepared-draft.json');spec['supports'][0]['maximum_displacement_m']=.1
    save(folder/'prepared-draft.json',spec)
    receipt=read(folder/'preparation-binding.json');receipt['draft_sha256']=sha256(folder/'prepared-draft.json');save(folder/'preparation-binding.json',receipt)
    completion=read(folder/'completion.json');completion['preparation_binding_sha256']=sha256(folder/'preparation-binding.json');save(folder/'completion.json',completion)
    with pytest.raises(ValueError,match='authoring bounds'):studio.manifest('prepared')


def test_preflight_eligibility_does_not_hide_worker_geometry_rejection(setup,monkeypatch):
    body=rounded(setup,monkeypatch,far=True)
    assert studio.metadata('parent','transfer')['rigid_preparation']['eligible']
    folder=studio.folder_for('large-change');studio.prepare(body,folder)
    with pytest.raises(ValueError,match='geometry change budget'):studio.run(folder)
    assert read(folder/'pipeline.json')['status']=='failed'
    assert sha256(folder/'source.glb')==setup.spec['glb_sha256']
    assert not (setup.root/'reports/native-support-fit-large-change').exists()


def test_http_preparation_submission_and_bound_original_comparison(setup,monkeypatch):
    import json,threading
    from http.client import HTTPConnection
    from http.server import ThreadingHTTPServer
    from types import SimpleNamespace
    import action_studio_server as server_module
    body=rounded(setup,monkeypatch)
    monkeypatch.setattr(server_module,'worker_busy',lambda:False)
    monkeypatch.setattr(server_module,'external_pair_fit_busy',lambda:False)
    def launch(args,**kwargs):
        assert Path(args[1]).name=='studio_native_support.py'
        studio.run(Path(args[2]));return SimpleNamespace(pid=99999999,poll=lambda:0)
    monkeypatch.setattr(server_module.subprocess,'Popen',launch)
    server=ThreadingHTTPServer(('127.0.0.1',0),server_module.Handler)
    host=f'127.0.0.1:{server.server_port}';server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(method,path,body=None,origin=True):
        connection=HTTPConnection('127.0.0.1',server.server_port)
        headers={'Host':host,'Content-Type':'application/json'}
        if origin:headers['Origin']='http://'+host
        connection.request(method,path,json.dumps(body) if body is not None else None,headers)
        response=connection.getresponse();data=response.read();status=response.status;connection.close();return status,data
    try:
        status,data=request('GET','/api/native-support-source?job=parent&variant=transfer')
        assert status==200 and json.loads(data)['rigid_preparation']['static_node_changes']==1
        assert request('POST','/api/native-support-edits',body,False)[0]==403
        status,data=request('POST','/api/native-support-edits',body);assert status==202
        job=json.loads(data)['id'];status,data=request('GET','/api/native-support-review?id='+job)
        assert status==200;review=json.loads(data)
        assert review['preparation']['original_sha256']==setup.spec['glb_sha256']
        assert request('GET',review['versions'][0]['url'])[1]==setup.source.read_bytes()
        status,data=request('GET',review['preparation']['comparison_url'])
        assert status==200 and json.loads(data)['native_animation_bytes_preserved']
        assert request('GET',f'/files/native-support-jobs/{job}/preparation-binding.json')[0]==404
        server.worker=SimpleNamespace(poll=lambda:None)
        assert request('POST','/api/native-support-edits',body)[0]==409
    finally:server.shutdown();server.server_close();thread.join()


def test_worker_limits_pools_after_numerical_imports_and_restores_caller(setup,monkeypatch):
    from threadpoolctl import threadpool_info,threadpool_limits
    import native_support_job
    original=native_support_job.run;observed=[]
    def checked(*args,**kwargs):
        observed.extend(p['num_threads'] for p in threadpool_info())
        return original(*args,**kwargs)
    monkeypatch.setattr(native_support_job,'run',checked)
    body=rounded(setup,monkeypatch);folder=studio.folder_for('threads');studio.prepare(body,folder)
    with threadpool_limits(limits=2):
        before=[p['num_threads'] for p in threadpool_info()];studio.run(folder)
        assert [p['num_threads'] for p in threadpool_info()]==before
    assert observed and all(n==1 for n in observed)
    runtime=read(folder/'numerical-runtime.json');assert runtime['configured_limit']==1 and all(p['num_threads']==1 for p in runtime['pools'])
    assert studio.manifest('threads')['preparation']
