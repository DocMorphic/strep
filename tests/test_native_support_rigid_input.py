"""Explicit preparation never mutates the source or hides real scaling."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_support import fixture
import native_support_rigid_input as prep
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from gltf_tools import write_glb,append_accessor
from strep import sha256,read


def source(tmp_path,scale):
    _,rig,_,_=fixture(tmp_path);doc=copy.deepcopy(rig.document)
    doc['nodes'][0]['scale']=scale
    path=tmp_path/'scaled.glb';write_glb(path,doc,rig.binary)
    return path,doc,rig.binary


def test_roundoff_preparation_is_explicit_bound_and_preserves_all_motion_bytes(tmp_path,monkeypatch):
    monkeypatch.setattr(prep,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    path,doc,binary=source(tmp_path,[1.0000004,.9999999,1.]);digest=sha256(path)
    output=tmp_path/'reports'/'rigid';r=prep.prepare(path,output)
    assert r['status']=='complete' and r['changes']==1 and not r['quality_approved']
    assert sha256(path)==digest==sha256(output/'input.glb')
    out=RigAsset.load(output/'prepared.glb')
    assert out.binary==binary and out.document['animations']==doc['animations']
    assert out.document['meshes']==doc['meshes'] and out.document['skins']==doc['skins']
    assert out.document['nodes'][0]['scale']==[1.,1.,1.]
    assert 0<r['maximum_vertex_distance_m']<prep.GEOMETRY_CHANGE_LIMIT_M
    reader=NativeSupportSampler(out.document,out.binary,0)
    for t in (.0,.173,.999,1.937,2.):
        w=reader.sample(t)[:,:3,:3]
        np.testing.assert_allclose(w.transpose(0,2,1)@w,np.eye(3)[None].repeat(len(w),axis=0),atol=1e-7,rtol=0)
    q=read(output/'request.json')
    for name,h in q['implementation'].items():assert sha256(output/'implementation'/name)==h
    for name,h in r['outputs'].items():assert sha256(output/name)==h


@pytest.mark.parametrize('fault',['static','animated','matrix','geometry'])
def test_unsupported_scaling_or_excess_geometry_change_is_rejected_without_output(tmp_path,monkeypatch,fault):
    monkeypatch.setattr(prep,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    path,doc,binary=source(tmp_path,[1.0000004,1.,1.]);binary=bytearray(binary)
    if fault=='static':doc['nodes'][0]['scale']=[1.000001,1,1]
    if fault=='matrix':
        del doc['nodes'][5]['translation']
        m=np.eye(4);m[0,0]=1.0000004;doc['nodes'][5]['matrix']=m.T.ravel().tolist()
    if fault=='animated':
        values=append_accessor(doc,binary,[[1.0000004,1,1]]*11,'VEC3')
        a=doc['animations'][0];i=len(a['samplers']);a['samplers'].append(dict(input=a['samplers'][0]['input'],output=values,interpolation='LINEAR'))
        a['channels'].append(dict(sampler=i,target=dict(node=0,path='scale')))
    if fault=='geometry':
        doc['meshes'][0]['primitives'][0]['attributes']['POSITION']=append_accessor(doc,binary,[[1000,.19,0],[1001,.19,0],[1000,.19,.1]],'VEC3')
    write_glb(path,doc,binary);digest=sha256(path);out=tmp_path/'reports'/'rigid'
    with pytest.raises(ValueError):prep.prepare(path,out)
    assert not out.exists() and sha256(path)==digest


def test_existing_output_cannot_be_overwritten(tmp_path,monkeypatch):
    monkeypatch.setattr(prep,'ROOT',tmp_path);out=tmp_path/'reports'/'old';out.mkdir(parents=True)
    with pytest.raises(ValueError,match='Fresh'):prep.prepare(tmp_path/'missing.glb',out)


def test_implementation_is_bound_before_sampling_and_checked_before_output(tmp_path,monkeypatch):
    monkeypatch.setattr(prep,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    path,_,_=source(tmp_path,[1.0000004,1.,1.]);calls=[]
    def changed(p):
        if Path(p)==prep.SOURCE_DIR/'native_support_rigid_input.py':
            calls.append(p)
            if len(calls)>1:return '0'*64
        return sha256(p)
    monkeypatch.setattr(prep,'sha256',changed);out=tmp_path/'reports'/'rigid'
    with pytest.raises(ValueError,match='implementation changed'):prep.prepare(path,out)
    assert not out.exists() and len(calls)==2
