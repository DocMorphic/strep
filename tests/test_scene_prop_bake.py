"""Model-free bake contracts; synthetic traces/engine doubles are not physics proof."""
import copy,json,sys,subprocess
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import scene_prop_bake as bake
from scene_prop_runtime import compile_request,package
from native_object_asset import ObjectAsset,export
from gltf_tools import read_glb
from object_geometry import Geometry
from strep import read,save,sha256
from test_native_scene_runtime import fixture
from test_scene_prop_runtime import request_for


def request(source):
    parent=np.eye(4);parent[1,3]=2
    return dict(schema='strep-scene-prop-bake-request-v1',source_runtime_zip_sha256=sha256(source),parent_world_transform=parent.tolist(),floor=dict(enabled=False,height_m=0.,friction=.6,restitution=0.))


def setup(tmp_path):
    folder,source,_,config,scene,_,events,_=fixture(tmp_path);r=request_for(source,scene)
    p,rot=scene.object_poses('item',np.array([0.]));t=np.eye(4);t[:3,3]=p[0];t[:3,:3]=rot[0]
    a=scene.actors['A'];place=np.eye(4);place[:3,3]=a['placement'][0];place[:3,:3]=a['placement'][1]
    node=r['grips']['left']['joint_node'];r['grips']['left']['prop_offsets']['item']=(np.linalg.inv(place@a['sampler'].sample(0)[node])@t).tolist()
    r['commands'][0]['event_id']='marker:initial';r['commands'][1]['event_id']='marker:fraction'
    compiled=compile_request(r,config,scene,events,sha256(source))
    clock=bake.physical_clock(scene.duration,120);initial=np.asarray(compiled['props']['item']['initial_pose']);poses=[]
    for time in clock:
        value=initial.copy();elapsed=max(0.,time-clock[1]);value[1,3]-=4.905*elapsed**2
        value[:3,:3]=Rotation.from_euler('y',elapsed*.7).as_matrix()@initial[:3,:3];poses.append(value)
    return folder,source,scene,events,r,compiled,clock,np.asarray(poses)


def trace(scene,events,compiled,clock,poses,digest):
    """Known analytic synthetic free-flight/rotation, not actual engine dynamics."""
    native=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')
    encoded=lambda matrix:np.asarray(matrix,dtype='<f8').tobytes().hex()
    marker=[dict(id=e['id'],source_time_f64le=bake.bits(native[e['sample_index']]),pose_time_f64le=bake.bits(native[e['sample_index']])) for e in events['events'] if e['runtime_dispatch_allowed']]
    actions=[]
    for g in compiled['ownership']['groups']:
        t=native[g['sample_index']];tick=int(np.searchsorted(clock,t))
        for tr in g['transitions']:
            actions.append(dict(object=tr['object'],before=tr['before'],after=tr['after'],event_ids=list(dict.fromkeys(c['event_id'] for c in tr['changes'])),tick=tick,source_time_f64le=bake.bits(t),application_time_f64le=bake.bits(clock[tick]),pose_f64le=encoded(poses[0]),last_grip_released=tr['last_grip_released']))
    rows=[]
    for i,t in enumerate(clock):
        rows.append(dict(tick=i,physics_time_f64le=bake.bits(t),source_time_f64le=bake.bits(min(t,scene.duration)),pose_time_f64le=bake.bits(min(t,scene.duration)),actor_ids=list(scene.actors),
            members={'item':['left'] if i==0 else []},modes={'item':'held' if i==0 else 'released'},props={'item':dict(pose_f64le=encoded(poses[i]),contacts=[],mode='held' if i==0 else 'released',direct_state_class='JoltPhysicsDirectBodyState3D',step_s=1/120,collision_layer=0 if i==0 else 1,collision_mask=0 if i==0 else 1)}))
    return dict(schema='strep-scene-prop-capture-v1',request_sha256=digest,physics_fps=120,faults=[],records=rows,actions=actions,events=marker,engine={'fixture':'Explicit synthetic double'})


def test_capture_preserves_quantization_failure_and_disabled_collision_screen(tmp_path):
    _,source,scene,events,_,compiled,clock,poses=setup(tmp_path);r=request(source)
    actual=trace(scene,events,compiled,clock,poses,'a'*64);audit,values=bake.audit_capture(actual,compiled,scene,events,r,'a'*64)
    assert not audit['exact_physical_event_timing_pass'] and audit['maximum_application_delay_s']==clock[1]-1/480
    assert audit['floor_sampled_screen_pass'] is None and not audit['continuous_collision_certified']
    assert audit['samples']==241 and np.array_equal(values['item'],poses)
    r['floor']['enabled']=True;audit,_=bake.audit_capture(actual,compiled,scene,events,r,'a'*64)
    assert not audit['floor_sampled_screen_pass'] and audit['floor_sampled_depth_max_m']['item']>10


