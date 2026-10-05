"""Offline Studio bake contracts; upstream Studio and engine are explicit doubles."""
import copy,json,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_scene_prop_bake as studio
import studio_scene_prop_runtime as prop
import scene_prop_bake as core
import action_studio_server as server
from strep import read,save,sha256
from native_object_asset import ObjectAsset
from test_scene_prop_bake import setup as source_fixture,trace,request as bake_request
from test_studio_native_scene import handler


def setup(tmp_path,monkeypatch,*,scene_pass=False,root_pass=True):
    folder,archive,scene,events,r,compiled,clock,poses=source_fixture(tmp_path)
    monkeypatch.setattr(prop,'ROOT',tmp_path);monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(server,'ROOT',tmp_path)
    import action_worker_lock
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    source=prop.folder_for('runtime');source.mkdir(parents=True)
    path=source/'runtime-request.json';save(path,r);prop.package(archive,path,source/'runtime')
    save(source/'result.json',dict(status='complete',fixture='Upstream Studio job double'))
    original={n:sha256(source/n) for n in ('result.json','runtime/prop-runtime-assets.zip','runtime/project/ownership-v1/prop-runtime.json')}
    manifest=dict(status='complete',source_scene_conditions_pass=scene_pass,root_samples_pass=root_pass)
    def verify(job):
        if job!='runtime' or any(sha256(source/n)!=h for n,h in original.items()):raise ValueError('Upstream runtime fixture changed')
        return copy.deepcopy(manifest)
    monkeypatch.setattr(prop,'manifest',verify)
    monkeypatch.setattr(prop,'frozen',lambda p,**kw:({},(folder,manifest,scene,events,compiled)))
    engine=tmp_path/'engine.exe';engine.write_bytes(b'Explicit engine test double')
    monkeypatch.setattr(core,'ENGINE',engine);monkeypatch.setattr(core,'ENGINE_SHA256',sha256(engine))
    def execute(project,script,path,out,log,timeout):
        payload=read(path)
        if script.endswith(core.CAPTURE):value=trace(scene,events,compiled,clock,poses,sha256(path))
        else:
            asset=ObjectAsset(payload['asset_path']);times=payload['payload']['sample_times_s'];value=dict(import_bake_fps=payload['import_bake_fps'])
            for mode in ('default-import','native-authoring'):
                value[mode]={}
                for n in asset.objects:
                    p,rot=asset.object_poses(n,times);q=Rotation.from_matrix(rot).as_quat()
                    if mode=='default-import' and payload['import_bake_fps']==30:p=p+np.array([.01,0,0])
                    value[mode][n]=[dict(time_f64le=core.bits(t),translation_m=x.tolist(),rotation_xyzw=y.tolist()) for t,x,y in zip(times,p,q)]
            Path(payload['resource_path']).write_bytes(b'Explicit native resource double')
        save(out,value);Path(log).write_text('Explicit engine double; no actual physics\n');return value
    monkeypatch.setattr(core,'engine_run',execute)
    meta=studio.metadata('runtime');payload=dict(runtime_job='runtime',source_result_sha256=meta['source_result_sha256'],request=bake_request(source/'runtime/prop-runtime-assets.zip'))
    return payload,source


def complete(tmp_path,monkeypatch):
    payload,source=setup(tmp_path,monkeypatch);folder=studio.folder_for('complete');studio.prepare(payload,folder);studio.run(folder);return folder,source


def test_complete_bake_preserves_source_failures_and_fixed_downloads(tmp_path,monkeypatch):
    folder,source=complete(tmp_path,monkeypatch);before=sha256(source/'runtime/prop-runtime-assets.zip')
    m=studio.manifest(folder.name)
    assert m['source_scene_conditions_pass'] is False and m['root_samples_pass'] is True
    assert m['engine_import_verified'] and not m['exact_physical_event_timing_pass'] and m['maximum_application_delay_s']==.00625
    assert m['floor_sampled_screen_pass'] is None and not m['default_30fps_import_pass'] and not m['quality_approved'] and not m['release_approved']
    assert len(m['downloads'])==len(studio.DOWNLOADS) and before==sha256(source/'runtime/prop-runtime-assets.zip')
    for d in m['downloads']:assert studio.served_file(d['url'].removeprefix('/files/')).is_file()
    for n in ('source-runtime.zip','implementation/studio_scene_prop_bake.py','bake/capture.json','bake/assets/objects.glb','../outside.zip'):
        assert studio.served_file('scene-prop-bake-jobs/complete/'+n) is None
    with pytest.raises(ValueError,match='Fresh prepared'):studio.run(folder)


@pytest.mark.parametrize('fault',['result','zip','floor-bool','scale','extra'])
def test_invalid_bound_bake_creates_no_job(tmp_path,monkeypatch,fault):
    p,_=setup(tmp_path,monkeypatch)
    if fault=='result':p['source_result_sha256']='0'*64
    elif fault=='zip':p['request']['source_runtime_zip_sha256']='0'*64
    elif fault=='floor-bool':p['request']['floor']['enabled']='false'
    elif fault=='scale':p['request']['parent_world_transform'][0][0]=2
    else:p['auto_approve']=True
    folder=studio.folder_for('invalid')
    with pytest.raises((ValueError,TypeError,KeyError)):studio.prepare(p,folder)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['request','snapshot','archive','source'])
