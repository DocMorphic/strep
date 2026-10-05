"""Offline Studio saved-scene contracts; upstream and engine are explicit doubles."""
import copy,json,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_baked_scene_runtime as studio
import studio_scene_prop_bake as bake
import baked_scene_runtime as sdk
import action_studio_server as server
from strep import read,save,sha256
from test_studio_scene_prop_bake import complete as baked_fixture
from test_baked_scene_runtime import observation
from test_studio_native_scene import handler


@pytest.fixture(scope='module')
def baked(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        job,_=baked_fixture(tmp_path_factory.mktemp('saved-scene-upstream'),patch)
        return (job/'bake/baked-assets.zip').read_bytes(),(job/'result.json').read_bytes(),bake.manifest(job.name)


def setup(tmp_path,monkeypatch,baked):
    monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(bake,'ROOT',tmp_path);monkeypatch.setattr(server,'ROOT',tmp_path)
    import action_worker_lock
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    source=bake.folder_for('source');(source/'bake').mkdir(parents=True)
    (source/'result.json').write_bytes(baked[1]);(source/'bake/baked-assets.zip').write_bytes(baked[0])
    hashes={n:sha256(source/n) for n in ('result.json','bake/baked-assets.zip')}
    def upstream(job):
        if job!='source' or any(sha256(source/n)!=h for n,h in hashes.items()):raise ValueError('Explicit upstream bake fixture changed')
        return copy.deepcopy(baked[2])
    monkeypatch.setattr(bake,'manifest',upstream)
    engine=tmp_path/'engine.exe';engine.write_bytes(b'Explicit headless engine double')
    monkeypatch.setattr(sdk,'ENGINE',engine);monkeypatch.setattr(sdk,'ENGINE_SHA256',sha256(engine))
    def execute(project,script,path,out,log,timeout):
        request=read(path);config,scene,asset,_,events=sdk.configure_bake(project,read(project/'package.json'))
        queries=np.frombuffer(bytes.fromhex(request['clock']['bytes_hex']),dtype='<f8');actual=observation(config,scene,asset,queries,events);actual['request_sha256']=sha256(path)
        save(out,actual);Path(log).write_text('Explicit engine double; no actual engine\n');return actual
    monkeypatch.setattr(sdk,'engine_run',execute)
    return dict(bake_job='source',source_result_sha256=hashes['result.json']),source


def complete(tmp_path,monkeypatch,baked):
    payload,source=setup(tmp_path,monkeypatch,baked);folder=studio.folder_for('complete');studio.prepare(payload,folder);studio.run(folder);return folder,source


def test_complete_shared_playback_exports_preserve_failures_and_fixed_downloads(tmp_path,monkeypatch,baked):
    folder,source=complete(tmp_path,monkeypatch,baked);before=sha256(source/'bake/baked-assets.zip');m=studio.manifest(folder.name)
    assert m['scene_playback_verified'] and m['exported_main_scene_verified'] and not m['live_prop_physics']
    assert not m['source_scene_conditions_pass'] and not m['exact_physical_event_timing_pass'] and not m['default_30fps_import_pass']
    assert m['maximum_application_delay_s']==.00625 and not m['quality_approved'] and not m['release_approved']
    assert len(m['downloads'])==5 and sha256(source/'bake/baked-assets.zip')==before
    for d in m['downloads']:assert studio.served_file(d['url'].removeprefix('/files/')).is_file()
    for n in ('source-baked-assets.zip','implementation/studio_baked_scene_runtime.py','audit/actual.json','../outside.zip'):
        assert studio.served_file('baked-scene-jobs/complete/'+n) is None
    with pytest.raises(ValueError,match='Fresh'):studio.run(folder)


@pytest.mark.parametrize('fault',['missing','extra','hash','traversal','not-complete','corrupt-source'])
def test_requests_bind_only_exact_completed_source(tmp_path,monkeypatch,baked,fault):
    payload,_=setup(tmp_path,monkeypatch,baked)
    if fault=='missing':payload.pop('source_result_sha256')
    elif fault=='extra':payload['root_mode']='extracted'
    elif fault=='hash':payload['source_result_sha256']='0'*64
    elif fault=='traversal':payload['bake_job']='../source'
    elif fault=='not-complete':monkeypatch.setattr(bake,'manifest',lambda job:dict(status='processing'))
    else:
        def corrupt(job):raise zipfile.BadZipFile('Explicit corrupt source')
        monkeypatch.setattr(bake,'manifest',corrupt)
    with pytest.raises(ValueError):studio.validate_request(payload)


@pytest.mark.parametrize('fault',['request','snapshot','archive','source-result','source-zip','condition'])
def test_snapshot_and_method_drift_retained_as_failed_job(tmp_path,monkeypatch,baked,fault):
    payload,source=setup(tmp_path,monkeypatch,baked);folder=studio.folder_for('failed');studio.prepare(payload,folder)
    if fault=='condition':p=read(folder/'prepared.json');p['conditions']['source_scene_conditions_pass']=True;save(folder/'prepared.json',p)
    else:
        p={'request':folder/'request.json','snapshot':folder/'source-baked-assets.zip','archive':folder/'implementation/baked_scene_runtime.py','source-result':source/'result.json','source-zip':source/'bake/baked-assets.zip'}[fault]
        p.write_bytes(p.read_bytes()+b' changed')
    with pytest.raises((ValueError,json.JSONDecodeError)):studio.run(folder)
    assert studio.manifest(folder.name)['downloads']==[] and read(folder/'pipeline.json')['status']=='failed'


def rehash(folder):
    """Rehash mutable receipts to require semantic/source checks too."""
    project=folder/'runtime/project';m=read(project/'baked-runtime-v1/package.json')
    m['files_sha256']={n:sha256(project/n) for n in m['files_sha256']};save(project/'baked-runtime-v1/package.json',m)
    (folder/'audit/project/baked-runtime-v1/package.json').write_bytes((project/'baked-runtime-v1/package.json').read_bytes())
    for n in m['files_sha256']:
        p=folder/'audit/project'/n;p.write_bytes((project/n).read_bytes())
    archive=folder/'runtime/baked-runtime.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n in list(m['files_sha256'])+['baked-runtime-v1/package.json']:z.write(project/n,n)
    save(folder/'runtime/result.json',dict(**m,package_sha256=sha256(archive)))
    e=read(folder/'execution.json');e['artifacts_sha256']={n:sha256(folder/n) for n in e['artifacts_sha256']};save(folder/'execution.json',e)
    r=read(folder/'result.json');r['execution_sha256']=sha256(folder/'execution.json');r['package_sha256']=sha256(archive);r['files_sha256']={n:sha256(folder/n) for n in r['files_sha256']};save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))


