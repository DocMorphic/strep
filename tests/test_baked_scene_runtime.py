"""Whole saved-scene contracts with explicitly synthetic upstream/engine data."""
import copy,json,sys,zipfile
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import baked_scene_runtime as runtime
from native_engine_clock import clock_wire
from strep import read,save,sha256
from test_studio_scene_prop_bake import complete


@pytest.fixture(scope='module')
def baked(tmp_path_factory):
    folder=tmp_path_factory.mktemp('baked-scene-source')
    with pytest.MonkeyPatch.context() as patch:
        job,_=complete(folder,patch)
    return job/'bake/baked-assets.zip'


def rewrite(source,target,change,*,runtime_package=False):
    with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
    header='baked-runtime-v1/package.json' if runtime_package else 'package.json'
    change(files)
    manifest=json.loads(files[header])
    import hashlib
    manifest['files_sha256']={n:hashlib.sha256(v).hexdigest() for n,v in files.items() if n!=header}
    files[header]=json.dumps(manifest).encode()
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,v in files.items():z.writestr(n,v)
    return target


def context(baked,folder):
    manifest=runtime.unpack(baked,folder)
    config,scene,asset,clock,events=runtime.configure_bake(folder,manifest)
    queries=np.unique(np.r_[clock,(clock[:-1]+clock[1:])/2,np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8'),scene.duration])
    return config,scene,asset,queries,events


def observation(config,scene,asset,queries,events):
    """CPU synthetic observations; no Godot/render/quality evidence."""
    encode=lambda value:np.asarray(value,dtype='<f8').tobytes().hex()
    parent=np.asarray(config['parent_world_transform'])
    def root(name,time):
        a=scene.actors[name];bone=next(e['root_bone'] for e in config['actors'] if e['id']==name)
        node=next(int(j) for j in a['rig'].joints if a['rig'].document['nodes'][int(j)]['name']==bone)
        return a['sampler'].sample(min(time,scene.duration))[node]@np.linalg.inv(a['sampler'].sample(0)[node])
    def frame(time,previous=0.):
        row=dict(time_f64le=encode([time]),actors={},objects={},root_motion={},root_deltas={})
        for name,a in scene.actors.items():
            placement=np.eye(4);placement[:3,3]=a['placement'][0];placement[:3,:3]=a['placement'][1]
            matrices=parent@placement@a['sampler'].sample(min(time,scene.duration))[a['rig'].joints]
            row['actors'][name]={a['rig'].document['nodes'][int(node)]['name']:encode(matrix) for node,matrix in zip(a['rig'].joints,matrices)}
            row['root_motion'][name]=encode(root(name,time));row['root_deltas'][name]=encode(np.linalg.inv(root(name,previous))@root(name,time))
        for name in asset.objects:
            p,r=asset.object_poses(name,[time]);m=np.eye(4);m[:3,3]=p[0];m[:3,:3]=r[0];row['objects'][name]=encode(parent@m)
        return row
    value=dict(schema='strep-baked-scene-audit-v1',faults=[],collision_objects=0,invalid_time_rejected=True,moved_parent_rejected=True,
        boot_bound=True,preview_silent=True,repeat_silent=True,repeat_root_delta_identity=True,backward_rejected=True,invalid_bindings_rejected=12,no_binding_leaks=True,
        object_key_envelope_s=max(config['duration_s'],float(np.float32(config['duration_s']))),
        frames=[frame(t,0. if i==0 else queries[i-1]) for i,t in enumerate(queries)],boot_frame=frame(config['duration_s']))
    native=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')
    for key in ('callbacks','skipped_callbacks','restart_callbacks','boot_callbacks'):
        rows=[]
        for event in events['events']:
            if not event['runtime_dispatch_allowed']:continue
            t=native[event['sample_index']];index=int(np.searchsorted(queries,t))
            rows.append(dict(frame(t,queries[index-1] if key in ('callbacks','restart_callbacks') and index else 0.),id=event['id']))
        value[key]=rows
    return value


def test_package_keeps_complete_original_bytes_and_unapproved_scope(baked,tmp_path):
    before=sha256(baked);result=runtime.package(baked,tmp_path/'saved')
    with zipfile.ZipFile(baked) as src,zipfile.ZipFile(tmp_path/'saved/baked-runtime.zip') as out:
        assert all(src.read(n)==out.read(n) for n in src.namelist())
        config=json.loads(out.read('baked-runtime-v1/runtime.json'))
        assert config['actor_end_policy']=='hold-original-end' and config['root_mode']=='original-embedded'
        assert all(not a['extract'] for a in config['actors'])
        assert all('baked-runtime-v1/'+n in out.namelist() for n in runtime.GDS)
    assert result['source_bytes_unchanged'] and sha256(baked)==before==sha256(tmp_path/'saved/source-baked-assets.zip')
    assert set(result['methods_sha256'])==set(runtime.METHODS)
    assert not any(result[k] for k in ('live_prop_physics','engine_executed','animation_quality_approved','release_approved'))
    with pytest.raises(ValueError,match='Fresh'):runtime.package(baked,tmp_path/'saved')


@pytest.mark.parametrize('fault',['actor-end','actor-root','source-end','clock','source-clock','modes','scale','source-root-mode','source-approval','reference','partial'])
def test_rehashed_baked_changes_cannot_change_original_contract(baked,tmp_path,fault):
    def change(files):
        name='composition.json';value=json.loads(files[name])
        if fault=='actor-end':value['actors']['A']['end_policy']='loop'
        elif fault=='actor-root':value['actors']['A']['root_motion']='extracted'
        elif fault=='source-end':value['source_duration_s']-=.1
        elif fault=='clock':value['clock']['bytes_hex']='00'
        elif fault=='source-clock':value['source_clock']=clock_wire(np.array([0.,2.]))
        elif fault=='modes':value['objects']['modes'].clear()
        elif fault=='scale':value['parent_world_transform'][0][0]=2.
        elif fault in ('source-root-mode','source-approval'):
            name='reference/source-game-package.json';value=json.loads(files[name])
            value['root_application_mode' if fault=='source-root-mode' else 'quality_approved']='extracted' if fault=='source-root-mode' else True
        elif fault=='reference':files['reference/animations/A.res']+=b'changed';return
        else:files.pop('reference/animations/A.res');return
        files[name]=json.dumps(value).encode()
    altered=rewrite(baked,tmp_path/'changed.zip',change)
    with pytest.raises((ValueError,KeyError)):runtime.package(altered,tmp_path/'saved')
    assert read(tmp_path/'saved/pipeline.json')['status']=='failed' and not (tmp_path/'saved/baked-runtime.zip').exists()


@pytest.mark.parametrize('fault',['traversal','case-duplicate','undeclared'])
def test_complete_portable_population_required(baked,tmp_path,fault):
    def change(files):
        files[{'traversal':'../outside','case-duplicate':'Objects.glb','undeclared':'extra'}[fault]]=b'unsafe'
    source=rewrite(baked,tmp_path/'changed.zip',change)
    if fault=='undeclared':
        # An unlisted file rejects even when all declared entries still match.
        with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
        m=json.loads(files['package.json']);m['files_sha256'].pop('extra');files['package.json']=json.dumps(m).encode()
        source=tmp_path/'unlisted.zip'
        with zipfile.ZipFile(source,'x') as z:
            for n,v in files.items():z.writestr(n,v)
    with pytest.raises(ValueError):runtime.unpack(source,tmp_path/'extract')
    assert not (tmp_path/'outside').exists()


def test_complete_exact_scene_events_roots_and_boot(baked,tmp_path):
    config,scene,asset,queries,events=context(baked,tmp_path/'assets')
    result=runtime.evaluate(observation(config,scene,asset,queries,events),config,scene,asset,queries,events)
    assert result['scene_playback_verified'] and result['exported_main_scene_verified']
    assert result['samples']==len(queries) and result['callback_observations']==16
    assert max(result['maximum_pose_component_error'].values())<1e-10
    assert not result['animation_quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('fault',['actor','bone','prop','pose','nonfinite','root','delta','clock','frames','event','event-count','boot','envelope','collision','preview','repeat','backward','parent','bind-leak'])
def test_missing_wrong_or_uncontrolled_playback_rejects(baked,tmp_path,fault):
    config,scene,asset,queries,events=context(baked,tmp_path/'assets');value=observation(config,scene,asset,queries,events)
    row=value['frames'][-1];actor=next(iter(row['actors']));bone=next(iter(row['actors'][actor]));prop=next(iter(row['objects']))
    if fault=='actor':row['actors'].pop(actor)
    elif fault=='bone':row['actors'][actor].pop(bone)
    elif fault=='prop':row['objects'].pop(prop)
    elif fault in ('pose','nonfinite','root','delta'):
        group,name=(row['actors'][actor],bone) if fault in ('pose','nonfinite') else (row['root_motion' if fault=='root' else 'root_deltas'],actor)
        m=np.frombuffer(bytes.fromhex(group[name]),dtype='<f8').copy();m[3]+=.02
        if fault=='nonfinite':m[3]=np.nan
        group[name]=m.tobytes().hex()
    elif fault=='clock':row['time_f64le']=np.array([0.],dtype='<f8').tobytes().hex()
    elif fault=='frames':value['frames'].pop()
    elif fault=='event':value['skipped_callbacks'][0]['id']='different'
    elif fault=='event-count':value['boot_callbacks'].pop()
    elif fault=='envelope':value['object_key_envelope_s']+=.001
    elif fault=='collision':value['collision_objects']=1
    else:value[{'boot':'boot_bound','preview':'preview_silent','repeat':'repeat_root_delta_identity','backward':'backward_rejected','parent':'moved_parent_rejected','bind-leak':'no_binding_leaks'}[fault]]=False
    with pytest.raises(ValueError):runtime.evaluate(value,config,scene,asset,queries,events)


@pytest.mark.parametrize('fault',['none','source-during-audit','methods-before-audit'])
def test_audit_snapshot_and_current_methods_bind_before_engine(baked,tmp_path,monkeypatch,fault):
    runtime.package(baked,tmp_path/'saved');source=tmp_path/'saved/baked-runtime.zip'
    if fault=='methods-before-audit':
        def change(files):
            name='baked-runtime-v1/package.json';m=json.loads(files[name]);m['methods_sha256'].pop('baked_scene_runtime.py');files[name]=json.dumps(m).encode()
        source=rewrite(source,tmp_path/'old-methods.zip',change,runtime_package=True)
    engine=tmp_path/'engine.exe';engine.write_bytes(b'Explicit engine double');monkeypatch.setattr(runtime,'ENGINE',engine);monkeypatch.setattr(runtime,'ENGINE_SHA256',sha256(engine))
    called=[]
    def execute(project,script,path,out,log,timeout):
        called.append(script);request=read(path);config,scene,asset,_,events=runtime.configure_bake(project,read(project/'package.json'))
        queries=np.frombuffer(bytes.fromhex(request['clock']['bytes_hex']),dtype='<f8');value=observation(config,scene,asset,queries,events);value['request_sha256']=sha256(path)
        save(out,value);Path(log).write_text('Explicit engine double\n')
        if fault=='source-during-audit':source.write_bytes(source.read_bytes()+b'changed')
        return value
    monkeypatch.setattr(runtime,'engine_run',execute)
    if fault=='none':
        result=runtime.audit(source,tmp_path/'audit');assert result['status']=='complete' and result['source_runtime_zip_sha256']==sha256(tmp_path/'audit/source-baked-runtime.zip')
    else:
        with pytest.raises(ValueError):runtime.audit(source,tmp_path/'audit')
        assert read(tmp_path/'audit/pipeline.json')['status']=='failed'
    assert bool(called)==(fault!='methods-before-audit')
