import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from correct_loops import crossfade_cycle, repeat_motion, geodesic_blend


def periodic_fixture():
    frames, period = 70, 23
    phase = np.arange(frames) * 2 * np.pi / period
    root = np.zeros((frames, 3))
    root[:, 1] = 1 + 0.04 * np.sin(phase)
    root[:, 2] = np.arange(frames) * 0.08
    rot = np.broadcast_to(np.eye(3), (frames, 2, 3, 3)).copy()
    rot[:, 1] = Rotation.from_euler('x', 0.3 * np.sin(phase)).as_matrix()
    contact = np.broadcast_to((np.sin(phase) >= 0)[:, None], (frames, 6)).copy()
    return {'root_positions': root, 'local_rot_mats': rot, 'foot_contacts': contact}


def test_exact_periodic_motion_stays_periodic_and_source_is_unchanged():
    source = periodic_fixture()
    original = {name: array.copy() for name, array in source.items()}
    rotations, root, contacts, delta = crossfade_cycle(source, 8, 23, 6, 'aligned')
    np.testing.assert_allclose(rotations, source['local_rot_mats'][8:31], atol=1e-7)
    expected_root = source['root_positions'][8:31].copy()
    expected_root[:, 2] -= expected_root[0, 2]
    np.testing.assert_allclose(root, expected_root, atol=1e-7)
    assert np.allclose(delta, [0, 0, 23 * 0.08])
    for name in source:
        np.testing.assert_array_equal(source[name], original[name])
    again = crossfade_cycle(source, 8, 23, 6, 'aligned')
    for first, second in zip((rotations, root, contacts, delta), again):
        np.testing.assert_array_equal(first, second)


def test_repetition_accumulates_travel_instead_of_teleporting():
    root = np.column_stack([np.zeros(23), np.ones(23), np.arange(23) * 0.08])
    motion = {'root_positions': root, 'posed_joints': root[:, None], 'foot_contacts': np.ones((23, 6), bool)}
    repeated = repeat_motion(motion, np.array([0, 0, 23 * 0.08]), 4)
    np.testing.assert_allclose(np.diff(repeated['root_positions'][:, 2]), 0.08, atol=1e-12)
    assert len(repeated['posed_joints']) == 92


def test_rotation_crossfade_uses_short_arc_and_valid_rotations():
    a = Rotation.from_euler('y', [179], degrees=True).as_matrix()[:, None]
    b = Rotation.from_euler('y', [-179], degrees=True).as_matrix()[:, None]
    result = geodesic_blend(a, b, np.array([0.5]))
    np.testing.assert_allclose(result[0, 0], Rotation.from_euler('y', 180, degrees=True).as_matrix(), atol=1e-12)
    np.testing.assert_allclose(result @ result.swapaxes(-1, -2), np.broadcast_to(np.eye(3), result.shape), atol=1e-12)
    np.testing.assert_allclose(np.linalg.det(result), 1, atol=1e-12)


def test_crossfade_never_drops_either_source_contact_label():
    source = periodic_fixture()
    source['foot_contacts'][:] = False
    source['foot_contacts'][8:14, 0] = True
    source['foot_contacts'][31:37, 1] = True
    _, _, contacts, _ = crossfade_cycle(source, 8, 23, 6, 'aligned')
    assert contacts[:6, :2].all()
    assert not contacts[:6, 2:].any()
