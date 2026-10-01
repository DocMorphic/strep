import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from hand_plane_retraction import retract
from paired_guarded_temporal import world_from_local


def fixture():
    parents = [-1, 0, 1, 2]; local = np.tile(np.eye(4), (4, 1, 1))
    local[2, :3, 3] = [.3, 0, 0]; local[3, :3, 3] = [0, .3, 0]
    world = world_from_local(local[None], parents)[0]
    def surface(w): return np.array([[0, 0, 0], [.01, 0, .02], [0, .01, 0]])@w[3, :3, :3].T+w[3, :3, 3]
    return parents, world, surface


def test_retraction_clears_surface_and_preserves_wrist_orientation():
    parents, world, surface = fixture()
    result, report = retract(world, parents, [1, 2, 3], surface, [0, 0, 0], [0, 0, 1], [0, 0, 1])
    assert report['selected_hand_plane_pass']
    assert np.max(surface(result)[:, 2]) <= -.0005
    np.testing.assert_allclose(result[3, :3, :3], world[3, :3, :3], atol=1e-12)
    assert not report['original_joint_limits_verified'] and not report['quality_approved']


def test_clear_input_is_bitwise_unchanged():
    parents, world, surface = fixture()
    result, report = retract(world, parents, [1, 2, 3], surface, [0, 0, 1], [0, 0, 1], [0, 0, 1])
    np.testing.assert_array_equal(result, world)
    assert report['total_retraction_m'] == 0 and report['iterations'] == []


def test_unreachable_retraction_reports_failure_without_false_clearance():
    parents, world, surface = fixture()
    result, report = retract(world, parents, [1, 2, 3], surface, [0, 0, -2], [0, 0, 1], [0, 0, 1])
    assert not report['selected_hand_plane_pass'] and report['error']
    np.testing.assert_array_equal(result, world)


def test_rig_and_stage_axes_can_differ():
    parents, world, original_surface = fixture()
    rotation = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
    surface = lambda w: original_surface(w)@rotation.T
    result, report = retract(world, parents, [1, 2, 3], surface, [0, 0, 0], [1, 0, 0], [0, 0, 1])
    assert report['selected_hand_plane_pass'] and surface(result)[:, 0].max() <= -.0005


def test_invalid_clearance_or_geometry_rejected():
    parents, world, surface = fixture()
    with pytest.raises(ValueError): retract(world, parents, [1, 2, 3], surface, [0, 0, 0], [0, 0, 2], [0, 0, 1])
    with pytest.raises(ValueError): retract(world, parents, [1, 2, 3], lambda w: np.empty((0, 3)), [0, 0, 0], [0, 0, 1], [0, 0, 1])
