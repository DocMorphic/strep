from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_pose_key_export import replace_keys
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from gltf_tools import write_glb
from test_native_support import fixture


def edit(source,current,path,changes,prefix):
    return replace_keys(source,current,root=0,rotations=[1,2,3],edits=changes,preserve_through=prefix,output=path)


def test_repeated_exports_preserve_prefix_shared_sampler_and_buffer_size(tmp_path):
    path,source,original,_=fixture(tmp_path);raw=path.read_bytes();x=np.zeros(12);x[1]=.02;x[6]=.15
    first=tmp_path/'first.glb';edit(source,source,first,{1:x},0);current=RigAsset.load(first);before=NativeSupportSampler(current.document,current.binary,0)
    y=x.copy();y[1]=.03;y[9]=-.1
    second=tmp_path/'second.glb';result=edit(source,current,second,{2:y},1);final=RigAsset.load(second);after=NativeSupportSampler(final.document,final.binary,0)
    assert path.read_bytes()==raw and final.binary[:len(source.binary)]==source.binary
    assert len(final.binary)==len(current.binary)
    for a,b in zip(before.channels,after.channels):
        np.testing.assert_array_equal(a[3][[0,1,*range(3,11)]],b[3][[0,1,*range(3,11)]])
        assert a[2].tobytes()==b[2].tobytes()
    for t in np.linspace(0,float(before.channels[0][2][1]),9):np.testing.assert_array_equal(before.sample(t),after.sample(t))
    assert result['preserved_through']==1 and result['unchanged_key_values_verified']
    assert not np.allclose(original.sample(float(original.channels[0][2][2])),after.sample(float(original.channels[0][2][2])))


@pytest.mark.parametrize('frame,prefix',[(0,0),(1,1),(-1,-1),(11,0),(True,0)])
def test_bad_keys_cannot_modify_preserved_prefix(tmp_path,frame,prefix):
    _,source,_,_=fixture(tmp_path);out=tmp_path/'bad.glb'
    with pytest.raises(ValueError):edit(source,source,out,{frame:np.zeros(12)},prefix)
    assert not out.exists()


@pytest.mark.parametrize('fault',['node','mode','clock','unexpected_channel'])
def test_incompatible_current_clip_rejected(tmp_path,fault):
    _,source,_,_=fixture(tmp_path);doc=copy.deepcopy(source.document);binary=bytearray(source.binary)
    if fault=='node':doc['nodes'][5]['translation'][0]+=.1
    elif fault=='mode':doc['animations'][0]['samplers'][0]['interpolation']='STEP'
    elif fault=='clock':doc['animations'][0]['samplers'][0]['input']=doc['animations'][0]['samplers'][1]['output']
    else:doc['animations'][0]['channels'].append(copy.deepcopy(doc['animations'][0]['channels'][0]))
    altered=tmp_path/'altered.glb';write_glb(altered,doc,binary);out=tmp_path/'bad.glb'
    with pytest.raises(ValueError):edit(source,RigAsset.load(altered),out,{2:np.zeros(12)},0)
    assert not out.exists()


def test_existing_output_and_nonfinite_controls_rejected(tmp_path):
    _,source,_,_=fixture(tmp_path);out=tmp_path/'keep.glb';out.write_bytes(b'keep')
    with pytest.raises(FileExistsError):edit(source,source,out,{1:np.zeros(12)},0)
    assert out.read_bytes()==b'keep'
    with pytest.raises(ValueError):edit(source,source,tmp_path/'bad.glb',{1:np.full(12,np.nan)},0)
