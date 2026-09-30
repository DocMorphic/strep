import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from two_bone_waypoint import reach,align_vectors
from elbow_swivel import swivel,descendants
from test_elbow_swivel import arm
from paired_guarded_temporal import world_from_local


@pytest.mark.parametrize('target_angle',[0,.2,-.6])
def test_reach_preserves_bone_lengths_orientation_and_native_local_translations(target_angle):
    parents,original,world=arm();target=world[3,:3,3]+[-.02,.03,.01]
    moved,local=reach(world,parents,1,2,3,target,target_angle)
    np.testing.assert_allclose(world_from_local(local[None],parents)[0],moved,atol=1e-14,rtol=0)
    np.testing.assert_allclose(moved[3,:3,3],target,atol=1e-14,rtol=0)
    np.testing.assert_allclose(moved[3:5,:3,:3],world[3:5,:3,:3],atol=1e-14,rtol=0)
    np.testing.assert_allclose(local[:,:3,3],original[:,:3,3],atol=1e-14,rtol=0)
    for a,b in [(1,2),(2,3)]:
        assert np.linalg.norm(moved[a,:3,3]-moved[b,:3,3])==pytest.approx(np.linalg.norm(world[a,:3,3]-world[b,:3,3]),abs=1e-14)
    np.testing.assert_allclose(moved[[0,6]],world[[0,6]],atol=1e-14,rtol=0)


def test_zero_displacement_matches_previous_swivel_and_zero_edit_is_exact():
    parents,_,world=arm()
    for angle in [0,.4,-.2]:
        actual=reach(world,parents,1,2,3,world[3,:3,3],angle)
        expected=swivel(world,parents,1,2,3,angle)
        for a,b in zip(actual,expected):np.testing.assert_array_equal(a,b)


def test_reach_has_no_discontinuous_pose_jump_at_zero_offset():
    parents,_,world=arm()
    base,_=reach(world,parents,1,2,3,world[3,:3,3],.3)
    moved,_=reach(world,parents,1,2,3,world[3,:3,3]+[1e-8,-1e-8,0],.3)
    assert np.abs(moved-base).max()<1e-6


@pytest.mark.parametrize('target',[[100,0,0],[np.nan,0,0],[1,2]])
def test_unreachable_or_invalid_targets_are_rejected_without_clamping(target):
    parents,_,world=arm()
    with pytest.raises(ValueError):reach(world,parents,1,2,3,target)


@pytest.mark.parametrize('a,b',[([1,0,0],[-1,0,0]),([1,2,3],[1,2,3]),([1,2,3],[-3,1,2])])
def test_alignment_handles_parallel_and_antiparallel_vectors(a,b):
    rot=align_vectors(a,b)
    np.testing.assert_allclose(rot@(np.array(a)/np.linalg.norm(a)),np.array(b)/np.linalg.norm(b),atol=1e-14)
    assert np.linalg.det(rot)==pytest.approx(1.)


def test_straight_arm_and_exact_reach_boundary_remain_finite():
    parents,local,_=arm();local[2,:3,3]=[.3,0,0];local[3,:3,3]=[.2,0,0]
    world=world_from_local(local[None],parents)[0];shoulder=world[1,:3,3]
    for distance in [.5,.4,.1]:
        target=shoulder+np.array([0.,distance,0.])
        moved,_=reach(world,parents,1,2,3,target)
        np.testing.assert_allclose(moved[3,:3,3],target,atol=1e-9,rtol=0)
    with pytest.raises(ValueError):reach(world,parents,1,2,3,shoulder+[0,.09,0])
