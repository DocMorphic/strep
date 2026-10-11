"""Generated static GLB fixtures; no model, downloaded assets or engine needed."""
import copy,hashlib,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(1,str(Path(__file__).resolve().parent))
from gltf_tools import append_accessor,write_glb
from static_prop_asset import StaticPropAsset


def fixture():
    document=dict(asset=dict(version='2.0'),nodes=[dict(name='Prop',mesh=0)],scene=0,scenes=[dict(nodes=[0])],
        buffers=[dict(byteLength=0)],bufferViews=[],accessors=[],materials=[dict(name='Original material')])
    binary=bytearray()
    position=append_accessor(document,binary,np.array([[0.,0,0],[1,0,0],[0,1,0]]),'VEC3')
    document['meshes']=[dict(primitives=[dict(attributes=dict(POSITION=position),material=0)])]
    document['buffers'][0]['byteLength']=len(binary)
    return document,bytes(binary)


def test_original_snapshot_and_landmark(tmp_path):
    document,binary=fixture();original=copy.deepcopy(document)
    path=tmp_path/'prop.glb';write_glb(path,document,binary);before=path.read_bytes()
    prop=StaticPropAsset.load(path)
    assert path.read_bytes()==before and document==original
    assert prop.source_sha256==hashlib.sha256(before).hexdigest()
    assert prop.binary==binary and prop.inventory()['source_scale_retained']
    mark=prop.surface_point(0,[.25,.25,.5])
    np.testing.assert_array_equal(mark['position_m'],[.25,.5,0])
    np.testing.assert_array_equal(mark['winding_normal'],[0,0,1])
    assert mark['source_sha256']==prop.source_sha256 and not mark['outward_normal_verified'] and not mark['contact_verified']
    assert all(prop.inventory()[k] is False for k in ('collision_verified','scene_solver_integrated','engine_import_verified','quality_approved','release_approved'))
    with pytest.raises(ValueError):prop.vertices_m[0,0]=1
    with pytest.raises(ValueError):prop.faces[0,0]=1


def test_full_hierarchy_scale_and_shared_mesh_instances():
    document,binary=fixture()
    document['nodes']=[dict(name='Root',translation=[10,20,30],scale=[2,3,4],children=[1,2]),
        dict(mesh=0,translation=[1,0,0]),dict(mesh=0,translation=[-1,0,0])]
    prop=StaticPropAsset(document,binary)
    np.testing.assert_array_equal(prop.vertices_m[:3],[[12,20,30],[14,20,30],[12,23,30]])
    np.testing.assert_array_equal(prop.vertices_m[3:],[[8,20,30],[10,20,30],[8,23,30]])
    np.testing.assert_array_equal(prop.faces,[[0,1,2],[3,4,5]])
    assert [s['node'] for s in prop.surfaces]==[1,2]
    np.testing.assert_array_equal(prop.surface_point(0,[.25,.25,.5])['position_m'],[12.5,21.5,30])


def test_world_shear_from_valid_local_trs_is_retained():
    document,binary=fixture()
    document['nodes']=[dict(scale=[2,3,4],children=[1]),dict(mesh=0,rotation=[0,0,np.sin(np.pi/8),np.cos(np.pi/8)])]
    prop=StaticPropAsset(document,binary)
    c=np.sqrt(.5)
    np.testing.assert_allclose(prop.vertices_m,[[0,0,0],[2*c,3*c,0],[-2*c,3*c,0]],rtol=0,atol=1e-14)


def test_reflection_retained_and_other_scenes_not_combined():
    document,binary=fixture()
    document['nodes']=[dict(mesh=0,scale=[-2,3,1]),dict(mesh=0,translation=[100,0,0])]
    document['scenes'].append(dict(nodes=[1]))
    prop=StaticPropAsset(document,binary)
    assert len(prop.faces)==1 and len(prop.surfaces)==1
    np.testing.assert_array_equal(prop.vertices_m,[[0,0,0],[-2,0,0],[0,3,0]])
    np.testing.assert_array_equal(prop.surface_point(0,[1,0,0])['winding_normal'],[0,0,-1])


