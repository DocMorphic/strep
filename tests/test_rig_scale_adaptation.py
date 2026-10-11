"""Generated scales, hierarchy, bind shape and static-instance preservation."""
import copy,sys,json,struct
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import append_accessor,global_matrices,write_glb
from rig_asset import RigAsset,array,read_asset
from rig_scale_adaptation import normalize,adapt_file


def fixture(*,scale=(100,100,100),static=False,extra_influences=False):
    nodes=[dict(name='Root',scale=list(scale),translation=[.2,.1,-.3],children=[1,3]),
        dict(name='Hip',translation=[0,.01,0],rotation=Rotation.from_euler('y',.2).as_quat().tolist(),children=[2]),
        dict(name='Child',translation=[0,.008,.001],scale=[1.00005,1,.99999]),
        dict(name='Mesh',mesh=0,skin=0,translation=[99,99,99])]
    doc=dict(asset=dict(version='2.0',extras=dict(original='keep')),nodes=nodes,skins=[dict(joints=[1,2])],
        scenes=[dict(nodes=[0])],scene=0,buffers=[dict(byteLength=0,extras=dict(original='buffer'))],
        bufferViews=[],accessors=[],materials=[dict(name='Original material')])
    binary=bytearray();positions=np.array([[.1,.2,0],[.2,.3,.1],[-.1,.3,.2]],dtype='<f4')
    attrs=dict(POSITION=append_accessor(doc,binary,positions,'VEC3'))
    def integer(values):
        while len(binary)%4:binary.append(0)
        raw=np.asarray(values,dtype='<u2').tobytes();start=len(binary);binary.extend(raw)
        view=len(doc['bufferViews']);doc['bufferViews'].append(dict(buffer=0,byteOffset=start,byteLength=len(raw)))
        index=len(doc['accessors']);doc['accessors'].append(dict(bufferView=view,componentType=5123,count=3,type='VEC4'))
        return index
    attrs['JOINTS_0']=integer([[0,1,0,1]]*3)
    attrs['WEIGHTS_0']=append_accessor(doc,binary,[[.1,.2,.3,.4]]*3,'VEC4')
    if extra_influences:
        attrs['WEIGHTS_0']=append_accessor(doc,binary,[[.05,.1,.15,.2]]*3,'VEC4')
        attrs['JOINTS_1']=integer([[1,0,1,0]]*3)
        attrs['WEIGHTS_1']=append_accessor(doc,binary,[[.2,.15,.1,.05]]*3,'VEC4')
    doc['meshes']=[dict(name='Original mesh',primitives=[dict(attributes=attrs,material=0)])]
    world=global_matrices(doc);inverse=np.linalg.inv(world[[1,2]])
    inverse[:,0,3]+=.013  # Nontrivial bind shape; not assumed inverse(rest).
    doc['skins'][0]['inverseBindMatrices']=append_accessor(doc,binary,inverse.transpose(0,2,1).reshape(2,16),'MAT4')
    if static:
        static_attrs=dict(POSITION=attrs['POSITION'],
            NORMAL=append_accessor(doc,binary,[[0,0,1]]*3,'VEC3'),
            TANGENT=append_accessor(doc,binary,[[1,0,0,1]]*3,'VEC4'))
        doc['meshes'].append(dict(name='Shared static accessory',primitives=[dict(attributes=static_attrs,material=0)]))
        nodes[0]['children'] += [4,5]
        nodes.extend([dict(name='AccessoryA',mesh=1,translation=[.01,0,0]),
            dict(name='AccessoryB',mesh=1,rotation=Rotation.from_euler('y',.3).as_quat().tolist())])
    doc['buffers'][0]['byteLength']=len(binary)
    return doc,bytes(binary)


@pytest.mark.parametrize('scale',[(100,100,100),(2,3,4),(.02,.03,.04),(1,1,1)])
def test_scaled_reference_and_influence_matrices_preserved(scale):
    doc,binary=fixture(scale=scale);before=copy.deepcopy(doc)
    output,data,record=normalize(doc,binary);rig=RigAsset(output,data)
    old=global_matrices(doc);inverse=array(doc,binary,doc['skins'][0]['inverseBindMatrices'])
    np.testing.assert_allclose(old[[1,2]]@inverse,rig.reference[[1,2]]@rig.inverse,atol=1e-6,rtol=0)
    np.testing.assert_allclose(old[:,:3,3],rig.reference[:,:3,3],atol=1e-12,rtol=0)
    assert doc==before and data[:len(binary)]==binary and output['meshes']==doc['meshes']
    assert output['accessors'][:len(doc['accessors'])]==doc['accessors']
    assert output['bufferViews'][:len(doc['bufferViews'])]==doc['bufferViews']
    assert output['materials']==doc['materials'] and output['asset']==doc['asset']
    assert record['reference_shape_verified'] and not record['source_deformation_model_preserved']
    assert not record['future_motion_quality_verified'] and not record['engine_verified']


