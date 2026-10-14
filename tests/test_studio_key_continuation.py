"""Registered Studio continuation orchestration; numerical replay is tested separately."""
from pathlib import Path
from types import SimpleNamespace
import io,json,os,sys,threading
import psutil,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_key_continuation as jobs
import studio_key_continuation_routes as routes
import action_studio_server as server
from strep import save,read,sha256


@pytest.fixture
def setup(tmp_path,monkeypatch):
    actual=Path(jobs.__file__).parent
    monkeypatch.setattr(jobs,'ROOT',tmp_path);monkeypatch.setattr(routes,'ROOT',tmp_path)
    scripts=tmp_path/'scripts';scripts.mkdir()
    for n in jobs.METHODS:(scripts/n).write_bytes((actual/n).read_bytes())
    parent=tmp_path/'reports/parent';(parent/'probes/final').mkdir(parents=True);(parent/'probes/final/character.glb').write_bytes(b'saved fixture clip')
    request=dict(schema='strep-native-key-interval-restoration-v1',controls=3,**jobs.FLAGS);save(parent/'request.json',request)
    cases=[dict(label='start'),dict(label='final',glb_sha256=sha256(parent/'probes/final/character.glb'))]
    result=dict(schema=request['schema'],status='complete',source_request_sha256=sha256(parent/'request.json'),probes=cases,
        sampled_conditions_pass=False,original_rate_failures=2,floor_failures=1,**jobs.FLAGS);save(parent/'result.json',result)
    proof=tmp_path/'reports/proof.json';save(proof,dict(schema='strep-native-key-restoration-replay-v1',status='complete',
        producer_result_sha256=sha256(parent/'result.json'),producer_request_sha256=sha256(parent/'request.json'),
        retention_history_replayed=True,optimizer_executed=False,cases=[dict(label=v['label'],exact_bytes_and_complete_observations=True) for v in cases],
        sampled_conditions_pass=False,original_rate_failures=2,floor_failures=1,**jobs.FLAGS))
    key=jobs.register(parent,sha256(parent/'result.json'),sha256(parent/'request.json'),proof,sha256(proof),'Saved development correction')
    payload=dict(schema='strep-studio-key-continuation-v1',source_id=key,iterations=1)
    return payload,parent,proof


def guard_fixture(folder,stage,args):
    """Controlled artifacts test sequencing/scope, not geometry or animation quality."""
    save(folder/(stage+'-guard/pipeline.json'),dict(status='complete',**jobs.FLAGS));save(folder/(stage+'-resource-replay.json'),dict(status='complete'))
    if stage=='runtime':save(folder/'runtime/runtime.json',dict(fixture=True))
    elif stage=='correction':
        assert '--expected-runtime-sha256' in args
        (folder/'study/probes/final').mkdir(parents=True);(folder/'study/probes/final/character.glb').write_bytes(b'returned fixture clip')
        save(folder/'study/request.json',dict(fixture=True))
        save(folder/'study/result.json',dict(schema='strep-native-key-continuation-job-v1',status='complete',probes=[dict(label='start'),dict(label='final')],
            original_rate_failures=1,floor_failures=0,sampled_conditions_pass=False,training_admitted=False,all_original_caps_preserved=True,**jobs.FLAGS))
    else:
        assert args[-1]==sha256(folder/'study/request.json')
        save(folder/'replay/result.json',dict(schema='strep-native-key-continuation-job-replay-v1',status='complete',original_reference_unchanged=True,
            producer_result_sha256=sha256(folder/'study/result.json'),producer_request_sha256=sha256(folder/'study/request.json'),
            retention_history_replayed=True,optimizer_executed=False,cases=[dict(label=v,exact_bytes_and_complete_observations=True) for v in ('start','final')],
            original_rate_failures=1,floor_failures=0,sampled_conditions_pass=False,**jobs.FLAGS))
    return 'complete'


def completed(setup,monkeypatch):
    payload,parent,proof=setup;folder=jobs.folder_for('example');jobs.prepare(payload,folder)
    monkeypatch.setattr(jobs,'guarded',guard_fixture);jobs.run(folder);return folder


