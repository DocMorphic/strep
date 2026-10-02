"""Detect between-key penetration and require it at actual export acceptance."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support import fixture
from test_rig_mesh_trajectory import make
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from native_support_clock import NativeSupportSampler
from rig_subframe_floor import inspect
from strep import read,save,sha256


def curved_fixture(tmp_path,duration=1/30,mode='LINEAR'):
    _,rig,_,_=fixture(tmp_path);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    keys=append_accessor(doc,binary,[0.,duration],'SCALAR')
    rotations=Rotation.from_euler('z',[-60,60],degrees=True).as_quat()
    output=append_accessor(doc,binary,rotations,'VEC4')
    doc['animations']=[dict(channels=[dict(sampler=0,target=dict(node=3,path='rotation'))],
        samplers=[dict(input=keys,output=output,interpolation=mode)])]
    positions=append_accessor(doc,binary,[[-.2,-.01,0],[-.201,-.011,.001],[-.199,-.01,.002]],'VEC3')
    doc['meshes'][0]['primitives'][0]['attributes']['POSITION']=positions
    path=tmp_path/'curved.glb';write_glb(path,doc,binary)
    return path


def test_between_key_rotation_dip_fails_while_both_keys_pass(tmp_path):
    path=curved_fixture(tmp_path);digest=sha256(path)
    rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    for t in sampler.channels[0][2]:assert rig.vertices(sampler.sample(float(t)))[:,1].min()>0
    result=inspect(path,.005)
    assert not result['sampled_floor_passed'] and result['failed_samples']>0
    assert result['floor_depth_max_m']==pytest.approx(.011,abs=2e-8)
    assert result['worst_floor']['time_s']==float(sampler.channels[0][2][-1])/2
    assert result['glb_sha256']==digest==sha256(path) and not result['quality_approved']


def test_step_interpolation_does_not_invent_a_rotating_dip(tmp_path):
    path=curved_fixture(tmp_path,mode='STEP');result=inspect(path,.005)
    assert result['sampled_floor_passed'] and result['failed_samples']==0


def test_long_export_inspection_preserves_default_import_duration_limit(tmp_path):
    path=curved_fixture(tmp_path,31,mode='STEP');rig=RigAsset.load(path)
    with pytest.raises(ValueError,match='duration'):AnimationSampler(rig.document,rig.binary,0)
    result=inspect(path,.005,hz=1)
    assert result['duration_s']==31 and result['sampled_floor_passed']


@pytest.mark.parametrize('hz',[0,True,1.5,1001])
def test_sampling_frequency_is_exact_and_bounded(tmp_path,hz):
    with pytest.raises(ValueError,match='frequency'):inspect(curved_fixture(tmp_path),.005,hz)


@pytest.mark.parametrize('cap',[0,True,float('nan'),float('inf'),-.005])
def test_floor_cap_is_positive_finite_and_not_boolean(tmp_path,cap):
    with pytest.raises(ValueError,match='floor depth'):inspect(curved_fixture(tmp_path),cap)


@pytest.mark.parametrize('limit',[0,True,float('nan'),float('inf'),-1])
def test_sampler_duration_override_is_explicit_and_valid(tmp_path,limit):
    path=curved_fixture(tmp_path);rig=RigAsset.load(path)
    with pytest.raises(ValueError,match='duration limit'):AnimationSampler(rig.document,rig.binary,0,max_duration_s=limit)


def test_multiple_animation_floor_check_is_rejected(tmp_path):
    path=curved_fixture(tmp_path);rig=RigAsset.load(path)
    rig.document['animations'].append(copy.deepcopy(rig.document['animations'][0]))
    write_glb(path,rig.document,rig.binary)
    with pytest.raises(ValueError,match='One animation'):inspect(path,.005)


def test_actual_pipeline_retains_input_on_subframe_floor_failure(tmp_path):
    import rig_mesh_trajectory as module
    source=curved_fixture(tmp_path);rig=RigAsset.load(source)
    binary=bytearray(rig.binary);sampler=rig.document['animations'][0]['samplers'][0]
    sampler['input']=append_accessor(rig.document,binary,[0.,1/30,2/30],'SCALAR')
    sampler['output']=append_accessor(rig.document,binary,Rotation.from_euler('z',[-60,60,60],degrees=True).as_quat(),'VEC4')
    write_glb(source,rig.document,binary);rig=RigAsset.load(source)
    _,_,_,_,spec=make(tmp_path);spec['glb_sha256']=sha256(source);spec['frames']=3
    spec['contacts'][0].update(start_frame=0,end_frame_exclusive=1,
        target_position_m=rig.vertices(NativeSupportSampler(rig.document,rig.binary,0).sample(0)).mean(axis=0).tolist())
    draft=tmp_path/'draft.json';save(draft,spec)
    result=module.run(source,draft,tmp_path/'fit',spacing=2,max_iterations=5)
    keys=read(tmp_path/'fit/independent-inspection.json')
    assert keys['floor_frames_failed']==keys['failed_intervals']==0
    assert result['solver']['solver_success']
    assert result['retained_input'] and result['selected_file']=='original.glb'
    assert read(tmp_path/'fit/audit.json')['flags']==['decoded_subframe_floor_screen_failed']
    assert read(tmp_path/'fit/request.json')['decoded_floor_sampling_hz']==120
    assert sha256(tmp_path/'fit/subframe-floor-inspection.json')==result['outputs']['subframe-floor-inspection.json']
    assert 'rig_subframe_floor.py' in read(tmp_path/'fit/request.json')['implementation']


def test_source_mutation_during_inspection_is_rejected(tmp_path,monkeypatch):
    import rig_subframe_floor as module
    path=curved_fixture(tmp_path);original=module.RigAsset.vertices;changed=[]
    def mutate(self,world):
        result=original(self,world)
        if not changed:path.write_bytes(path.read_bytes()+b'\0');changed.append(True)
        return result
    monkeypatch.setattr(module.RigAsset,'vertices',mutate)
    with pytest.raises(ValueError,match='source changed'):module.inspect(path,.005)
