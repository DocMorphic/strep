"""Checked weight grids, adversarial Float32 loading and preserved animation payloads."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from skin_weight_grid import condition
from native_skin_export import run,unchanged,write_export
from test_native_support import fixture
from rig_asset import RigAsset
from strep import read,sha256


def encoded(values):
    x=np.asarray(values,np.float32);total=np.zeros(len(x),np.float32)
    for slot in range(x.shape[1]):total=np.add(total,x[:,slot],dtype=np.float32)
    normalized=np.divide(x,total[:,None],dtype=np.float32)
    return np.floor(normalized*np.float32(65535)).astype(np.int64)


@pytest.mark.parametrize('width',[4,8])
def test_random_and_sparse_weights_preserve_zeros_and_checked_integer_sums(width):
    rng=np.random.default_rng(42);weights=rng.uniform(0,1,(10000,width));weights[::3,::2]=0
    values,report=condition(weights);codes=encoded(values)
    assert np.max(abs(65535-codes.sum(1)))<=1
    assert np.all(values[weights==0]==0) and float(abs(values-weights/weights.sum(1)[:,None]).max())<2/65535
    repeat,_=condition(weights);np.testing.assert_array_equal(values,repeat)
    assert report['encoding_checked'] and values.dtype==np.float32


def test_one_hot_and_equal_weights_remain_valid_without_losing_influences():
    values,report=condition(np.r_[np.eye(4),np.ones((1,4))])
    np.testing.assert_array_equal(values[:4],np.eye(4));assert report['influences']==4
    assert (encoded(values).sum(1)>=65534).all()


@pytest.mark.parametrize('bad',[[],[[0,0,0,0]],[[1,2,3]],[[1,2,3,-1]],[[1,2,3,float('nan')]],[[1,2,3,float('inf')]]])
def test_invalid_weight_populations_reject(bad):
    with pytest.raises(ValueError):condition(bad)


def test_export_changes_only_weight_references_and_retains_all_old_binary_and_metadata(tmp_path):
    source,rig,reader,_=fixture(tmp_path)
    document=copy.deepcopy(rig.document);document['buffers'][0]['name']='retained payload'
    document['buffers'][0]['extras']={'retain':True};write_export(source,document,rig.binary)
    rig=RigAsset.load(source);before=sha256(source);result=run(source,tmp_path/'job')
    output=RigAsset.load(tmp_path/'job/proposal.glb');unchanged(rig,output)
    assert output.document['animations']==rig.document['animations'] and output.document['skins']==rig.document['skins']
    assert output.binary[:len(rig.binary)]==rig.binary
    assert output.document['buffers'][0]['name']=='retained payload'
    assert sha256(source)==before==sha256(tmp_path/'job/original.glb')
    assert result['source_payload_prefix_preserved'] and result['non_weight_scene_data_preserved']
    assert result['original_selected'] and not result['animation_changed']
    assert not any(result[k] for k in ('skin_fidelity_verified','engine_playback_verified','quality_approved','training_admitted','release_approved'))


@pytest.mark.parametrize('fault',['binary','animation','position','buffer'])
def test_non_weight_changes_cannot_pass_preservation_check(tmp_path,fault):
    source,rig,reader,_=fixture(tmp_path);run(source,tmp_path/'job');output=RigAsset.load(tmp_path/'job/proposal.glb')
    if fault=='binary':output.binary=b'X'+output.binary[1:]
    if fault=='animation':output.document['animations'][0]['name']='changed'
    if fault=='position':output.document['meshes'][0]['primitives'][0]['attributes']['POSITION']=0
    if fault=='buffer':output.document['buffers'][0]['name']='changed'
    with pytest.raises(ValueError):unchanged(rig,output)


def test_method_archive_mutation_keeps_failed_job_visible(tmp_path,monkeypatch):
    import native_skin_export as export
    source,rig,reader,_=fixture(tmp_path);writer=export.write_export;out=tmp_path/'job'
    def changed(*args):
        writer(*args);path=out/'implementation/native_skin_export.py';path.write_bytes(path.read_bytes()+b'\n')
    monkeypatch.setattr(export,'write_export',changed)
    with pytest.raises(ValueError):run(source,out)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()