def test_registered_catalog_and_three_phase_worker_keep_original_bytes(setup,monkeypatch):
    payload,parent,proof=setup;before={p:p.read_bytes() for p in parent.rglob('*') if p.is_file()}
    assert jobs.catalog()['sources'][0]['id']==payload['source_id']
    folder=completed(setup,monkeypatch);m=jobs.manifest(folder.name)
    assert m['status']=='complete' and m['full_replay_pass'] and m['rate_failures']==1 and m['floor_failures']==0
    assert not m['sampled_conditions_pass'] and m['original_selected'] and not m['quality_approved'] and not m['release_approved']
    assert len(m['downloads'])==4 and jobs.listing()['jobs'][0]==m
    assert all(sha256(jobs.served_file(d['url'].removeprefix('/files/')))==d['sha256'] for d in m['downloads'])
    assert {p:p.read_bytes() for p in before}==before and (folder/'input/saved-start.glb').read_bytes()==b'saved fixture clip'
    assert jobs.served_file('key-continuation-jobs/example/recipe.json') is None
    assert jobs.served_file('key-continuation-jobs/example/../../parent/result.json') is None
    with pytest.raises(ValueError,match='restarted'):jobs.run(folder)


@pytest.mark.parametrize('fault',['iterations-bool','iterations-zero','iterations-large','schema','extra','missing-source','changed-source'])
def test_invalid_submission_creates_no_job(setup,monkeypatch,fault):
    payload,parent,proof=setup
    if fault.startswith('iterations'):payload['iterations']={'iterations-bool':True,'iterations-zero':0,'iterations-large':5}[fault]
    elif fault=='schema':payload['schema']='private-trial'
    elif fault=='extra':payload['quality_approved']=True
    elif fault=='missing-source':payload['source_id']='0'*64
    else:save(proof,{})
    folder=jobs.folder_for('invalid')
    with pytest.raises((ValueError,OSError,KeyError)):jobs.prepare(payload,folder)
    assert not folder.exists()


@pytest.mark.parametrize('stage,status',[('runtime','deferred'),('correction','failed'),('replay','failed')])
def test_incomplete_phase_never_publishes_downloads_and_keeps_partial_bytes(setup,monkeypatch,stage,status):
    payload,parent,proof=setup;folder=jobs.folder_for('stopped');jobs.prepare(payload,folder);calls=[]
    def guarded(folder,name,args):
        calls.append(name)
        if name==stage:(folder/'partial.bin').write_bytes(b'keep failed evidence');return status
        return guard_fixture(folder,name,args)
    monkeypatch.setattr(jobs,'guarded',guarded);jobs.run(folder)
    assert jobs.manifest(folder.name)['status']==status and jobs.manifest(folder.name)['downloads']==[]
    assert (folder/'partial.bin').read_bytes()==b'keep failed evidence' and calls[-1]==stage


@pytest.mark.parametrize('fault',['clip','replay','missing-artifact','approval','source-snapshot'])
def test_completed_changed_evidence_is_not_downloadable(setup,monkeypatch,fault):
    folder=completed(setup,monkeypatch)
    if fault=='clip':(folder/'study/probes/final/character.glb').write_bytes(b'changed')
    elif fault=='replay':save(folder/'replay/result.json',{})
    elif fault=='source-snapshot':(folder/'input/saved-start.glb').write_bytes(b'changed')
    else:
        c=read(folder/'completion.json')
        if fault=='approval':c['quality_approved']=True
        else:c['artifacts'].pop('study/probes/final/character.glb')
        save(folder/'completion.json',c)
    with pytest.raises(ValueError):jobs.manifest(folder.name)
    assert jobs.served_file(f'key-continuation-jobs/{folder.name}/study/probes/final/character.glb') is None


def test_dead_worker_is_projected_without_changing_raw_pipeline(setup,monkeypatch):
    payload,parent,proof=setup;folder=jobs.folder_for('dead');jobs.prepare(payload,folder)
    save(folder/'worker.json',dict(pid=1234,created_at=100.,prepared_sha256=sha256(folder/'prepared.json')))
    before=(folder/'pipeline.json').read_bytes()
    monkeypatch.setattr(psutil,'Process',lambda pid:(_ for _ in ()).throw(psutil.NoSuchProcess(pid)))
    assert jobs.manifest(folder.name)['status']=='failed' and (folder/'pipeline.json').read_bytes()==before


