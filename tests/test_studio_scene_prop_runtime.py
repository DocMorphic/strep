"""Offline Studio grip drafts; upstream engine resources are explicit doubles."""
import json,shutil,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_scene_prop_runtime as studio
import studio_native_scene_game as game
import action_studio_server as server
from strep import read,save,sha256
from test_native_scene_runtime import fixture as game_fixture
from test_studio_native_scene import handler
from test_scene_prop_runtime import request_for


def setup(tmp_path,monkeypatch,*,scene_pass=True,root_pass=True):
    # Valid complete native-key ZIP; upstream Studio job boundary is a double.
    original,archive,_,_,scene,_,_,_=game_fixture(tmp_path)
    monkeypatch.setattr(game,'ROOT',tmp_path);monkeypatch.setattr(server,'ROOT',tmp_path)
    import action_worker_lock
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    source=game.folder_for('game');(source/'tracks').mkdir(parents=True)
    shutil.copyfile(archive,source/'game-assets.zip')
    for n in ('events.json','root-motion.json'):shutil.copyfile(original/n,source/'tracks'/n)
    save(source/'result.json',dict(status='complete',fixture='Upstream Studio job double',scene_sampled_conditions_pass=scene_pass,root_samples_pass=root_pass))
    save(source/'completion.json',dict(result_sha256=sha256(source/'result.json')));save(source/'pipeline.json',dict(status='complete'))
    bound={n:sha256(source/n) for n in ('game-assets.zip','result.json','completion.json','tracks/events.json','tracks/root-motion.json')}
    def manifest(job):
        if job!='game' or any(sha256(source/n)!=h for n,h in bound.items()):raise ValueError('Upstream game fixture changed')
        return dict(status='complete',scene_sampled_conditions_pass=scene_pass,root_samples_pass=root_pass)
    def frozen(folder,**kwargs):
        manifest(folder.name);return {},(None,None,None,scene)
    monkeypatch.setattr(game,'manifest',manifest);monkeypatch.setattr(game,'frozen',frozen)
    monkeypatch.setattr(studio,'ROOT',tmp_path)
    m=studio.metadata('game')
    request=request_for(source/'game-assets.zip',scene)
    return dict(game_job='game',source_result_sha256=m['source_result_sha256'],request=request),source


@pytest.mark.parametrize('scene_pass,root_pass',[(True,True),(False,True),(True,False)])
def test_complete_grip_package_preserves_source_failures_bytes_and_fixed_downloads(tmp_path,monkeypatch,scene_pass,root_pass):
    payload,source=setup(tmp_path,monkeypatch,scene_pass=scene_pass,root_pass=root_pass)
    before={n:sha256(source/n) for n in ('game-assets.zip','result.json','completion.json','pipeline.json')}
    meta=studio.metadata('game')
    assert next(e for e in meta['confirmed_events'] if e['id']=='marker:fraction')['time_s']==1/480
    assert 'marker:review' not in [e['id'] for e in meta['confirmed_events']]
    assert set(meta['actors'])=={'A','B'} and set(meta['objects'])=={'item'}
    folder=studio.folder_for('complete');studio.prepare(payload,folder);result=studio.run(folder)
    manifest=studio.manifest(folder.name)
    assert result['source_scene_conditions_pass'] is scene_pass and result['root_samples_pass'] is root_pass
    assert manifest['source_scene_conditions_pass'] is scene_pass and manifest['root_samples_pass'] is root_pass
    assert result['source_bytes_unchanged'] and not any(result[k] for k in ('physics_verified','animation_runtime_playback_verified','quality_approved','release_approved','studio_selection_changed'))
    assert before=={n:sha256(source/n) for n in before}
    assert len(manifest['downloads'])==len(studio.DOWNLOADS)
    for d in manifest['downloads']:assert studio.served_file(d['url'].removeprefix('/files/')).is_file()
    for relative in ('implementation/studio_scene_prop_runtime.py','request.json','source-game-assets.zip','runtime/project/scene.json','../game-assets.zip'):
        assert studio.served_file('scene-prop-runtime-jobs/complete/'+relative) is None
    before=sha256(folder/'pipeline.json')
    with pytest.raises(ValueError,match='Fresh prepared'):studio.run(folder)
    assert sha256(folder/'pipeline.json')==before


