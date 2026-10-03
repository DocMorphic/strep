"""Model-free corruption/clock/matrix tests; observations are explicit doubles.

Actual saved-resource Godot studies are recorded separately, never inferred here.
"""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_godot_payload import payload
from native_engine_contacts import matrices
from test_native_scene_geometry import closed_fixture
from test_native_scene_engine import mock_actor,serialized
from strep import sha256,read
import audit_native_root_runtime as runtime


def setup(tmp_path):
    source,_,_=closed_fixture(tmp_path);rig=RigAsset.load(source)
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    q=Rotation.from_euler('yxz',[[25,11,-8],[61,-16,29]],degrees=True).as_quat()
    times=append_accessor(doc,binary,np.array([0.,2.]),'SCALAR')
    values=append_accessor(doc,binary,q,'VEC4')
    animation=doc['animations'][0];animation['samplers'].append(dict(input=times,output=values,interpolation='LINEAR'))
    animation['channels'].append(dict(sampler=len(animation['samplers'])-1,target=dict(node=rig.joints[0],path='rotation')))
    write_glb(source,doc,binary);rig=RigAsset.load(source)
    sampler=NativeSupportSampler(rig.document,rig.binary,0)
    times=np.unique(np.concatenate([np.array([0.,1/480,.375,.853725,1.,2.])]+[c[2] for c in sampler.channels]))
    placement=np.eye(4);placement[:3,:3]=Rotation.from_euler('yxz',[-43,7,12],degrees=True).as_matrix();placement[:3,3]=[2.,-.3,-1.]
    actual=mock_actor(rig,sampler,times)
    native=payload(rig,sampler,'');actual['channels']=[dict(path='Skeleton:'+c['bone'],type={'translation':1,'rotation':2,'scale':3}[c['path']],times_s=c['times_s'],values=c['values']) for c in native['channels']]
    root=rig.joints[0];anchor=sampler.sample(0.)[root]
    poses=placement@np.array([sampler.sample(t)[rig.joints] for t in times])
    transforms=np.array([sampler.sample(t)[root]@np.linalg.inv(anchor) for t in times])
    deltas=np.concatenate([np.eye(4)[None],np.linalg.inv(transforms[:-1])@transforms[1:]])
    names=[rig.document['nodes'][n]['name'] for n in rig.joints];order=[names.index(n) for n in actual['bone_names']]
    for mode in ('embedded','extracted'):
        frames=[]
        for i,t in enumerate(times):
            frames.append(dict(time_s=float(t),bones=[serialized(v) for v in poses[i,order]],root_motion=serialized(transforms[i]),
                actor_world=serialized(placement@transforms[i] if mode=='extracted' else placement),root_delta=serialized(deltas[i]),
                root_in_actor=serialized(anchor if mode=='extracted' else sampler.sample(t)[root])))
        actual[mode]=frames
    ids=[0,len(times)-1,len(times)//2,len(times)-1,0,0]
    actual['preview']=[copy.deepcopy(actual['extracted'][i]) for i in ids]
    for frame in actual['preview']:frame['root_delta']=serialized(np.eye(4))
    actual.update(invalid_rejected=True,malformed_bindings_rejected=True,malformed_bindings=8,engine=dict(string='test-double'))
    return source,rig,sampler,times,placement,actual


def test_noncommuting_root_placement_complete_bone_reordering_and_skin(tmp_path):
    _,rig,sampler,times,placement,actual=setup(tmp_path)
    sampler,times,placement=runtime.validate(rig,0,rig.joints[0],times,placement)
    result,arrays=runtime.evaluate(rig,sampler,times,placement,actual)
    assert result['sampled_runtime_conditions_pass'] and result['samples']==len(times)
    assert result['bones']==len(rig.joints) and result['vertices']==8
    assert result['maximum_mode_skin_position_difference_m']==0.
    assert result['imported_skin']['source_vertex_coverage'] and not result['imported_skin']['raw_imported_weights_renormalized']
    wrong=np.linalg.inv(sampler.sample(0)[rig.joints[0]])@sampler.sample(2)[rig.joints[0]]
    assert abs(wrong-arrays['extracted_root'][-1]).max()>.1
    assert all(a.dtype==np.dtype('<f8') for a in arrays.values())


@pytest.mark.parametrize('fault',['key-missing','clock-first','clock-end','clock-repeat','clock-nan','index-bool','root-bool','partial-root','static-mesh','placement-scale','placement-nan','placement-row'])
def test_incomplete_clock_partial_skeleton_and_unsupported_placement_reject(tmp_path,fault):
    _,rig,_,times,placement,_=setup(tmp_path);index=0;root=rig.joints[0]
    if fault=='key-missing':times=times[times!=sampler_key(rig)]
    if fault=='clock-first':times=times[1:]
    if fault=='clock-end':times=np.r_[times,3.]
    if fault=='clock-repeat':times=np.r_[times,times[-1]]
    if fault=='clock-nan':times[1]=np.nan
    if fault=='index-bool':index=False
    if fault=='root-bool':root=False
    if fault=='partial-root':root=rig.joints[1]
    if fault=='static-mesh':rig.primitives[0]['joints']=None
    if fault=='placement-scale':placement[0,0]*=2
    if fault=='placement-nan':placement[0,0]=np.nan
    if fault=='placement-row':placement[3,0]=1
    with pytest.raises(ValueError):runtime.validate(rig,index,root,times,placement)


def sampler_key(rig):
    keys=NativeSupportSampler(rig.document,rig.binary,0).channels[0][2]
    return float(keys[1]) # Interior original key, not a duration endpoint.


@pytest.mark.parametrize('fault',['double-root','wrong-side','root-drift','root-delta','embedded-placement','preview-leak','key-value','invalid-accepted','binding-accepted'])
def test_numerical_failures_are_recorded_without_dropping_samples(tmp_path,fault):
    _,rig,sampler,times,placement,actual=setup(tmp_path)
    if fault=='double-root':
        root=matrices([f['root_motion'] for f in actual['embedded']])
        bones=matrices([f['bones'] for f in actual['extracted']])
        doubled=placement@root[:,None]@np.linalg.inv(placement)@bones
        for frame,values in zip(actual['extracted'],doubled):frame['bones']=[serialized(v) for v in values]
    if fault=='wrong-side':actual['extracted'][-1]['actor_world']=serialized(placement@np.linalg.inv(sampler.sample(0)[rig.joints[0]])@sampler.sample(2)[rig.joints[0]])
    if fault=='root-drift':actual['extracted'][-1]['root_in_actor'][3][0]+=.01
    if fault=='root-delta':actual['extracted'][-1]['root_delta'][3][0]+=.01
    if fault=='embedded-placement':actual['embedded'][-1]['actor_world'][3][0]+=.01
    if fault=='preview-leak':actual['preview'][-1]['bones'][0][3][0]+=.01
    if fault=='key-value':actual['channels'][0]['values'][0][0]+=.01
    if fault=='invalid-accepted':actual['invalid_rejected']=False
    if fault=='binding-accepted':actual['malformed_bindings_rejected']=False
    result,arrays=runtime.evaluate(rig,sampler,times,placement,actual)
    assert not result['sampled_runtime_conditions_pass']
    assert len(arrays['extracted_world'])==len(times)


@pytest.mark.parametrize('fault',['bone-lost','clock-lost','clock-changed','nan-bone','native-key-time','native-key-count','native-channel-lost','native-bone','topology-lost','duration'])
def test_corrupted_populations_reject(tmp_path,fault):
    _,rig,sampler,times,placement,actual=setup(tmp_path)
    if fault=='bone-lost':actual['bone_names'].pop()
    if fault=='clock-lost':actual['extracted'].pop()
    if fault=='clock-changed':actual['extracted'][1]['time_s']+=.01
    if fault=='nan-bone':actual['extracted'][1]['bones'][0][0][0]=np.nan
    if fault=='native-key-time':actual['channels'][0]['times_s'][0]+=.00001
    if fault=='native-key-count':actual['channels'][0]['times_s'].pop()
    if fault=='native-channel-lost':actual['channels'].pop()
    if fault=='native-bone':actual['channels'][0]['path']='Skeleton:wrong'
    if fault=='topology-lost':actual['meshes'][0]['indices']=actual['meshes'][0]['indices'][3:]
    if fault=='duration':actual['duration_s']+=1
    with pytest.raises(ValueError):runtime.evaluate(rig,sampler,times,placement,actual)


def test_wrapper_snapshots_binds_and_preserves_failed_numerical_evidence(tmp_path,monkeypatch):
    source,rig,_,times,placement,actual=setup(tmp_path)
    resource=tmp_path/'saved.res';resource.write_bytes(b'test double resource');engine=tmp_path/'godot.exe';engine.write_bytes(b'test double engine')
    source_hash=sha256(source);resource_hash=sha256(resource)
    actual['extracted'][-1]['bones'][0][3][0]+=.03
    def fake(command,**kwargs):
        from strep import save
        save(command[-1],actual);return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runtime.subprocess,'run',fake)
    out=tmp_path/'output';result=runtime.run(source,resource,0,rig.joints[0],times,out,placement=placement,engine=engine)
    assert result['status']=='complete' and not result['sampled_runtime_conditions_pass']
    assert not result['quality_approved'] and not result['physics_verified'] and not result['release_approved']
    assert result['source_bytes_unchanged'] and result['arrays_roundtrip_exact']
    assert sha256(source)==source_hash and sha256(resource)==resource_hash
    assert sha256(out/'character.glb')==source_hash and sha256(out/'animation.res')==resource_hash
    with pytest.raises(ValueError,match='Fresh'):runtime.run(source,resource,0,rig.joints[0],times,out,engine=engine)


def test_actual_engine_failure_is_preserved_and_retry_does_not_replace_it(tmp_path,monkeypatch):
    source,rig,_,times,_,_=setup(tmp_path);resource=tmp_path/'saved.res';resource.write_bytes(b'resource');engine=tmp_path/'godot.exe';engine.write_bytes(b'engine')
    monkeypatch.setattr(runtime.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=2))
    out=tmp_path/'failed'
    with pytest.raises(ValueError,match='Actual native root'):runtime.run(source,resource,0,rig.joints[0],times,out,engine=engine)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()
    before=sha256(out/'pipeline.json')
    with pytest.raises(ValueError,match='Fresh'):runtime.run(source,resource,0,rig.joints[0],times,out,engine=engine)
    assert sha256(out/'pipeline.json')==before