@pytest.mark.parametrize('mutation',[
    lambda d:d.update(skins=[dict(joints=[0])]),lambda d:d.update(animations=[dict()]),
    lambda d:d['nodes'][0].update(skin=0),lambda d:d['nodes'][0].update(children=[0]),
    lambda d:d['nodes'][0].update(rotation=[0,0,0,0]),lambda d:d['nodes'][0].update(translation=[float('nan'),0,0]),
    lambda d:d['nodes'][0].update(matrix=np.eye(4).reshape(-1).tolist(),scale=[1,1,1]),
    lambda d:d['nodes'][0].update(scale=[0,1,1]),lambda d:d['meshes'][0]['primitives'][0].update(mode=5),
    lambda d:d['meshes'][0]['primitives'][0].update(targets=[dict(POSITION=0)]),
    lambda d:d['meshes'][0]['primitives'][0]['attributes'].update(JOINTS_0=0),
    lambda d:d['accessors'][0].update(count=True),lambda d:d['accessors'][0].update(count=200001),
    lambda d:d['accessors'][0].update(sparse=dict(count=1)),lambda d:d['scenes'][0].update(nodes=[0,0]),
    lambda d:d['accessors'][0].update(normalized=True),lambda d:d['accessors'][0].update(componentType=5123),
])
def test_rejects_unsupported_or_malformed_geometry(mutation):
    document,binary=fixture();mutation(document)
    with pytest.raises(ValueError):StaticPropAsset(document,binary)


def test_rejects_local_shear_but_accepts_decomposable_matrix():
    document,binary=fixture();matrix=np.eye(4);matrix[0,1]=.2
    document['nodes'][0]['matrix']=matrix.T.reshape(-1).tolist()
    with pytest.raises(ValueError,match='shear'):StaticPropAsset(document,binary)
    matrix[0,1]=0;matrix[0,0]=-2;matrix[0,3]=4
    document['nodes'][0]['matrix']=matrix.T.reshape(-1).tolist()
    np.testing.assert_array_equal(StaticPropAsset(document,binary).vertices_m,[[4,0,0],[2,0,0],[4,1,0]])


def indexed(document,binary,indices):
    binary=bytearray(binary)
    document['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=len(indices)*2))
    binary.extend(np.asarray(indices,dtype='<u2').tobytes())
    document['accessors'].append(dict(bufferView=len(document['bufferViews'])-1,componentType=5123,type='SCALAR',count=len(indices)))
    document['meshes'][0]['primitives'][0]['indices']=len(document['accessors'])-1
    return bytes(binary)


@pytest.mark.parametrize('indices',[[0,1,2],[2,1,0]])
def test_unsigned_index_order_preserved(indices):
    document,binary=fixture();prop=StaticPropAsset(document,indexed(document,binary,indices))
    np.testing.assert_array_equal(prop.faces,[indices])


@pytest.mark.parametrize('indices',[[0,1,3],[0,0,1],[0,1],[0,1,2,0]])
def test_rejects_bad_index_bounds_and_degenerate_triangles(indices):
    document,binary=fixture()
    with pytest.raises(ValueError):StaticPropAsset(document,indexed(document,binary,indices))


@pytest.mark.parametrize('face,bary',[(True,[1,0,0]),(-1,[1,0,0]),(1,[1,0,0]),(0,[True,0,0]),
    (0,[.5,.5,.5]),(0,[-.1,1.1,0]),(0,[float('inf'),0,0]),(0,['1','0','0']),(0,[1,0])])
def test_landmark_rejects_invalid_binding(face,bary):
    prop=StaticPropAsset(*fixture())
    with pytest.raises(ValueError):prop.surface_point(face,bary)


def test_required_extension_and_external_image_rejection(tmp_path):
    for key,value in [('extensionsRequired',['Unknown']),('images',[dict(uri='outside.png')])]:
        document,binary=fixture();document[key]=value
        path=tmp_path/(key+'.glb');write_glb(path,document,binary)
        with pytest.raises(ValueError):StaticPropAsset.load(path)


def test_byte_budget_rejected_before_decode(tmp_path,monkeypatch):
    import static_prop_asset as module
    monkeypatch.setattr(module,'MAX_BYTES',16)
    path=tmp_path/'too-large.glb';path.write_bytes(bytes(17))
    with pytest.raises(ValueError,match='32 MiB'):StaticPropAsset.load(path)
