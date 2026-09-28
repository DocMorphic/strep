import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from correct_stance import periodic_offsets, knee_target, swing, apply_offsets
from correct_loops import assemble


def test_periodic_offset_accounts_for_root_travel_at_wrap():
    n = 12
    points = np.zeros((n, 1, 3))
    points[:, 0, 2] = np.arange(n) * .03
    contacts = np.zeros((n, 1), bool)
    contacts[[10, 11, 0, 1], 0] = True
    delta = np.array([0, 0, n * .03])
    offsets = periodic_offsets(points, contacts, delta, 100, .1, .02)
    fixed = points + offsets[:, None]
    wrap_velocity = fixed[0, 0] + delta - fixed[-1, 0]
    assert np.linalg.norm(wrap_velocity) < .001
    assert np.isfinite(offsets).all()
    np.testing.assert_array_equal(offsets[:, 1], 0)


def test_no_contacts_no_correction():
    rng = np.random.default_rng(4)
    offsets = periodic_offsets(rng.normal(size=(20, 3, 3)), np.zeros((20, 3), bool), np.array([0, 0, 2]), 100, 1, .02)
    np.testing.assert_array_equal(offsets, 0)


def test_two_bone_ik_preserves_lengths_and_bend_side():
    h, k, a = np.array([0, 1., 0]), np.array([0, .6, .2]), np.array([0, .2, 0])
    target = a + [.05, 0, .04]
    new_k, new_a, clamp = knee_target(h, k, a, target)
    np.testing.assert_allclose(new_a, target, atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(new_k-h), np.linalg.norm(k-h), atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(new_a-new_k), np.linalg.norm(a-k), atol=1e-12)
    assert new_k[2] > 0 and clamp == 0
    far_k, far_a, clamp = knee_target(h, k, a, np.array([0, -10, 0]))
    assert clamp > 1
    np.testing.assert_allclose(np.linalg.norm(far_a-far_k), np.linalg.norm(a-k), atol=1e-10)


def test_antipodal_swing_is_proper_rotation():
    matrix = swing([1, 0, 0], [-1, 0, 0])
    np.testing.assert_allclose(matrix @ [1, 0, 0], [-1, 0, 0], atol=1e-12)
    np.testing.assert_allclose(np.linalg.det(matrix), 1, atol=1e-12)


def test_leg_ik_reaches_foot_target_and_preserves_world_orientation():
    from kimodo.skeleton import SOMASkeleton77
    from scipy.spatial.transform import Rotation
    skeleton = SOMASkeleton77()
    local = np.broadcast_to(np.eye(3), (3, 77, 3, 3)).copy()
    knee = skeleton.bone_order_names.index('LeftFoot') - 1
    local[:, knee] = Rotation.from_euler('x', -.5).as_matrix()
    motion = assemble(local, np.tile([0, 1.1, 0], (3, 1)), np.ones((3, 6), bool), skeleton)
    original = {key: val.copy() for key, val in motion.items()}
    shift = np.tile([.004, 0, .007], (3, 1))
    fixed, clamp = apply_offsets(motion, [shift, np.zeros_like(shift)], skeleton)
    foot = skeleton.bone_order_names.index('LeftFoot')
    np.testing.assert_allclose(fixed['posed_joints'][:, foot], motion['posed_joints'][:, foot] + shift, atol=3e-7)
    np.testing.assert_allclose(fixed['global_rot_mats'][:, foot], motion['global_rot_mats'][:, foot], atol=3e-7)
    assert clamp == 0
    for name in original:
        np.testing.assert_array_equal(motion[name], original[name])