def test_selected_joint_alignment_uses_exact_event_clock_and_parked_source_prop(tmp_path,monkeypatch):
    payload,source=setup(tmp_path,monkeypatch);scene=studio.source('game')[2]
    actor=scene.actors['A'];node=int(actor['rig'].joints[0]);request=dict(actor='A',joint_node=node,object='item',event_id='marker:fraction')
    payload['request']=request;before=sha256(source/'game-assets.zip');result=studio.align(payload)
    time=1/480;p,r=actor['placement'];placement=np.eye(4);placement[:3,:3]=r;placement[:3,3]=p
    p,r=scene.object_poses('item',np.array([0.]));target=np.eye(4);target[:3,3]=p[0];target[:3,:3]=r[0]
    actual=placement@actor['sampler'].sample(time)[node]@np.array(result['prop_offsets']['item'])
    assert np.allclose(actual,target,atol=1e-12,rtol=0)
    assert result['source_time_f64le']==np.asarray([time],dtype='<f8').tobytes().hex()
    assert result['selection']==request and result['pose_alignment_only'] and result['target']=='parked-source-prop-center-at-zero'
    assert not any(result[k] for k in ('physics_verified','quality_approved','release_approved')) and sha256(source/'game-assets.zip')==before
    from scipy.spatial.transform import Rotation
    assert np.allclose(Rotation.from_euler('xyz',result['rotation_xyz_degrees'],degrees=True).as_matrix(),np.array(result['prop_offsets']['item'])[:3,:3])
    for update in (dict(joint_node=True),dict(joint_node=999),dict(event_id='marker:review'),dict(actor='B'),dict(object='ghost'),dict(guess=True)):
        payload['request']={**request,**update}
        with pytest.raises((ValueError,TypeError,KeyError)):studio.align(payload)


@pytest.mark.parametrize('fault',['result','zip','root','joint','missing-prop','unconfirmed','extra'])
def test_invalid_explicit_request_creates_no_job(tmp_path,monkeypatch,fault):
    payload,_=setup(tmp_path,monkeypatch)
    if fault=='result':payload['source_result_sha256']='0'*64
    elif fault=='zip':payload['request']['source_game_zip_sha256']='0'*64
    elif fault=='root':payload['request']['root_modes'].pop('B')
    elif fault=='joint':payload['request']['grips']['left']['joint_node']=True
    elif fault=='missing-prop':payload['request']['object_modes'].clear()
    elif fault=='unconfirmed':payload['request']['commands'][0]['event_id']='marker:review'
    else:payload['auto_approve']=True
    folder=studio.folder_for('bad')
    with pytest.raises((ValueError,TypeError,KeyError)):studio.prepare(payload,folder)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['request','runtime-request','snapshot','archive','upstream-archive','source'])
def test_frozen_preparation_rejects_changes(tmp_path,monkeypatch,fault):
    payload,source=setup(tmp_path,monkeypatch);folder=studio.folder_for('frozen');studio.prepare(payload,folder)
    path={'request':folder/'request.json','runtime-request':folder/'runtime-request.json','snapshot':folder/'source-game-assets.zip',
          'archive':folder/'implementation/studio_scene_prop_runtime.py','upstream-archive':folder/'implementation/studio_native_scene.py','source':source/'game-assets.zip'}[fault]
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises((ValueError,OSError)):studio.frozen(folder)


@pytest.mark.parametrize('fault',['scale','reflection'])
def test_alignment_rejects_nonrigid_joint_instead_of_approximating_rotation(tmp_path,monkeypatch,fault):
    payload,source=setup(tmp_path,monkeypatch);actor=studio.source('game')[2].actors['A'];node=int(actor['rig'].joints[0])
    payload['request']=dict(actor='A',joint_node=node,object='item',event_id='marker:fraction')
    sample=actor['sampler'].sample
    def invalid(t):
        values=sample(t).copy()
        if fault=='scale':values[node,:3,:3]*=2
        else:values[node,:3,0]*=-1
        return values
    monkeypatch.setattr(actor['sampler'],'sample',invalid)
    before=sha256(source/'game-assets.zip')
    with pytest.raises(ValueError):studio.align(payload)
    assert sha256(source/'game-assets.zip')==before


def rewrite_export(folder,relative,content):
    """Rehash all mutable output receipts: original request/method/source still binds."""
    project=folder/'runtime/project';(project/relative).write_bytes(content)
    exported=read(folder/'runtime/result.json');exported['files_sha256'][relative]=sha256(project/relative)
    manifest={k:v for k,v in exported.items() if k!='package_sha256'};save(project/'package.json',manifest)
    path=folder/'runtime/prop-runtime-assets.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n in list(manifest['files_sha256'])+['package.json']:z.write(project/n,n)
    exported['package_sha256']=sha256(path);save(folder/'runtime/result.json',exported)
    result=read(folder/'result.json');result['package_sha256']=exported['package_sha256']
    result['files_sha256']={n:sha256(folder/n) for n in result['files_sha256']};save(folder/'result.json',result)
    save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))