@pytest.mark.parametrize('fault',['clock','rounded','pose-clock','actor','missing-prop','member','mode','mask-bool','backend','step','nonfinite','scale','event','action-time','extra-action','fault'])
def test_malformed_or_incomplete_capture_never_validates(tmp_path,fault):
    _,source,scene,events,_,compiled,clock,poses=setup(tmp_path);r=request(source);v=trace(scene,events,compiled,clock,poses,'a'*64)
    if fault=='clock':v['records'].pop()
    elif fault=='rounded':v['events'][1]['source_time_f64le']=bake.bits(float('0.00208333333333333'))
    elif fault=='pose-clock':v['records'][1]['pose_time_f64le']=bake.bits(0.)
    elif fault=='actor':v['records'][0]['actor_ids']=['A','A']
    elif fault=='missing-prop':v['records'][0]['props'].clear()
    elif fault=='member':v['records'][0]['members']['item']=[]
    elif fault=='mode':v['records'][1]['props']['item']['mode']='held'
    elif fault=='mask-bool':v['records'][1]['props']['item']['collision_mask']=True
    elif fault=='backend':v['records'][0]['props']['item']['direct_state_class']='GodotPhysicsDirectBodyState3D'
    elif fault=='step':v['records'][0]['props']['item']['step_s']=1/60
    elif fault in ('nonfinite','scale'):
        p=poses[0].copy();p[0,0]=float('nan') if fault=='nonfinite' else 2.;v['records'][0]['props']['item']['pose_f64le']=p.astype('<f8').tobytes().hex()
    elif fault=='event':v['events'].pop()
    elif fault=='action-time':v['actions'][1]['application_time_f64le']=v['actions'][1]['source_time_f64le']
    elif fault=='extra-action':v['actions'].append(v['actions'][0])
    else:v['faults']=['Explicit fixture failure']
    with pytest.raises((ValueError,KeyError,TypeError)):bake.audit_capture(v,compiled,scene,events,r,'a'*64)


@pytest.mark.parametrize('shape',['box','sphere','cylinder'])
def test_mesh_prefix_authored_channels_and_nonuniform_interpolation_survive(tmp_path,shape):
    folder,_,scene,_,_,_,clock,poses=setup(tmp_path)
    scene.objects['item']['geometry']=Geometry.parse(dict(schema='strep-object-geometry-v1',shape=shape,**({'size_m':[1.6,.4,.8]} if shape=='box' else {'radius_m':.8} if shape=='sphere' else {'radius_m':.8,'height_m':.4})))
    scene.objects['authored']=copy.deepcopy(scene.objects['item']);scene.objects['authored']['positions'][:,2]+=3
    src=tmp_path/'objects-source.glb';export(scene,src);before=sha256(src);original=ObjectAsset(src)
    asset,audit=bake.export_bake(src,tmp_path/'objects-baked.glb',clock,{'item':poses,'authored':poses},{'item':'grip-physics','authored':'authored'})
    old_doc,old_binary=read_glb(src);new_doc,new_binary=read_glb(tmp_path/'objects-baked.glb')
    assert new_binary[:len(old_binary)]==old_binary and new_doc['meshes']==old_doc['meshes'] and sha256(src)==before
    assert [c for c in asset.channels if c['object']=='authored']==[c for c in original.channels if c['object']=='authored']
    query=np.array([1/480,.317,.7995,1.88888,2.]);expected=bake.interpolated(clock,poses,query);actual=asset.object_poses('item',query)
    assert max(float(abs(a-b).max()) for a,b in zip(expected,actual))<bake.POSE_LIMIT
    assert audit['original_mesh_payload_unchanged'] and not audit['quality_approved']


def test_full_cli_pipeline_with_explicit_engine_double_preserves_sources_and_no_overwrite(tmp_path,monkeypatch):
    folder,source,scene,events,r,compiled,clock,poses=setup(tmp_path)
    import action_worker_lock
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    runtime_request=tmp_path/'runtime-request.json';save(runtime_request,r);pack=package(source,runtime_request,tmp_path/'runtime')
    runtime=tmp_path/'runtime/prop-runtime-assets.zip';author=request(runtime);author_path=tmp_path/'bake-request.json';save(author_path,author)
    engine=tmp_path/'engine.exe';engine.write_bytes(b'Explicit engine test double')
    monkeypatch.setattr(bake,'ENGINE',engine);monkeypatch.setattr(bake,'ENGINE_SHA256',sha256(engine))
    before=(runtime.read_bytes(),author_path.read_bytes())
    def execute(project,script,path,out,log,timeout):
        payload=read(path)
        if script==bake.CAPTURE or script.endswith('/'+bake.CAPTURE):v=trace(scene,events,compiled,clock,poses,sha256(path))
        else:
            asset=ObjectAsset(payload['asset_path']);times=payload['payload']['sample_times_s'];v=dict(import_bake_fps=payload['import_bake_fps'])
            for mode in ('default-import','native-authoring'):
                v[mode]={}
                for n in asset.objects:
                    p,r=asset.object_poses(n,times);q=Rotation.from_matrix(r).as_quat();v[mode][n]=[dict(time_f64le=bake.bits(t),translation_m=x.tolist(),rotation_xyzw=y.tolist()) for t,x,y in zip(times,p,q)]
            Path(payload['resource_path']).write_bytes(b'Explicit resource double')
        save(out,v);Path(log).write_text('Explicit engine double, not execution\n');return v
    monkeypatch.setattr(bake,'engine_run',execute);output=tmp_path/'baked';result=bake.bake(runtime,author_path,output)
    assert result['status']=='complete' and result['original_selected'] and not result['studio_selection_changed']
    assert not result['exact_physical_event_timing_pass'] and not result['animation_quality_approved']
    assert before==(runtime.read_bytes(),author_path.read_bytes())
    assert read(output/'assets/composition.json')['actors']['A']['end_policy']=='hold-original-end'
    assert sha256(output/'assets/reference/actors/0.glb')==sha256(folder/'actors/0.glb')
    with pytest.raises(ValueError,match='Fresh'):bake.bake(runtime,author_path,output)


