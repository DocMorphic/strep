"""Real FK target proportions, incompatible branches and protected pose caps."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_pose_scaffold import propose,branch_rotation
from bounded_pose_ik import world_matrices,hierarchy_order


def fixture():
    local=np.tile(np.eye(4),(4,1,1));local[1,0,3]=2;local[2,0,3]=3;local[3,0,3]=1
    return local,np.array([-1,0,1,2]),dict(root=0,elbow=1,wrist=2)


def test_reference_lengths_are_adapted_to_the_target_not_copied():
    local,parents,mapping=fixture();points=dict(root=[0,0,0],elbow=[1,0,0],wrist=[1,1,0])
    changed,world,r=propose(local,parents,mapping,points,{0:90,1:90,2:90})
    np.testing.assert_allclose(world[:3,:3,3],[[0,0,0],[2,0,0],[2,3,0]],atol=1e-12)
    assert r['maximum_role_edge_length_change_m']<1e-12 and r['status']=='proposed'
    assert not r['contact_verified'] and not r['temporal_verified'] and not r['quality_approved']
    np.testing.assert_array_equal(changed[:,:3,3],local[:,:3,3]);np.testing.assert_array_equal(changed[3],local[3])


def test_source_relative_caps_hold_even_after_ancestor_changes():
    local,parents,mapping=fixture();points=dict(root=[0,0,0],elbow=[0,1,0],wrist=[-1,1,0])
    changed,world,r=propose(local,parents,mapping,points,{0:20,1:10,2:15})
    angles=np.rad2deg(Rotation.from_matrix(local[:3,:3,:3].swapaxes(-1,-2)@changed[:3,:3,:3]).magnitude())
    assert np.all(angles<=[20+1e-9,10+1e-9,15+1e-9]) and any(e['clamped'] for e in r['edits'])
    assert r['maximum_role_edge_length_change_m']<1e-12


def test_leaf_world_orientation_is_retained_when_cap_allows_compensation():
    local,parents,mapping=fixture();points=dict(root=[0,0,0],elbow=[1,0,0],wrist=[1,1,0])
    _,world,r=propose(local,parents,mapping,points,{0:90,1:90,2:90})
    np.testing.assert_allclose(world[2,:3,:3],np.eye(3),atol=1e-12)
    assert r['edits'][-1]['branch_rank'] is None


def test_rigid_branch_geometry_stays_valid_for_incompatible_reference_angles():
    local=np.tile(np.eye(4),(3,1,1));local[1,0,3]=1;local[2,1,3]=2
    changed,world,r=propose(local,np.array([-1,0,0]),dict(root=0,left=1,right=2),
        dict(root=[0,0,0],left=[1,0,0],right=[1,0,0]),{0:30,1:30,2:30})
    assert np.dot(world[1,:3,3],world[2,:3,3])==pytest.approx(0,abs=1e-12)
    assert np.linalg.norm(world[1,:3,3]-world[2,:3,3])==pytest.approx(np.sqrt(5))
    assert max(e['after_direction_error_degrees'] for e in r['edges'])>0


def test_rank_zero_and_rank_one_branches_do_not_invent_twist():
    r,rank=branch_rotation([[1,0,0],[-1,0,0]],[[0,1,0],[0,1,0]])
    np.testing.assert_array_equal(r,np.eye(3));assert rank==0
    r,rank=branch_rotation([[1,0,0],[-1,0,0]],[[0,1,0],[0,-1,0]])
    np.testing.assert_allclose(r@[1,0,0],[0,1,0],atol=1e-12);np.testing.assert_allclose(r@[0,0,1],[0,0,1],atol=1e-12)
    assert rank==1


def test_full_rank_matches_rigidly_rotated_branches_with_different_lengths():
    a=np.array([[2,0,0],[0,3,0],[0,0,4]]);rotation=Rotation.from_euler('xyz',[23,-17,39],degrees=True).as_matrix()
    r,rank=branch_rotation(a,(a/np.linalg.norm(a,axis=1)[:,None])@rotation.T)
    np.testing.assert_allclose(r,rotation,atol=1e-12);assert rank==3


def test_non_topological_order_helpers_and_input_arrays_remain_unchanged():
    local,parents,mapping=fixture();order=[3,2,0,1];remap={old:new for new,old in enumerate(order)}
    local=local[order];parents=np.array([-1 if parents[n]<0 else remap[int(parents[n])] for n in order]);mapping={r:remap[n] for r,n in mapping.items()}
    before=local.tobytes();points=dict(root=[0,0,0],elbow=[1,0,0],wrist=[1,1,0])
    changed,world,r=propose(local,parents,mapping,points,{n:90 for n in mapping.values()})
    assert local.tobytes()==before and r['unmapped_locals_unchanged']
    np.testing.assert_allclose(world[mapping['wrist'],:3,3],[2,3,0],atol=1e-12)


@pytest.mark.parametrize('fault',['duplicate','missing','unknown','bool','nonfinite','zero-edge','cap','unmapped-edit','cycle','nonrigid'])
def test_ambiguous_invalid_or_unsupported_inputs_reject(fault):
    local,parents,mapping=fixture();points=dict(root=[0,0,0],elbow=[1,0,0],wrist=[1,1,0]);caps={0:25,1:25,2:25}
    if fault=='duplicate':mapping['wrist']=1
    if fault=='missing':del points['wrist']
    if fault=='unknown':points['unknown']=[0,0,0]
    if fault=='bool':points['wrist']=[True,False,True]
    if fault=='nonfinite':points['wrist']=[np.nan,0,0]
    if fault=='zero-edge':points['wrist']=points['elbow']
    if fault=='cap':caps[0]=91
    if fault=='unmapped-edit':caps[3]=25
    if fault=='cycle':parents[0]=3
    if fault=='nonrigid':local[0,0,0]=1.01
    with pytest.raises(ValueError):propose(local,parents,mapping,points,caps)