def test_prepared_bake_rejects_source_or_method_drift(tmp_path,monkeypatch,fault):
    p,source=setup(tmp_path,monkeypatch);folder=studio.folder_for('prepared');studio.prepare(p,folder)
    path={'request':folder/'bake-request.json','snapshot':folder/'source-runtime.zip','archive':folder/'implementation/scene_prop_bake.py','source':source/'runtime/prop-runtime-assets.zip'}[fault]
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises((ValueError,OSError)):studio.frozen(folder)


def rewrite_asset(folder,name,content):
    assets=folder/'bake/assets';(assets/name).write_bytes(content);m=read(assets/'package.json');m['files_sha256'][name]=sha256(assets/name);save(assets/'package.json',m)
    archive=folder/'bake/baked-assets.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for n in list(m['files_sha256'])+['package.json']:z.write(assets/n,n)
    r=read(folder/'bake/result.json');r.update(m);r['package_sha256']=sha256(archive);save(folder/'bake/result.json',r)
    execution=read(folder/'execution.json');execution['artifacts_sha256']={n:sha256(folder/n) for n in execution['artifacts_sha256']};save(folder/'execution.json',execution)
    r=read(folder/'result.json');r['execution_sha256']=sha256(folder/'execution.json');r['package_sha256']=sha256(archive);r['files_sha256']={n:sha256(folder/n) for n in r['files_sha256']};save(folder/'result.json',r)
    save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))


@pytest.mark.parametrize('fault',['download','resource','capture-source','actor','composition','motion-audit','storage-audit','import-audit','approval'])
def test_changed_or_rehashed_outputs_are_not_served(tmp_path,monkeypatch,fault):
    folder,_=complete(tmp_path,monkeypatch)
    if fault=='download':(folder/'bake/baked-assets.zip').write_bytes(b'changed')
    elif fault=='resource':(folder/'bake/assets/objects.res').write_bytes(b'Changed saved resource')
    elif fault=='capture-source':(folder/'bake/capture-project/scene.json').write_bytes(b'Changed capture source')
    elif fault=='actor':rewrite_asset(folder,'reference/animations/A.res',b'Changed original resource')
    elif fault=='composition':
        v=read(folder/'bake/assets/composition.json');v['actors']['A']['end_policy']='loop';rewrite_asset(folder,'composition.json',(json.dumps(v)+'\n').encode())
    elif fault=='motion-audit':
        v=read(folder/'bake/assets/baked-motion-audit.json');v['held_grip_position_error_max_m']+=1;rewrite_asset(folder,'baked-motion-audit.json',(json.dumps(v)+'\n').encode())
    elif fault=='storage-audit':
        v=read(folder/'bake/assets/bake-storage.json');v['quality_approved']=True;rewrite_asset(folder,'bake-storage.json',(json.dumps(v)+'\n').encode())
    elif fault=='import-audit':
        v=read(folder/'bake/assets/import-audit.json');v['default_30fps_import_pass']=True;rewrite_asset(folder,'import-audit.json',(json.dumps(v)+'\n').encode())
    else:
        r=read(folder/'result.json');r['quality_approved']=True;save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
    with pytest.raises((ValueError,OSError)):studio.manifest(folder.name)
    assert studio.served_file('scene-prop-bake-jobs/complete/bake/baked-assets.zip') is None


def test_failed_bake_retains_request_and_has_no_downloads(tmp_path,monkeypatch):
    p,_=setup(tmp_path,monkeypatch);folder=studio.folder_for('failed');studio.prepare(p,folder)
    def fail(*a):raise ValueError('Explicit retained bake failure')
    monkeypatch.setattr(core,'bake',fail)
    with pytest.raises(ValueError,match='retained'):studio.run(folder)
    assert studio.manifest('failed')['downloads']==[] and read(folder/'pipeline.json')['status']=='failed'
    assert (folder/'bake-request.json').is_file() and not (folder/'completion.json').exists()


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409),('valid',202)])
def test_offline_handler_gates(tmp_path,monkeypatch,fault,expected):
    p,_=setup(tmp_path,monkeypatch);h=handler(p,'/api/scene-prop-bake-assets');calls=[]
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(server.subprocess,'Popen',lambda argv,**kw:calls.append((argv,kw)) or SimpleNamespace(poll=lambda:None))
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:assert Path(calls[0][0][1]).name=='studio_scene_prop_bake.py' and calls[0][1]['env']['HF_HUB_OFFLINE']=='1'


def test_offline_metadata_build_and_module_allowlist(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    for path in ('/api/scene-prop-bake-source?id=runtime','/api/scene-prop-bake-jobs'):
        h=handler({},path);h.do_GET();assert h.responses[-1][0]==200
    h=handler({},'/api/scene-prop-bake-source?id=runtime&id=other');h.do_GET();assert h.responses[-1][0]==400
    from build_desktop import render
    page=render();assert page.count('id="scenePropBakePanel"')==1 and 'createScenePropBakeEditor({api,post})' in page and '__SCENE_PROP_BAKE_EDITOR__' not in page
    assert server.allowed_file('/scene-prop-bake-editor.mjs')==tmp_path/'scripts/scene-prop-bake-editor.mjs'
