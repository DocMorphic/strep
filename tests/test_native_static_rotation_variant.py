"""Separate static-joint variants: exact old payloads and measured pose drift."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support import fixture
from gltf_tools import write_glb
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_static_rotation_variant import run,SCHEMA
from strep import save,sha256


def request(tmp_path,precision=False):
    source,rig,_,_=fixture(tmp_path)
    if precision:
        doc=copy.deepcopy(rig.document)
        doc['nodes'][0]['rotation']=Rotation.from_euler('xyz',[.057,.131,-.093]).as_quat().tolist()
        write_glb(source,doc,rig.binary)
    value=dict(schema=SCHEMA,source=dict(path=source.name,sha256=sha256(source),animation_index=0),nodes=[0],
        clock_from=dict(node=0,path='translation'),sample_times_s=[0.,.853725,2.],
        limits=dict(matrix_error_max=1e-7,vertex_error_max_m=1e-7),label='explicit static rotation',acknowledge_float32_pose_drift=True)
    path=tmp_path/'prepare.json';save(path,value);return path,value


@pytest.mark.parametrize('precision',[False,True])
def test_original_library_and_channels_preserved_with_independent_skin_replay(tmp_path,precision):
    path,value=request(tmp_path,precision);digest=sha256(tmp_path/'source.glb');out=tmp_path/'variant';result=run(path,out)
    assert result['status']=='complete' and result['sampled_fidelity_pass'] and result['original_selected']
    assert not result['quality_approved'] and not result['release_approved']
    assert sha256(tmp_path/'source.glb')==digest and result['candidate']['animation_index']==1
    old=RigAsset.load(tmp_path/'source.glb');new=RigAsset.load(out/'character.glb')
    assert new.document['animations'][:-1]==old.document['animations'] and new.binary[:len(old.binary)]==old.binary
    a=NativeSupportSampler(old.document,old.binary,0);b=NativeSupportSampler(new.document,new.binary,1)
    for key in ('nodes','skins','meshes','scenes'):assert new.document[key]==old.document[key]
    for channel in a.channels:
        match=next(c for c in b.channels if c[:2]==channel[:2])
        for x,y in zip(channel[2:4],match[2:4]):np.testing.assert_array_equal(x,y)
        assert channel[4]==match[4]
    with np.load(out/'observations.npz',allow_pickle=False) as z:
        times=z['times_s'];mat=[];skin=[]
        for i,t in enumerate(times):
            worlds=a.sample(float(t));other=b.sample(float(t))
            np.testing.assert_array_equal(z['source_worlds'][i],worlds);np.testing.assert_array_equal(z['variant_worlds'][i],other)
            mat.append(np.abs(worlds-other).max());skin.append(np.linalg.norm(old.vertices(worlds)-new.vertices(other),axis=1).max())
        np.testing.assert_array_equal(z['matrix_errors'],mat);np.testing.assert_array_equal(z['vertex_errors_m'],skin)
        for c in a.channels:
            assert set(c[2].astype(float))<=set(times) and set((c[2][:-1].astype(float)+c[2][1:].astype(float))/2)<=set(times)
        assert .853725 in times and set(np.arange(241)/120)<=set(times)
    assert result['maximum_matrix_error']==max(mat) and result['maximum_vertex_error_m']==max(skin)
    if precision:
        assert max(mat)>0 and max(skin)>0 and not result['sampled_world_bytes_equal'] and not result['sampled_skin_bytes_equal']
    else:assert result['sampled_world_bytes_equal'] and result['sampled_skin_bytes_equal']
    with pytest.raises(ValueError,match='Fresh immutable'):run(path,out)


def test_exceeding_declared_fidelity_retains_unapproved_result(tmp_path):
    path,value=request(tmp_path,True);value['limits']=dict(matrix_error_max=1e-12,vertex_error_max_m=1e-12);save(path,value)
    result=run(path,tmp_path/'variant')
    assert not result['sampled_fidelity_pass'] and result['original_selected'] and not result['quality_approved']


@pytest.mark.parametrize('fault',['pin','index-bool','existing','duplicate','node-bool','matrix','clock','samples','ack','limit-bool','label','extra'])
def test_invalid_preparation_rejects_before_creating_output(tmp_path,fault):
    path,value=request(tmp_path)
    if fault=='pin':value['source']['sha256']='0'*64
    elif fault=='index-bool':value['source']['animation_index']=True
    elif fault=='existing':value['nodes']=[1]
    elif fault=='duplicate':value['nodes']=[0,0]
    elif fault=='node-bool':value['nodes']=[False]
    elif fault=='matrix':
        source=tmp_path/'source.glb';rig=RigAsset.load(source);doc=copy.deepcopy(rig.document)
        doc['nodes'][0].pop('translation');doc['nodes'][0]['matrix']=np.eye(4).T.reshape(-1).tolist()
        write_glb(source,doc,rig.binary);value['source']['sha256']=sha256(source)
    elif fault=='clock':value['clock_from']['node']=5
    elif fault=='samples':value['sample_times_s']=[0.,2.,2.]
    elif fault=='ack':value['acknowledge_float32_pose_drift']=False
    elif fault=='limit-bool':value['limits']['matrix_error_max']=True
    elif fault=='label':value['label']=' '
    elif fault=='extra':value['auto_approve']=True
    save(path,value);out=tmp_path/'variant'
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()
