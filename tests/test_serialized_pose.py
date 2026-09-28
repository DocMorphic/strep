import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation, Slerp
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from serialized_pose import SerializedPose


def test_static_matrix_preserved_and_animated_node_scale_matches_encoder():
    static = np.eye(4); static[0, 0] = 2.; static[1, 3] = .125
    rig = SimpleNamespace(parents=[-1, -1], document=dict(nodes=[{'matrix': static.T.ravel().tolist()}, {'scale': [3, 3, 3]}]))
    oracle = SerializedPose(rig, {1}, 1, 3)
    world = np.tile(np.eye(4), (2, 1, 1)); world[0] = static
    world[1, :3, :3] = Rotation.from_euler('y', 23., degrees=True).as_matrix()
    world[1, 0, 3] = .123456789123
    found = oracle.pose(world)
    np.testing.assert_array_equal(found[0], static)
    assert found[1, 0, 3] == float(np.float32(world[1, 0, 3]))
    np.testing.assert_allclose(np.linalg.det(found[1, :3, :3]), 1., atol=1e-15)


def test_half_frame_crosses_quaternion_sign_boundary_on_short_arc():
    rig = SimpleNamespace(parents=[-1], document=dict(nodes=[{}]))
    oracle = SerializedPose(rig, {0}, 0, 151)
    worlds = np.tile(np.eye(4), (2, 1, 1, 1))
    worlds[0, 0, :3, :3] = Rotation.from_euler('y', 179., degrees=True).as_matrix()
    worlds[1, 0, :3, :3] = Rotation.from_euler('y', -179., degrees=True).as_matrix()
    worlds[1, 0, 0, 3] = 1.
    frame = 129
    left, right = [oracle.pose(w)[0] for w in worlds]
    times = oracle.times[frame:frame+2].astype(float)
    time = (frame+.5)/30
    expected_rotation = Slerp(times, Rotation.from_matrix([left[:3, :3], right[:3, :3]]))(time).as_matrix()
    found = oracle.half_pose(worlds[0], worlds[1], frame)[0]
    np.testing.assert_allclose(found[:3, :3], expected_rotation, atol=1e-14)
    np.testing.assert_allclose(found[0, 3], (time-times[0])/(times[1]-times[0]), atol=1e-15)
    assert found[0, 0] < -.999  # Passes through180 degrees, not zero.


def test_rejects_invalid_frame_pair_and_nonfinite_world():
    rig = SimpleNamespace(parents=[-1], document=dict(nodes=[{}]))
    oracle = SerializedPose(rig, {0}, 0, 3)
    world = np.eye(4)[None]
    for frame in [-1, 2, .5]:
        with pytest.raises(ValueError): oracle.half_pose(world, world, frame)
    world[0, 0, 3] = np.nan
    with pytest.raises(ValueError): oracle.pose(world)
