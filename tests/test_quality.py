import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evaluate_grid import loop_screen, transition_screen
from strep import ROOT, read


def test_smooth_periodic_motion_is_not_rejected_for_nonidentical_endpoints():
    count = 60
    phase = np.arange(count) * 2 * np.pi / count
    pose = np.zeros((count, 2, 3))
    pose[:, 1, 0] = np.sin(phase)
    pose[:, 1, 1] = np.cos(phase)
    rotations = np.broadcast_to(np.eye(3), (count, 2, 3, 3)).copy()
    root = np.zeros((count, 3)); root[:, 2] = np.arange(count) / 30
    data = {'posed_joints': pose + root[:, None], 'local_rot_mats': rotations, 'global_rot_mats': rotations,
            'root_positions': root}
    targets = read(ROOT / 'benchmarks/acceptance-v0.json')['targets']
    screen = loop_screen(data, 30, targets)
    assert screen['raw_root_relative_endpoint_joint_rms_m'] > 0.05
    assert screen['next_pose_prediction_rms_m'] < 0.01
    assert screen['screen_status'] == 'within_provisional_screen'
    data['posed_joints'][0, 1, 0] += 0.5
    broken = loop_screen(data, 30, targets)
    assert 'next_pose_prediction_rms_m' in broken['screen_exceedances']


def test_transition_diagnostic_detects_boundary_teleport():
    root = np.zeros((210, 3))
    root[:, 2] = np.arange(210) / 30
    data = {'root_positions': root, 'posed_joints': root[:, None, :].copy()}
    good = transition_screen(data, 30)
    assert max(row['root_velocity_change_m_s'] for row in good['boundary_samples']) < 1e-10
    data['root_positions'][90:, 0] += 1
    bad = transition_screen(data, 30)
    assert max(row['root_step_m'] for row in bad['boundary_samples']) > 1
