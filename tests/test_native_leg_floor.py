"""Synthetic rigid chains test lift invariants, not human motion quality."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_leg_floor import lift_pose, foot_region, export_rotations
from paired_guarded_temporal import world_from_local


def fixture():
    parents=np.array([-1,0,1,2,3,0])
    local=np.tile(np.eye(4),(6,1,1))
    local[:,:3,3]=[[0,1.2,0],[-.2,0,0],[0,-.5,.03],[0,-.5,-.03],[0,0,.1],[.5,.1,0]]
    return world_from_local(local[None],parents)[0],parents


def test_floor_lift_keeps_root_other_branch_foot_rotation_and_lengths():
    world,parents=fixture();original=world.copy()
    changed,local,report=lift_pose(world,parents,[1,2,3],-.01)
    np.testing.assert_array_equal(world,original)
    np.testing.assert_allclose(changed[[0,5]],world[[0,5]],atol=1e-12,rtol=0)
    np.testing.assert_allclose(changed[1,:3,3],world[1,:3,3],atol=1e-12,rtol=0)
    np.testing.assert_allclose(changed[3,:3,:3],world[3,:3,:3],atol=1e-12,rtol=0)
    np.testing.assert_allclose(changed[3,:3,3]-world[3,:3,3],[0,.01025,0],atol=1e-12,rtol=0)
    np.testing.assert_allclose(changed[4,:3,3]-world[4,:3,3],[0,.01025,0],atol=1e-12,rtol=0)
    for a,b in [(1,2),(2,3)]:assert abs(np.linalg.norm(changed[a,:3,3]-changed[b,:3,3])-np.linalg.norm(world[a,:3,3]-world[b,:3,3]))<1e-12
    assert report['lift_m']==.01025


def test_clear_foot_retained_exactly():
    world,parents=fixture();changed,_,report=lift_pose(world,parents,[1,2,3],.1)
    np.testing.assert_array_equal(changed,world);assert report['lift_m']==0


@pytest.mark.parametrize('kwargs',[dict(minimum_height=np.nan),dict(minimum_height=-.04),dict(maximum_angle_degrees=.1),dict(up=[0,2,0]),dict(clearance=-1),dict(maximum_lift=0),dict(maximum_angle_degrees=46)])
def test_invalid_or_infeasible_lift_rejected(kwargs):
    world,parents=fixture();options=dict(minimum_height=-.01);options.update(kwargs)
    with pytest.raises(ValueError):lift_pose(world,parents,[1,2,3],**options)


def test_chain_and_scaled_transforms_rejected_even_without_lift():
    world,parents=fixture()
    with pytest.raises(ValueError):lift_pose(world,parents,[1,3,2],.1)
    world[0,0,0]=2
    with pytest.raises(ValueError):lift_pose(world,parents,[1,2,3],.1)


def test_regions_ignore_only_zero_influences_and_reject_mixed_vertices():
    _,parents=fixture()
    skin=SimpleNamespace(nodes=np.array([[3,0],[3,4],[3,1]]),weights=np.array([[1,0],[.5,.5],[.99999999999,.00000000001]]))
    np.testing.assert_array_equal(foot_region(skin,parents,3),[0,1])
    skin.weights[0]=[.5,.5];skin.nodes[1]=[3,1]
    with pytest.raises(ValueError):foot_region(skin,parents,3)


def test_export_keeps_native_clocks_and_shared_sampler_other_channel(tmp_path):
    from test_timed_rotation_edit import fixture as animation_fixture
    from paired_temporal_neighbor import rotation_channels
    from gltf_tools import read_glb
    from scipy.spatial.transform import Rotation
    import copy
    doc,binary=animation_fixture();original=copy.deepcopy(doc);old=rotation_channels(doc,binary)
    q=(Rotation.from_quat(old[1][2])*Rotation.from_rotvec([.01,0,0])).as_quat()
    path=tmp_path/'native.glb';export_rotations(doc,binary,{1:q},path)
    updated,payload=read_glb(path);new=rotation_channels(updated,payload)
    assert doc==original
    np.testing.assert_array_equal(new[1][1],old[1][1]);np.testing.assert_array_equal(new[3][2],old[3][2])
    assert not np.array_equal(new[1][2],old[1][2])
    # Endpoints are intentionally editable for this full-clip leg condition.
    assert not np.array_equal(new[1][2][0],old[1][2][0])
    with pytest.raises(ValueError):export_rotations(doc,binary,{1:q[:2]},tmp_path/'bad.glb')
    with pytest.raises(ValueError):export_rotations(doc,binary,{0:q},tmp_path/'missing.glb')
