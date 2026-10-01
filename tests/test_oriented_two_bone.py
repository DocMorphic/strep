import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from oriented_two_bone import reach_pose
from elbow_swivel import local_transforms
from paired_guarded_temporal import world_from_local


def fixture():
    parents = [-1, 0, 1, 2, 3, 0]
    local = np.tile(np.eye(4), (6, 1, 1))
    local[2, :3, 3] = [1, 0, 0]; local[3, :3, 3] = [0, 1, 0]
    local[4, :3, 3] = [.2, 0, 0]; local[5, :3, 3] = [0, 0, 1]
    return parents, local, world_from_local(local[None], parents)[0]


@pytest.mark.parametrize('swivel', [-.4, 0., .5])
def test_wrist_pose_reach_preserves_fingers_and_other_channels(swivel):
    parents, old, world = fixture(); rotation = Rotation.from_rotvec([.2, .3, -.1]).as_matrix()
    position = np.array([.8, .7, .2]); result, local = reach_pose(world, parents, 1, 2, 3, position, rotation, swivel)
    np.testing.assert_allclose(result[3, :3, 3], position, atol=1e-12)
    np.testing.assert_allclose(result[3, :3, :3], rotation, atol=1e-12)
    np.testing.assert_allclose(result[4, :3, 3], position+rotation@[.2, 0, 0], atol=1e-12)
    np.testing.assert_allclose(local[:, :3, 3], old[:, :3, 3], atol=1e-12)
    np.testing.assert_allclose(local[[0, 4, 5]], old[[0, 4, 5]], atol=1e-12)
    np.testing.assert_allclose(local_transforms(result, parents), local, atol=1e-12)


def test_improper_rotation_and_unreachable_wrist_rejected():
    parents, _, world = fixture()
    with pytest.raises(ValueError, match='rotation'): reach_pose(world, parents, 1, 2, 3, [1, 1, 0], -np.eye(3))
    with pytest.raises(ValueError, match='reach'): reach_pose(world, parents, 1, 2, 3, [3, 0, 0], np.eye(3))