def test_timestep_budget_non_grid_end_and_invalid_bake_request(tmp_path):
    clock=bake.physical_clock(2.001,120);assert clock[-1]>=2.001 and clock[-2]<2.001 and len(clock)==242
    for duration,rate in [(0,120),(float('nan'),120),(1000,120),(2,True),(2,30)]:
        with pytest.raises(ValueError):bake.physical_clock(duration,rate)
    p=tmp_path/'source';p.write_bytes(b'fixture');r=request(p)
    for update in ({'source_runtime_zip_sha256':'0'*64},{'schema':'other'},{'infer_hands':True},{'floor':{'enabled':True}}):
        with pytest.raises((ValueError,KeyError)):bake.validate_request({**r,**update},sha256(p))


def test_owned_engine_timeout_stops_child_tree_and_retains_terminal_receipt(tmp_path,monkeypatch):
    class Process:
        pid=12345;returncode=None
        def wait(self,timeout=None):
            if timeout is not None:raise subprocess.TimeoutExpired('Explicit process double',timeout)
            self.returncode=-9
        def poll(self):return self.returncode
    calls=[];monkeypatch.setattr(bake.subprocess,'Popen',lambda *a,**kw:Process());monkeypatch.setattr(bake,'kill_tree',calls.append)
    with pytest.raises(subprocess.TimeoutExpired):bake.engine_run(tmp_path,'capture.gd',tmp_path/'request.json',tmp_path/'out.json',tmp_path/'engine.log',1)
    assert calls==[12345] and read(tmp_path/'engine.log.terminal.json')['exit_code']==-9


@pytest.mark.parametrize('fault',['population','clock','position','rotation'])
def test_engine_import_rejects_missing_samples_inexact_clocks_and_nonfinite_poses(tmp_path,fault):
    folder,_,_,_,_,_,_,_=setup(tmp_path);asset=ObjectAsset(folder/'objects.glb');times=np.array([0.,1/480,2.])
    p,r=asset.object_poses('item',times);q=Rotation.from_matrix(r).as_quat()
    rows=[dict(time_f64le=bake.bits(t),translation_m=x.tolist(),rotation_xyzw=y.tolist()) for t,x,y in zip(times,p,q)]
    actual={mode:{'item':copy.deepcopy(rows)} for mode in ('default-import','native-authoring')}
    assert all(v<1e-12 for v in bake.import_errors(actual,asset,times).values())
    target=actual['native-authoring']['item']
    if fault=='population':target.pop()
    elif fault=='clock':target[1]['time_f64le']=bake.bits(float('0.00208333333333333'))
    elif fault=='position':target[1]['translation_m'][0]=float('nan')
    else:target[1]['rotation_xyzw']=[0.,0.,0.,0.]
    with pytest.raises(ValueError):bake.import_errors(actual,asset,times)


def test_baked_midpoint_grip_and_floor_failures_remain_separate_from_export_fidelity(tmp_path):
    folder,source,scene,events,_,compiled,clock,poses=setup(tmp_path);r=request(source)
    # The stored track reproduces the supplied displacement accurately, while
    # its midpoint fails the held-joint condition. Export is no grasp approval.
    query=np.array([0.,1/240,1/120]);initial=poses[0].copy();displaced=initial.copy();displaced[0,3]+=.2
    captured=np.repeat(initial[None],len(clock),axis=0);captured[1]=displaced
    asset,storage=bake.export_bake(folder/'objects.glb',tmp_path/'bake.glb',clock,{'item':captured},{'item':'grip-physics'})
    applied=[dict(object='item',after=['left'],application_time_f64le=bake.bits(0.))]
    audit=bake.audit_baked_motion(asset,query,compiled,scene,applied,r)
    assert storage['decoded_tracks']['item']['passed'] and not audit['held_grip_sampled_conditions_pass']
    assert audit['held_grip_position_error_max_m']>.19 and audit['floor_sampled_screen_pass'] is None
    r['floor'].update(enabled=True,height_m=10.)
    assert not bake.audit_baked_motion(asset,query,compiled,scene,applied,r)['floor_sampled_screen_pass']
    assert not audit['anatomical_contact_verified'] and not audit['release_approved']
