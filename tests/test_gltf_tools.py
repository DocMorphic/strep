import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gltf_tools import accessor, append_accessor, write_glb, read_glb, global_matrices, skin_vertices


def test_glb_roundtrip_and_strided_accessor(tmp_path):
    document={'asset':{'version':'2.0'},'bufferViews':[],'accessors':[]}
    binary=bytearray()
    index=append_accessor(document,binary,np.array([[1,2,3],[4,5,6]]),'VEC3')
    append_accessor(document,binary,np.array([0,.1,.2]),'SCALAR')
    path=tmp_path/'sample.glb'
    write_glb(path,document,binary)
    doc,raw=read_glb(path)
    np.testing.assert_array_equal(accessor(doc,raw,index),[[1,2,3],[4,5,6]])
    interleaved=np.array([[1,2,3,99],[4,5,6,88]],dtype='<f4').tobytes()
    doc['bufferViews'][0].update(byteStride=16,byteLength=32)
    np.testing.assert_array_equal(accessor(doc,interleaved,0),[[1,2,3],[4,5,6]])


def test_skinning_uses_column_major_inverse_bind_and_world_joint_transform():
    bind=np.eye(4);bind[0,3]=-2
    vertices=np.array([[2,1,0]],dtype='<f4')
    joints=np.zeros((1,4),dtype='<u2')
    weights=np.array([[1,0,0,0]],dtype='<f4')
    arrays=[vertices.tobytes(),joints.tobytes(),weights.tobytes(),bind.T.astype('<f4').tobytes()]
    views=[];raw=b''
    for array in arrays:
        views.append({'buffer':0,'byteOffset':len(raw),'byteLength':len(array)});raw+=array
    doc={'nodes':[{'translation':[5,0,0]},{'skin':0,'mesh':0}],
        'skins':[{'joints':[0],'inverseBindMatrices':3}],
        'meshes':[{'primitives':[{'attributes':{'POSITION':0,'JOINTS_0':1,'WEIGHTS_0':2}}]}],
        'bufferViews':views,'accessors':[{'bufferView':i,'componentType':5123 if i==1 else 5126,'count':1,'type':kind} for i,kind in enumerate(['VEC3','VEC4','VEC4','MAT4'])]}
    result=skin_vertices(doc,raw,global_matrices(doc),mesh_node=1)
    np.testing.assert_allclose(result,[[5,1,0]])
