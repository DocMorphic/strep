from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from authored_root_correction import affected_nodes, root_weights, offset_maps, export, load_motion, root_channel, serialized_cap
from strep import ROOT


def test_root_scope_includes_descendants_but_not_siblings():
    assert affected_nodes([-1, 0, 1, 0, 3], 1) == [1, 2]


def test_half_frame_local_offsets_follow_animated_parent():
    world = np.tile(np.eye(4), (5, 2, 1, 1))
    world[1, 0, :3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    maps = offset_maps(world, [-1, 0], 1, 3)
    offsets = np.array([[0., 0, 0], [2, 0, 0], [0, 0, 0]])
    np.testing.assert_allclose(maps[1]@offsets.ravel(), [0, 1, 0], atol=1e-7)
    np.testing.assert_array_equal(maps[2]@offsets.ravel(), [2, 0, 0])


def test_export_affine_geometry_and_rotation_preservation(tmp_path):
    # Existing authored CesiumMan clip provides real multi-primitive skin data.
    path = ROOT/'reports/rig-jobs/20260926-202244-c3c3bb14/corrected/character.glb'
    rig, world = load_motion(path, 61)
    offsets = np.zeros((61, 3))
    offsets[2:-2, 0] = np.sin(np.arange(57))*.001
    offsets[2:-2, 1] = .0003
    target = tmp_path/'candidate.glb'
    export(rig, 3, offsets, target)
    decoded, actual = load_motion(target, 61)
    maps = offset_maps(world, rig.parents, 3, 61)
    weights = root_weights(rig, 3)
    np.testing.assert_array_equal(actual[:, :, :3, :3], world[:, :, :3, :3])
    for f in [0, 1, 5, 29, 60, 119, 120]:
        expected = rig.vertices(world[f])+weights[:, None]*(maps[f]@offsets.ravel())
        np.testing.assert_allclose(decoded.vertices(actual[f]), expected, atol=2e-7, rtol=0)
    _, _, original = root_channel(rig, 3, 61)
    _, _, changed = root_channel(decoded, 3, 61)
    np.testing.assert_allclose(changed, original+offsets, atol=6e-8, rtol=0)


def test_reject_root_curve_with_different_interpolation():
    path = ROOT/'reports/rig-jobs/20260926-202244-c3c3bb14/corrected/character.glb'
    rig, _ = load_motion(path, 61)
    channel, sampler, _ = root_channel(rig, 3, 61)
    sampler['interpolation'] = 'STEP'
    with pytest.raises(ValueError, match='LINEAR'):
        root_channel(rig, 3, 61)


def test_serialized_cap_does_not_grant_unused_error_allowance():
    assert serialized_cap(.04, .03, 1e-6) == .04
    assert serialized_cap(.04, .040000004, 1e-6) == .040000004


def test_serialized_cap_refuses_actual_source_budget_failure():
    with pytest.raises(ValueError, match='Source exceeds'):
        serialized_cap(.04, .040002, 1e-6)
    with pytest.raises(ValueError, match='Finite'):
        serialized_cap(.04, np.nan, 1e-6)
