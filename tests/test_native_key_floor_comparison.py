"""Complete shared-clock comparison keeps negative and transferred failures."""
from pathlib import Path
import copy,sys
import numpy as np,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_key_floor_comparison import compare,run
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from native_support_clock import NativeSupportSampler
from test_native_scene_geometry import closed_fixture
from strep import sha256


def fixture(tmp_path):
    source,_,_=closed_fixture(tmp_path);return source,RigAsset.load(source)


def test_complete_vertices_and_shared_clock_match_direct_skin_queries(tmp_path):
    _,rig=fixture(tmp_path);report,arrays=compare(rig,rig,0,0,1.)
    reader=NativeSupportSampler(rig.document,rig.binary,0)
    expected=[rig.vertices(reader.sample(float(t)))[:,1].min() for t in arrays['source_times']]
    np.testing.assert_array_equal(arrays['source_min_y_m'],expected)
    np.testing.assert_array_equal(arrays['target_min_y_m'],expected)
    assert report['source']['vertices']==8 and report['source']['faces']==12
    assert report['maximum_target_minus_scaled_source_depth_m']==0
    assert not report['quality_approved'] and not report['release_approved']


def test_target_penetration_and_scale_are_not_hidden_by_source_pass(tmp_path):
    _,rig=fixture(tmp_path);target=copy.deepcopy(rig)
    target.primitives[0]['positions'][:,1]-=1.
    report,arrays=compare(rig,target,0,0,1.5)
    assert report['target']['floor_failed_keys']>report['source']['floor_failed_keys']
    assert report['maximum_target_minus_scaled_source_depth_m']>.1
    np.testing.assert_allclose(arrays['target_min_y_m'],arrays['source_min_y_m']-1,atol=1e-14,rtol=0)


@pytest.mark.parametrize('scale',[True,0,-1,float('nan'),float('inf'),101])
def test_invalid_scale_rejects(tmp_path,scale):
    _,rig=fixture(tmp_path)
    with pytest.raises(ValueError):compare(rig,rig,0,0,scale)


def test_changed_native_clock_or_implicit_animation_selection_rejects(tmp_path):
    _,rig=fixture(tmp_path);other=copy.deepcopy(rig);data=bytearray(other.binary)
    animation=other.document['animations'][0];key=animation['samplers'][0]['input']
    from rig_asset import array
    times=array(other.document,other.binary,key).reshape(-1).copy();times[-1]+=.125
    replacement=append_accessor(other.document,data,times,'SCALAR')
    for sampler in animation['samplers']:
        if sampler['input']==key:sampler['input']=replacement
    other.binary=bytes(data)
    with pytest.raises(ValueError,match='clock'):compare(rig,other,0,0,1.)
    with pytest.raises(ValueError,match='index'):compare(rig,rig,False,0,1.)


def test_run_retains_input_bytes_and_bound_observation_archive(tmp_path,monkeypatch):
    import action_worker_lock
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    source,_=fixture(tmp_path);before=sha256(source);output=tmp_path/'comparison'
    result=run(source,source,output,source_index=0,target_index=0,scale=1.)
    assert result['schema']=='strep-native-key-floor-comparison-v1'
    assert sha256(source)==before and result['source_bindings_sha256'][str(source.resolve())]==before
    assert result['observations_sha256']==sha256(output/'observations.npz')
    assert result['original_selected'] and not result['training_admitted']
    with pytest.raises(FileExistsError):run(source,source,output,source_index=0,target_index=0,scale=1.)