def test_metadata_larger_than_the_explicit_bound_is_not_loaded(tmp_path):
    p=tmp_path/'large.json'
    with p.open('wb') as stream:stream.truncate(64*1024**2+1)
    with pytest.raises(ValueError,match='Bounded correction metadata'):jobs.bounded_read(p)


def handler(payload,path='/api/key-continuations',**headers):
    h=server.Handler.__new__(server.Handler);h.path=path;body=json.dumps(payload).encode()
    h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(body)),**headers}
    h.rfile=io.BytesIO(body);h.responses=[];h.respond=lambda code,value:h.responses.append((code,value))
    h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},worker=None,job_lock=threading.Lock());return h


def test_real_dispatch_registers_launch_separately_without_starting_a_server(setup,monkeypatch):
    payload,parent,proof=setup;monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    calls=[]
    def launch(args,**kwargs):calls.append(args);return SimpleNamespace(pid=os.getpid(),poll=lambda:None)
    monkeypatch.setattr(routes.subprocess,'Popen',launch)
    h=handler(payload);h.do_POST();assert h.responses[0][0]==202
    folder=jobs.folder_for(h.responses[0][1]['id']);assert read(folder/'launch.json')['pid']==os.getpid()
    assert jobs.manifest(folder.name)['status']=='starting' and not (folder/'worker.json').exists()
    assert '--offline' in calls[0] and calls[0][-1]==str(folder)
    get=handler({},'/api/key-continuation-sources');get.do_GET();assert get.responses[0][0]==200


@pytest.mark.parametrize('fault',['host','origin','type','transfer','duplicate','oversize','busy'])
def test_transport_and_busy_gates_create_no_jobs(setup,monkeypatch,fault):
    payload,parent,proof=setup;h=handler(payload)
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    if fault=='host':h.headers['Host']='elsewhere'
    elif fault=='origin':h.headers['Origin']='http://elsewhere'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='transfer':h.headers['Transfer-Encoding']='chunked'
    elif fault=='oversize':h.headers['Content-Length']='16385'
    elif fault=='duplicate':
        body=b'{"schema":"one","schema":"two"}';h.rfile=io.BytesIO(body);h.headers['Content-Length']=str(len(body))
    h.do_POST();assert h.responses[0][0] in (400,403,409,415)
    assert not (jobs.ROOT/'reports'/jobs.NAMESPACE).exists()


@pytest.mark.parametrize('identity',['live','dead','reused','denied'])
def test_external_driver_busy_and_resource_wait_projection(setup,monkeypatch,identity):
    payload,parent,proof=setup;folder=jobs.folder_for('external');jobs.prepare(payload,folder)
    save(folder/'pipeline.json',dict(status='processing',stage='correction',**jobs.FLAGS))
    save(folder/'correction-guard/pipeline.json',dict(status='waiting_resources'))
    save(folder/'worker.json',dict(pid=1234,created_at=100.,prepared_sha256=sha256(folder/'prepared.json')))
    before=(folder/'pipeline.json').read_bytes()
    def process(pid):
        if identity=='dead':raise psutil.NoSuchProcess(pid)
        if identity=='denied':raise psutil.AccessDenied(pid)
        return SimpleNamespace(create_time=lambda:101. if identity=='reused' else 100.,is_running=lambda:True,status=lambda:psutil.STATUS_RUNNING)
    monkeypatch.setattr(psutil,'Process',process)
    expected={'live':'waiting_resources','dead':'failed','reused':'failed','denied':'unknown'}[identity]
    assert jobs.manifest(folder.name)['status']==expected
    assert jobs.running()==(identity in ('live','denied'))
    assert (folder/'pipeline.json').read_bytes()==before
    if identity in ('live','denied'):
        monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
        h=handler(payload);h.do_POST();assert h.responses[0][0]==409
        assert len(list(folder.parent.iterdir()))==1


def test_launcher_exiting_before_identity_is_recorded_retains_failed_job(setup,monkeypatch):
    payload,parent,proof=setup
    monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(routes.subprocess,'Popen',lambda *a,**k:SimpleNamespace(pid=1234,poll=lambda:1))
    monkeypatch.setattr(psutil,'Process',lambda pid:(_ for _ in ()).throw(psutil.NoSuchProcess(pid)))
    h=handler(payload);h.do_POST();assert h.responses[0][0]==400
    folders=list((jobs.ROOT/'reports'/jobs.NAMESPACE).iterdir());assert len(folders)==1
    assert jobs.manifest(folders[0].name)['status']=='failed'