@pytest.mark.parametrize('fault',['actor','helper','config','observation','request-clock','source-marker','audit-summary','result-condition'])
def test_rehashed_output_changes_cannot_approve_different_scene(tmp_path,monkeypatch,baked,fault):
    folder,_=complete(tmp_path,monkeypatch,baked);project=folder/'runtime/project'
    if fault in ('actor','helper'):
        p=project/('reference/actors/0.glb' if fault=='actor' else 'baked-runtime-v1/godot_baked_scene_player.gd');p.write_bytes(p.read_bytes()+b' changed')
    elif fault=='config':p=project/'baked-runtime-v1/runtime.json';v=read(p);v['actor_end_policy']='loop';save(p,v)
    elif fault=='source-marker':p=project/'reference/events.json';v=read(p);v['events'][0]['id']='different';save(p,v)
    elif fault=='observation':p=folder/'audit/actual.json';v=read(p);v['frames'][-1]['actors'].clear();save(p,v)
    elif fault=='request-clock':p=folder/'audit/request.json';v=read(p);v['clock']['bytes_hex']='00';save(p,v)
    elif fault=='audit-summary':p=folder/'audit/result.json';v=read(p);v['maximum_pose_component_error']['actor']=.001;save(p,v)
    else:p=folder/'result.json';v=read(p);v['conditions']['exact_physical_event_timing_pass']=True;save(p,v)
    rehash(folder)
    with pytest.raises(ValueError):studio.manifest(folder.name)
    assert studio.served_file('baked-scene-jobs/complete/runtime/baked-runtime.zip') is None


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409),('valid',202)])
def test_offline_handler_gates(tmp_path,monkeypatch,baked,fault,expected):
    payload,_=setup(tmp_path,monkeypatch,baked);h=handler(payload,'/api/baked-scene-assets');calls=[]
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(server.subprocess,'Popen',lambda argv,**kw:calls.append((argv,kw)) or SimpleNamespace(poll=lambda:None))
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:assert Path(calls[0][0][1]).name=='studio_baked_scene_runtime.py' and calls[0][1]['env']['HF_HUB_OFFLINE']=='1'


def test_offline_metadata_build_and_module_allowlist(tmp_path,monkeypatch,baked):
    setup(tmp_path,monkeypatch,baked)
    for path in ('/api/baked-scene-source?id=source','/api/baked-scene-jobs'):
        h=handler({},path);h.do_GET();assert h.responses[-1][0]==200
    h=handler({},'/api/baked-scene-source?id=source&id=other');h.do_GET();assert h.responses[-1][0]==400
    from build_desktop import render
    page=render();assert page.count('id="bakedScenePanel"')==1 and 'createBakedSceneEditor({api,post})' in page and '__BAKED_SCENE_EDITOR__' not in page
    assert server.allowed_file('/baked-scene-editor.mjs')==tmp_path/'scripts/baked-scene-editor.mjs'
