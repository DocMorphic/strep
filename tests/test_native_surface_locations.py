import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_asset import RigAsset
from native_self_surface import audit
from native_scene_geometry import faces_for
from native_surface_locations import locate


def fixture(different_weights=False):
    # Two independent primitive triangles cross away from an identical corner.
    a=np.array([[-2.,-1.,0.],[2.,-1.,0.],[0.,2.,0.]])
    b=np.array([a[0],[0.,0.,-1.],[0.,0.,1.]])
    rig=RigAsset.__new__(RigAsset)
    rig.document=dict(nodes=[dict(mesh=0),dict(name='same label'),dict(name='same label')],meshes=[dict(primitives=[{},{}])])
    rig.binary=b'';rig.joints=[1,2];rig.inverse=np.repeat(np.eye(4)[None],2,axis=0)
    rig.primitives=[dict(node=0,primitive=i,positions=points,joints=np.full((3,1),i if different_weights else 0),weights=np.ones((3,1))) for i,points in enumerate([a,b])]
    pose=np.repeat(np.eye(4)[None],3,axis=0);faces,_=faces_for(rig)
    report=audit(rig.vertices(pose),faces)
    return rig,pose,report


def test_all_flags_located_and_duplicate_attributes_never_exempt_crossing():
    rig,pose,report=fixture();before=copy.deepcopy(report);v=rig.vertices(pose).copy()
    result=locate(rig,pose,report)
    assert result['record_count']==1 and result['records'][0]['kind']=='proper_crossing'
    assert result['records'][0]['duplicate_loaded_attribute_pairs']==[[0,3]]
    assert result['triangles']['0']['primitive']==0 and result['triangles']['1']['primitive']==1
    assert result['triangles']['0']['dominant_joint']==1
    assert len(result['vertices_world_m'])==6 and result['regions']==[dict(kind='proper_crossing',joint_nodes=[1,1],records=1)]
    assert result['flags_exempted']==0 and not result['self_collision_free_certified']
    assert report==before and np.array_equal(v,rig.vertices(pose))


def test_same_position_with_different_skin_function_is_not_duplicate_or_same_named_joint():
    rig,pose,report=fixture(True);r=locate(rig,pose,report)
    assert r['records'][0]['duplicate_loaded_attribute_pairs']==[]
    assert r['regions'][0]['joint_nodes']==[1,2]


@pytest.mark.parametrize('fault',['hash','count','partial','approval','duplicate','boolean','outside','kind','nan','shared'])
def test_invalid_or_mismatched_evidence_rejected(fault):
    rig,pose,r=fixture()
    if fault=='hash':r['faces_sha256']='0'*64
    elif fault=='count':r['vertices']+=1
    elif fault=='partial':r['complete_triangle_population']=False
    elif fault=='approval':r['self_collision_free_certified']=True
    elif fault=='duplicate':r['records']*=2
    elif fault=='boolean':r['records'][0]['left_triangle']=False
    elif fault=='outside':r['records'][0]['right_triangle']=22
    elif fault=='kind':r['records'][0]['kind']='safe'
    elif fault=='nan':r['records'][0]['overlap_length_m']=float('nan')
    else:r['records'][0]['shared_vertices']=1
    with pytest.raises(ValueError):locate(rig,pose,r)


def test_degenerate_face_locations_and_pose_population_are_not_omitted():
    rig,pose,_=fixture();rig.primitives[0]['positions'][:]=[0,0,0]
    r=audit(rig.vertices(pose),faces_for(rig)[0]);result=locate(rig,pose,r)
    assert result['degenerate_faces']==[0] and '0' in result['triangles']
    with pytest.raises(ValueError):locate(rig,pose[:2],r)
    pose[0,0,0]=float('nan')
    with pytest.raises(ValueError):locate(rig,pose,r)


def test_ambiguous_coplanar_overlap_keeps_unknown_length_and_all_duplicates():
    rig,pose,_=fixture();rig.primitives[1]['positions']=rig.primitives[0]['positions'].copy()
    r=audit(rig.vertices(pose),faces_for(rig)[0]);result=locate(rig,pose,r)
    assert result['records'][0]['kind']=='coplanar_or_near_parallel_overlap'
    assert result['records'][0]['overlap_length_m'] is None
    assert len(result['records'][0]['duplicate_loaded_attribute_pairs'])==3
    assert result['flags_exempted']==0