def preview_glb():
    import struct
    document={'asset':{'version':'2.0'},'animations':[{'samplers':[{'input':0}]},{'samplers':[{'input':1}]}],
        'accessors':[dict(type='SCALAR',componentType=5126,count=2,min=[0.],max=[.7]),dict(type='SCALAR',componentType=5126,count=120,min=[0.],max=[3.9666666984558105])],
        'buffers':[{'byteLength':0}]}
    payload=json.dumps(document).encode();payload+=b' '*((-len(payload))%4)
    return struct.pack('<5I',0x46546c67,2,len(payload)+20,len(payload),0x4e4f534a)+payload


def preview_completed(setup,monkeypatch):
    folder=completed(setup,monkeypatch);raw=preview_glb()
    for name in ('input/saved-start.glb','study/probes/final/character.glb'):(folder/name).write_bytes(raw)
    result=read(folder/'study/result.json')
    for probe in result['probes']:probe.update(glb_sha256=sha256(folder/'input/saved-start.glb'),output_animation_index=1)
    save(folder/'study/result.json',result)
    prepared=read(folder/'prepared.json');prepared['saved_start_sha256']=sha256(folder/'input/saved-start.glb');save(folder/'prepared.json',prepared)
    c=read(folder/'completion.json');c['prepared_sha256']=sha256(folder/'prepared.json')
    c['artifacts']={name:sha256(folder/name) for name in c['artifacts']};save(folder/'completion.json',c)
    return folder


def test_completed_preview_selects_recorded_appended_clip_and_original_clock(setup,monkeypatch):
    import key_continuation_preview as preview
    folder=preview_completed(setup,monkeypatch);digest=sha256(folder/'completion.json');value=preview.review(folder.name,digest)
    assert value['completion_sha256']==digest and value['original_selected'] and not value['sampled_conditions_pass']
    assert [(v['id'],v['animation_index'],v['animation_count']) for v in value['previews']]==[('source',1,2),('candidate',1,2)]
    assert all(v['preview_start_s']==0 and v['preview_end_s']==3.9666666984558105 for v in value['previews'])
    h=handler({},f'/api/key-continuation-preview?id={folder.name}&completion={digest}');h.do_GET();assert h.responses[0]==(200,value)
    for suffix in ('&completion='+digest,'&extra=x'):
        h=handler({},f'/api/key-continuation-preview?id={folder.name}&completion={digest}'+suffix);h.do_GET();assert h.responses[0][0]==400
    with pytest.raises(ValueError,match='changed'):preview.review(folder.name,'0'*64)


@pytest.mark.parametrize('fault',['index','clock','external','header','digest'])
def test_preview_rejects_missing_or_changed_clock_selection_and_bytes(setup,monkeypatch,fault):
    import key_continuation_preview as preview
    folder=preview_completed(setup,monkeypatch);digest=sha256(folder/'completion.json')
    if fault=='digest':
        (folder/'study/probes/final/character.glb').write_bytes(b'changed')
        with pytest.raises(ValueError):preview.review(folder.name,digest)
        return
    path=folder/'input/saved-start.glb'
    if fault=='index':
        with pytest.raises(ValueError,match='selection'):preview.clip_metadata(path,True)
    elif fault=='header':
        path.write_bytes(b'invalid glb bytes are invalid')
        with pytest.raises(ValueError,match='metadata'):preview.clip_metadata(path,1)
    else:
        import struct
        raw=preview_glb();document=json.loads(raw[20:])
        if fault=='clock':document['accessors'][1]['max']=[float('inf')]
        else:document['buffers'][0]['uri']='https://example.test/payload.bin'
        raw=json.dumps(document).encode();raw+=b' '*((-len(raw))%4)
        path.write_bytes(struct.pack('<5I',0x46546c67,2,len(raw)+20,len(raw),0x4e4f534a)+raw)
        with pytest.raises(ValueError):preview.clip_metadata(path,1)
