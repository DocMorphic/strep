from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_authoring_intent import check_files, posture_expected, joint_targets, rotation_error
from strep import sha256


def test_changed_recipe_is_rejected(tmp_path):
    path = tmp_path/'recipe.json'
    path.write_text('{}')
    files = {'recipe.json': sha256(path)}
    path.write_text('{"changed":true}')
    with pytest.raises(ValueError, match='Frozen input changed'):
        check_files(tmp_path, files)


def test_intent_uses_world_target_not_source_pose():
    source = np.tile(np.eye(4), (3, 1, 1, 1))
    candidate = source.copy()
    candidate[1, 0, :3, 3] = [1, 0, 0]
    candidate[1, 0, :3, :3] = Rotation.from_euler('z', 45, degrees=True).as_matrix()
    goal = dict(frame=1, node=0, position_m=[1, 0, 0],
                rotation_xyzw=Rotation.from_euler('z', 45, degrees=True).as_quat())
    row = joint_targets({'goals': [goal]}, {'source': source, 'candidate': candidate})[0]
    assert row['source']['position_error_m'] == 1
    assert row['source']['orientation_error_degrees'] == pytest.approx(45)
    assert row['candidate']['position_error_m'] == 0
    assert row['candidate']['orientation_error_degrees'] == pytest.approx(0, abs=1e-10)


def test_independent_posture_blend_preserves_endpoints_and_other_nodes():
    local = np.tile(np.eye(4), (9, 2, 1, 1))
    recipe = {'poses': [dict(id='finger', start_frame=0, full_start_frame=4,
        full_end_frame=4, end_frame=8, strength=.5,
        targets=[dict(node=1, rotation_xyzw=Rotation.from_euler('z', 80, degrees=True).as_quat())])]}
    expected, weights = posture_expected(local, recipe)
    np.testing.assert_array_equal(expected[:, 0], local[:, 0])
    np.testing.assert_array_equal(expected[[0, 8]], local[[0, 8]])
    assert weights['finger'][2] == .25
    angle = rotation_error(local[:, 1, :3, :3], expected[:, 1, :3, :3])
    np.testing.assert_allclose(angle[[2, 4, 6]], [20, 40, 20], atol=1e-10)


def test_rotation_difference_handles_pi_wrap():
    first = Rotation.from_euler('z', 179, degrees=True).as_matrix()
    second = Rotation.from_euler('z', -179, degrees=True).as_matrix()
    assert float(rotation_error(first, second)) == pytest.approx(2)
