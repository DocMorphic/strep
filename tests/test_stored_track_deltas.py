from pathlib import Path
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import accessor,append_accessor
from stored_track_deltas import append_track_deltas


def fixture():
    d=dict(nodes=[{},{}],meshes=[{'preserved':'mesh'}],accessors=[],bufferViews=[],animations=[dict(channels=[],samplers=[])],buffers=[{}]);b=bytearray();times=np.arange(3,dtype=np.float32)/30;clock=append_accessor(d,b,times,'SCALAR')
    q=Rotation.from_rotvec([.1,.2,-.3]).as_quat().astype(np.float32);q[3]=np.nextafter(q[3],np.float32(1.));values=np.tile(q,(3,1));output=append_accessor(d,b,values,'VEC4')
    d['animations'][0]['samplers'].append(dict(input=clock,output=output,interpolation='LINEAR'))
    for node in [0,1]:d['animations'][0]['channels'].append(dict(sampler=0,target=dict(node=node,path='rotation')))
    position=append_accessor(d,b,np.tile(np.array([.1,0,0],np.float32),(3,1)),'VEC3');d['animations'][0]['samplers'].append(dict(input=clock,output=position,interpolation='LINEAR'));d['animations'][0]['channels'].append(dict(sampler=1,target=dict(node=0,path='translation')))
    return d,b,times


def edit(path='rotation',delta=None):
    return dict(node=0,path=path,delta=np.zeros((3,3)) if delta is None else delta,protected=np.array([True,False,True]),maximum_norm=.02 if path=='translation' else .1)


def values(d,b,channel):
    a=d['animations'][0];return accessor(d,b,a['samplers'][a['channels'][channel]['sampler']]['output'])


def test_zero_edit_keeps_original_document_and_every_raw_quaternion_component():
    d,b,t=fixture();out,payload,r=append_track_deltas(d,b,0,t,[edit()])
    assert out==d and payload==b and values(out,payload,0).tobytes()==values(d,b,0).tobytes()
    assert r['all_stored_track_bounds_pass'] and r['tracks'][0]['changed_keys']==0


def test_shared_sampler_is_split_without_changing_other_channel_or_original_sampler():
    d,b,t=fixture();delta=np.zeros((3,3));delta[1]=[.03,0,0]
    out,payload,r=append_track_deltas(d,b,0,t,[edit(delta=delta)])
    assert out['animations'][0]['samplers'][:2]==d['animations'][0]['samplers'] and out['animations'][0]['channels'][1:]==d['animations'][0]['channels'][1:]
    assert values(out,payload,1).tobytes()==values(d,b,1).tobytes() and bytes(payload[:len(b)])==bytes(b) and out['meshes']==d['meshes']
    before=Rotation.from_quat(values(d,b,0)[1]);after=Rotation.from_quat(values(out,payload,0)[1]);assert (before.inv()*after).as_rotvec()==pytest.approx(delta[1],abs=1e-7)
    assert r['all_stored_track_bounds_pass']


def test_protected_and_zero_delta_keys_are_byte_exact_and_source_length_is_retained():
    d,b,t=fixture();delta=np.zeros((3,3));delta[1]=[0,.03,0];out,payload,r=append_track_deltas(d,b,0,t,[edit(delta=delta)])
    before=values(d,b,0);after=values(out,payload,0)
    assert before[[0,2]].tobytes()==after[[0,2]].tobytes()
    assert abs(np.linalg.norm(before[1].astype(float))-np.linalg.norm(after[1].astype(float)))<np.finfo(np.float32).eps
    assert r['zero_delta_and_protected_keys_exact'] and r['tracks'][0]['protected_keys']==2


def test_mixed_root_and_rotation_edits_preserve_unrelated_static_metadata():
    d,b,t=fixture();d['extras']={'label':'original'};delta=np.zeros((3,3));delta[1]=[.01,0,0]
    out,payload,r=append_track_deltas(d,b,0,t,[edit(delta=delta),edit('translation',delta)])
    assert len(r['tracks'])==2 and r['all_stored_track_bounds_pass'] and out['extras']==d['extras']
    assert values(out,payload,2)[[0,2]].tobytes()==values(d,b,2)[[0,2]].tobytes()


def test_float32_translation_overshoot_is_reported_without_epsilon_or_clipping():
    d,b,t=fixture();delta=np.zeros((3,3));delta[1]=[.02,0,0];out,payload,r=append_track_deltas(d,b,0,t,[edit('translation',delta)])
    assert not r['all_stored_track_bounds_pass'] and r['tracks'][0]['maximum_stored_norm']>.02 and r['physical_tolerance_added']==0
    assert values(out,payload,2)[1,0]==np.float32(float(values(d,b,2)[1,0])+.02)


def test_input_ownership_and_output_metadata_are_independent():
    d,b,t=fixture();snapshot=copy.deepcopy(d);raw=bytes(b);delta=np.zeros((3,3));delta[1]=[.01,0,0];request=edit(delta=delta)
    out,payload,r=append_track_deltas(d,b,0,t,[request]);out['nodes'][0]['changed']=True;payload[0]=123;r['tracks'][0]['node']=99
    assert d==snapshot and bytes(b)==raw and np.array_equal(request['delta'],delta) and d['nodes'][0]=={}


@pytest.mark.parametrize('fault',['over_budget','protected','shape','bool','complex','nan','protected_type','protected_shape','limit_bool','limit_nan','zero_limit','rotation_alias','duplicate_edit','duplicate_channel','missing_channel','clock','interpolation','source_quaternion','animation_index'])
def test_invalid_complete_track_edits_reject(fault):
    d,b,t=fixture();request=edit();requests=[request]
    if fault=='over_budget':request['delta'][1,0]=.1000000001
    elif fault=='protected':request['delta'][0,0]=.01
    elif fault=='shape':request['delta']=np.zeros((2,3))
    elif fault=='bool':request['delta']=np.zeros((3,3),dtype=bool)
    elif fault=='complex':request['delta']=np.zeros((3,3),dtype=complex)
    elif fault=='nan':request['delta'][1,0]=np.nan
    elif fault=='protected_type':request['protected']=np.zeros(3,dtype=int)
    elif fault=='protected_shape':request['protected']=np.zeros(2,dtype=bool)
    elif fault=='limit_bool':request['maximum_norm']=True
    elif fault=='limit_nan':request['maximum_norm']=float('nan')
    elif fault=='zero_limit':request['maximum_norm']=0
    elif fault=='rotation_alias':request['maximum_norm']=4
    elif fault=='duplicate_edit':requests*=2
    elif fault=='duplicate_channel':d['animations'][0]['channels'].append(copy.deepcopy(d['animations'][0]['channels'][0]))
    elif fault=='missing_channel':request['node']=1;request['path']='translation'
    elif fault=='clock':t=t+np.float32(.01)
    elif fault=='interpolation':d['animations'][0]['samplers'][0]['interpolation']='STEP'
    elif fault=='source_quaternion':
        q=append_accessor(d,b,np.zeros((3,4)),'VEC4');d['animations'][0]['samplers'][0]['output']=q
    with pytest.raises(ValueError):append_track_deltas(d,b,True if fault=='animation_index' else 0,t,requests)
