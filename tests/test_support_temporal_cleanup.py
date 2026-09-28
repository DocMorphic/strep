from pathlib import Path
import shutil
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read, save, sha256
from authored_root_correction import POLICY, export
from support_temporal_cleanup import SupportProblem, guarded_edges, support_mask
from verify_support_temporal_cleanup import inspect


def test_release_and_approach_neighbors_are_guarded_without_wrapping():
    active = np.array([False, False, False, True, True, False, False, False])
    assert np.flatnonzero(guarded_edges(active)).tolist() == [1, 2, 3, 4, 5]
    assert guarded_edges(np.zeros(5, bool)).tolist() == [False]*4
    assert guarded_edges(np.ones(5, bool)).tolist() == [True]*4
    assert guarded_edges([True, False, False, False, False]).tolist() == [True, True, False, False]


def test_overlapping_foot_and_toe_intervals_form_one_support_clock():
    annotations = dict(intervals=[dict(joint='LeftFoot', start_frame=1, end_frame_exclusive=3),
                                 dict(joint='LeftToeBase', start_frame=2, end_frame_exclusive=4)])
    assert support_mask(annotations, 'Left', 5).tolist() == [False, True, True, True, False]
    annotations['intervals'][0]['start_frame'] = -1
    with pytest.raises(ValueError): support_mask(annotations, 'Left', 5)


@pytest.fixture(scope='module')
def problem(tmp_path_factory):
    source = ROOT/'reports/whole-support-breadth-v1/takes/motion-061-rig-01'
    folder = tmp_path_factory.mktemp('temporal-support')
    for name in ('input', 'candidate'):
        (folder/name).mkdir()
        shutil.copyfile(source/name/'character.glb', folder/name/'character.glb')
    shutil.copyfile(source/'input/contacts.json', folder/'input/contacts.json')
    shutil.copyfile(source/'spec.json', folder/'contact-spec.json')
    shutil.copyfile(source/'request.json', folder/'support-request.json')
    spec = read(folder/'contact-spec.json')
    save(folder/'result.json', {k: spec[k] for k in ('frames', 'fps', 'root_node')})
    policy = dict(POLICY, minimum_relative_energy_improvement=.001, support_speed_tolerance_m_s=.00006)
    case = dict(source='input', candidate='candidate', files={
        p.relative_to(folder).as_posix(): sha256(p) for p in folder.rglob('*') if p.is_file()})
    return SupportProblem(folder, case, policy)


def test_unchanged_motion_retains_support_but_is_not_useful_cleanup(problem):
    audit = inspect(problem.folder, problem.source, problem.policy)
    assert all(v for k, v in audit['checks'].items() if k != 'base')
    assert all(v for k, v in audit['root']['checks'].items() if k != 'objective')
    assert not audit['all_checks_passed']


def test_exported_release_spike_is_rejected_even_outside_stance(problem, tmp_path):
    active = support_mask(problem.annotations, 'Right', problem.frames)
    frame = next(f for f in range(3, problem.frames-2) if active[f-1] and not active[f])
    ids = problem.spec['patches']['Right']['vertices']
    centers = problem.points[::2, ids].mean(axis=1)
    vector = centers[frame]-centers[frame-1]; vector[1] = 0
    vector = vector/np.linalg.norm(vector)
    parent = problem.rig.parents[problem.root]
    matrix = np.eye(3) if parent < 0 else problem.world[2*frame, parent, :3, :3]
    offsets = np.zeros((problem.frames, 3)); offsets[frame] = np.linalg.solve(matrix, .002*vector)
    path = tmp_path/'release-spike.glb'; export(problem.rig, problem.root, offsets, path)
    audit = inspect(problem.folder, path, problem.policy)
    assert not audit['checks']['support_and_boundary_speed']
    assert audit['root']['checks']['channels']
    assert audit['feet'][1]['guarded_speed_excess_m_s'] > .05


def test_supported_height_regression_cannot_hide_behind_floor_improvement(problem, tmp_path):
    active = support_mask(problem.annotations, 'Left', problem.frames)
    frame = next(f for f in range(3, problem.frames-2) if active[f])
    parent = problem.rig.parents[problem.root]
    matrix = np.eye(3) if parent < 0 else problem.world[2*frame, parent, :3, :3]
    offsets = np.zeros((problem.frames, 3)); offsets[frame] = np.linalg.solve(matrix, [0, .002, 0])
    path = tmp_path/'hover.glb'; export(problem.rig, problem.root, offsets, path)
    audit = inspect(problem.folder, path, problem.policy)
    assert not audit['checks']['support_height']
    assert audit['root']['checks']['floor']
