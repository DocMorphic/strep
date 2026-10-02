"""Synthetic skin/pose checks; no browser, model or human quality claims."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_candidate_preview import native_world,source_offsets,export_candidate
from build_soma_preview import make_preview
from gltf_tools import write_glb,read_glb,accessor,sample_animation


def native_fixture(folder):
    names=['Joint'+str(i) for i in range(77)]
    parents=[-1]+[(j-1 if j%5 else 0) for j in range(1,77)]
    offsets=np.zeros((77,3));offsets[1:,1]=.04
    local=np.tile(np.eye(3,dtype=np.float32),(6,77,1,1))
    local[:,0]=Rotation.from_euler('y',np.arange(6)*.05).as_matrix()
    roots=np.zeros((6,3),dtype=np.float32);roots[:,1]=1.;roots[:,0]=np.arange(6)*.02
    world=native_world(local,roots,offsets,parents)
    source=dict(local_rot_mats=local,root_positions=roots,posed_joints=world[:,:,:3,3].astype(np.float32),
                global_rot_mats=world[:,:,:3,:3].astype(np.float32),foot_contacts=np.zeros((6,6),dtype=np.float32))
    bind=native_world(np.tile(np.eye(3),(1,77,1,1)),np.zeros((1,3)),offsets,parents)[0]
    skin=dict(bind_rig_transform=bind,rig_joint_names=np.array(names),rig_joint_connections=np.array([[p,j] for j,p in enumerate(parents) if p>=0]),
              bind_vertices=np.array([[0,0,0],[.1,0,0],[0,.1,0]],dtype=np.float32),faces=np.array([[0,1,2]]),
              lbs_indices=np.tile(np.arange(1,9),(3,1)),lbs_weights=np.tile(np.array([.05,.1,.15,.2,.05,.1,.15,.2],dtype=np.float32),(3,1)))
    doc,binary,_,_=make_preview(skin,source,np.zeros(3),repeat=False)
    path=folder/'original.glb';write_glb(path,doc,binary)
    return names,parents,source,path,skin


def test_candidate_preserves_skin_and_serializes_changed_root_and_joint_geometry(tmp_path):
    names,parents,source,path,skin=native_fixture(tmp_path)
    original={k:v[2:5] for k,v in source.items()}
    local=original['local_rot_mats'].copy();local[:,4]=Rotation.from_euler('x',[.1,.2,.3]).as_matrix()
    roots=original['root_positions'].copy();roots[:,0]+=.15
    output=tmp_path/'candidate.glb';result=export_candidate(path,original,local,roots,names,parents,output)
    doc,binary=read_glb(output);attrs=doc['meshes'][0]['primitives'][0]['attributes']
    assert result['all_eight_influences_preserved'] and result['max_skin_error_m']<1e-5
    weights=np.concatenate([accessor(doc,binary,attrs['WEIGHTS_'+str(i)]) for i in range(2)],axis=1)
    np.testing.assert_array_equal(weights,skin['lbs_weights'])
    for frame in range(3):np.testing.assert_allclose(sample_animation(doc,binary,0,frame)[1,:3,3],roots[frame],atol=1e-7)
    expected=native_world(local,roots,source_offsets(original,parents),parents)
    np.testing.assert_allclose(sample_animation(doc,binary,0,2)[1:,:3,:3],expected[2,:,:3,:3],atol=1e-6)
    assert accessor(doc,binary,doc['animations'][0]['samplers'][0]['input']).tolist()==pytest.approx([0,1/30,2/30])
    assert result['quality_approved'] is False


@pytest.mark.parametrize('fault',['pose','rotation','names','hierarchy','weights','external','nonfinite_skin'])
def test_incompatible_or_inconsistent_inputs_rejected(tmp_path,fault):
    names,parents,source,path,_=native_fixture(tmp_path)
    if fault=='pose':source['posed_joints'][1,4,0]+=.2
    if fault=='rotation':source['local_rot_mats'][1,0,0,0]=2
    if fault=='names':names[2]='Different'
    if fault=='hierarchy':parents[4]=5
    if fault in ('weights','external','nonfinite_skin'):
        doc,binary=read_glb(path)
        if fault=='weights':del doc['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_1']
        elif fault=='external':doc['images']=[{'uri':'foreign.png'}]
        else:
            entry=doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['POSITION']]
            view=doc['bufferViews'][entry['bufferView']];binary=bytearray(binary)
            import struct
            struct.pack_into('<f',binary,view.get('byteOffset',0)+entry.get('byteOffset',0),float('nan'))
        write_glb(path,doc,binary)
    with pytest.raises((ValueError,KeyError)):
        export_candidate(path,source,source['local_rot_mats'],source['root_positions'],names,parents,tmp_path/'bad.glb')