@pytest.mark.parametrize('fault',['download','source-bytes','helper','configuration','startup-rate','startup-entry','approval'])
def test_changed_export_even_rehashed_cannot_be_served(tmp_path,monkeypatch,fault):
    payload,_=setup(tmp_path,monkeypatch);folder=studio.folder_for('tampered');studio.prepare(payload,folder);studio.run(folder)
    if fault=='download':(folder/'runtime/prop-runtime-assets.zip').write_bytes(b'changed')
    elif fault=='source-bytes':rewrite_export(folder,'animations/A.res',b'Changed original source resource')
    elif fault=='helper':rewrite_export(folder,'ownership-v1/godot_scene_prop_owner.gd',b'Changed runtime helper')
    elif fault=='configuration':
        path=folder/'runtime/project/ownership-v1/prop-runtime.json';v=read(path);v['grip_bindings']['left']['joint_node']=999
        rewrite_export(folder,'ownership-v1/prop-runtime.json',(json.dumps(v)+'\n').encode())
    elif fault=='startup-rate':
        path=folder/'runtime/project/project.godot';rewrite_export(folder,'project.godot',path.read_bytes().replace(b'physics_ticks_per_second=120',b'physics_ticks_per_second=60'))
    elif fault=='startup-entry':rewrite_export(folder,'ownership-v1/scene.tscn',b'[gd_scene format=3]\n[node name="Empty" type="Node3D"]\n')
    else:
        v=read(folder/'result.json');v['physics_verified']=True;save(folder/'result.json',v);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
    with pytest.raises((ValueError,OSError)):studio.manifest(folder.name)
    assert studio.served_file('scene-prop-runtime-jobs/tampered/runtime/prop-runtime-assets.zip') is None


def test_failed_worker_preserves_receipt_and_never_serves_download(tmp_path,monkeypatch):
    payload,_=setup(tmp_path,monkeypatch);folder=studio.folder_for('failed');studio.prepare(payload,folder)
    def fail(*args):raise ValueError('Explicit retained fixture packaging failure')
    monkeypatch.setattr(studio,'package',fail)
    with pytest.raises(ValueError,match='retained'):studio.run(folder)
    assert read(folder/'pipeline.json')['status']=='failed' and studio.manifest('failed')['downloads']==[]
    assert (folder/'runtime-request.json').is_file() and not (folder/'completion.json').exists()
    assert studio.listing()['jobs']==[dict(id='failed',status='failed')]


@pytest.mark.parametrize('route',['assets','align'])
@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409),('valid',202)])
def test_offline_handler_gates(tmp_path,monkeypatch,route,fault,expected):
    payload,_=setup(tmp_path,monkeypatch)
    if route=='align':payload['request']=dict(actor='A',joint_node=payload['request']['grips']['left']['joint_node'],object='item',event_id='marker:grasp')
    h=handler(payload,'/api/scene-prop-runtime-'+route);calls=[]
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy')
    monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(server.subprocess,'Popen',lambda argv,**kw:calls.append((argv,kw)) or SimpleNamespace(poll=lambda:None))
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    if route=='align' and fault=='busy':
        from action_worker_lock import worker_lock
        with worker_lock():h.do_POST()
    else:h.do_POST()
    assert h.responses[-1][0]==(200 if route=='align' and fault=='valid' else expected)
    assert len(calls)==(route=='assets' and fault=='valid')
    if calls:assert Path(calls[0][0][1]).name=='studio_scene_prop_runtime.py' and calls[0][1]['env']['HF_HUB_OFFLINE']=='1'


def test_offline_metadata_get_source_build_and_allowlisted_module(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    for route in ('/api/scene-prop-runtime-source?id=game','/api/scene-prop-runtime-jobs'):
        h=handler({},route);h.do_GET();assert h.responses[-1][0]==200
    h=handler({},'/api/scene-prop-runtime-source?id=game&id=other');h.do_GET();assert h.responses[-1][0]==400
    from build_desktop import render
    page=render();assert page.count('id="scenePropRuntimePanel"')==1 and 'createScenePropRuntimeEditor({api,post})' in page
    assert '__SCENE_PROP_RUNTIME_EDITOR__' not in page
    assert server.allowed_file('/scene-prop-runtime-editor.mjs')==tmp_path/'scripts/scene-prop-runtime-editor.mjs'