def test_eight_influences_and_missing_inverse_binds():
    doc,binary=fixture(scale=(2,3,4),extra_influences=True)
    doc['skins'][0].pop('inverseBindMatrices')
    output,data,record=normalize(doc,binary)
    assert RigAsset(output,data).primitives[0]['weights'].shape==(3,8)
    assert record['maximum_reference_vertex_error_m']<=1e-5


def test_shared_static_instances_and_surface_basis_preserved():
    doc,binary=fixture(scale=(2,3,4),static=True);output,data,record=normalize(doc,binary)
    old=global_matrices(doc);rig=RigAsset(output,data)
    for node in (4,5):
        primitive=doc['meshes'][1]['primitives'][0]
        source=array(doc,binary,primitive['attributes']['POSITION'])
        expected=(old[node]@np.column_stack([source,np.ones(3)]).T).T[:,:3]
        derivative=output['meshes'][output['nodes'][node]['mesh']]['primitives'][0]
        target=array(output,data,derivative['attributes']['POSITION'])
        actual=(rig.reference[node]@np.column_stack([target,np.ones(3)]).T).T[:,:3]
        np.testing.assert_allclose(actual,expected,atol=1e-6,rtol=0)
        normal=array(output,data,derivative['attributes']['NORMAL'])
        tangent=array(output,data,derivative['attributes']['TANGENT'])
        np.testing.assert_allclose(np.linalg.norm(normal,axis=1),1,atol=1e-6)
        np.testing.assert_allclose((normal*tangent[:,:3]).sum(axis=1),0,atol=1e-6)
        np.testing.assert_array_equal(tangent[:,3],[1,1,1])
    assert output['nodes'][4]['mesh']!=output['nodes'][5]['mesh']
    assert output['meshes'][:len(doc['meshes'])]==doc['meshes']
    assert record['vertices']==9


def test_serialized_derivative_preserves_original_and_metadata(tmp_path):
    doc,binary=fixture();source=tmp_path/'source.glb';write_glb(source,doc,binary)
    # The fixture writer drops buffer metadata; add it to this separately tested input.
    raw=source.read_bytes();original_doc,original_binary=read_asset(source)
    original_doc['buffers'][0]['extras']={'original':'buffer'}
    encoded=json.dumps(original_doc).encode();encoded+=b' '*(-len(encoded)%4)
    padded=original_binary+b'\0'*(-len(original_binary)%4)
    raw=struct.pack('<III',0x46546c67,2,28+len(encoded)+len(padded))
    raw+=struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(padded),0x004e4942)+padded
    source.write_bytes(raw);result=adapt_file(source,tmp_path/'adapted')
    assert source.read_bytes()==raw==(tmp_path/'adapted/source.glb').read_bytes()
    rig=RigAsset.load(tmp_path/'adapted/character.glb')
    assert rig.document['buffers'][0]['extras']=={'original':'buffer'}
    assert result['status']=='complete' and result['reference_shape_verified']
    with pytest.raises(FileExistsError):adapt_file(source,tmp_path/'adapted')


@pytest.mark.parametrize('change',[
    lambda d:d.update(animations=[dict(channels=[],samplers=[])]),
    lambda d:d['nodes'][0].update(scale=[0,1,1]),
    lambda d:d['nodes'][0].update(scale=[-1,1,1]),
    lambda d:d['nodes'][0].update(rotation=[0,0,0,2]),
    lambda d:d['nodes'][0].update(scale=[True,True,True]),
    lambda d:d['skins'].append(copy.deepcopy(d['skins'][0])),
    lambda d:d['meshes'][0]['primitives'][0].update(targets=[{}]),
    lambda d:d['nodes'][0].update(children=[1,3,1]),
])
def test_unsupported_or_malformed_input_rejected(change):
    doc,binary=fixture();change(doc)
    with pytest.raises(ValueError):normalize(doc,binary)


@pytest.mark.parametrize('limit',[False,0,-1,float('nan'),float('inf'),'1e-5'])
def test_invalid_reference_limits_rejected(limit):
    with pytest.raises(ValueError):normalize(*fixture(),maximum_reference_error_m=limit)


def test_local_shear_is_rejected():
    doc,binary=fixture();doc['nodes'][0].pop('scale')
    shear=np.eye(4);shear[0,1]=.2;doc['nodes'][0].pop('translation');doc['nodes'][0]['matrix']=shear.T.reshape(-1).tolist()
    with pytest.raises(ValueError,match='shear'):normalize(doc,binary)


def test_rejected_derivative_retains_original_and_failed_receipt(tmp_path):
    doc,binary=fixture();doc['animations']=[dict(channels=[],samplers=[])]
    path=tmp_path/'source.glb';write_glb(path,doc,binary);before=path.read_bytes()
    with pytest.raises(ValueError):adapt_file(path,tmp_path/'failed')
    assert (tmp_path/'failed/source.glb').read_bytes()==before==path.read_bytes()
    import json
    assert json.loads((tmp_path/'failed/result.json').read_bytes())['status']=='failed'
