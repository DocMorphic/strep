import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_clip_windows import choose_windows
from study_coupled_breadth_block import make_problem
from coupled_breadth_conic import constraints
from verify_coupled_start import verify_start
from strep import ROOT, read
from threadpoolctl import threadpool_limits


def test_windows_include_separated_failures_and_keep_fixed_endpoint_keys():
    a = np.zeros(28)
    a[[0, 1, 12, 13, 27]] = [10, 9, 8, 7, 6]
    windows = choose_windows(a, 1., 30)
    assert [w['center'] for w in windows] == [1, 13, 28]
    assert all(2 <= f < 28 for w in windows for f in w['frames'])
    assert windows[0]['frames'] == [2, 3]
    assert windows[-1]['frames'] == [26, 27]


def test_budget_ties_and_no_failures():
    a = np.zeros(28)
    a[[6, 20]] = 3.
    assert choose_windows(a, 1., 30, max_blocks=1)[0]['center'] == 7
    assert choose_windows(a, 3., 30) == []
    with pytest.raises(ValueError):
        choose_windows([np.nan]*28, 1., 30)


def test_rebased_block_keeps_original_root_radius_in_both_constraint_paths():
    folder = ROOT/'reports/coupled-breadth-block-v1'
    if not (folder/'request.json').exists():
        pytest.skip('Provisioned source fixture required')
    request = read(folder/'request.json')
    with threadpool_limits(limits=1):
        original = make_problem(folder, request)
        assert verify_start(original, folder/'source/candidate/character.glb')['matched']
        current = original.initial.copy()
        frame = original.frames[-1]
        current[frame, 0] += .006
        continued = make_problem(folder, request, initial_parameters=current)
        with pytest.raises(ValueError, match='Starting parameters'):
            verify_start(continued, folder/'source/candidate/character.glb')
        np.testing.assert_array_equal(continued.reference_parameters, original.initial)
        x = current[np.ix_(continued.frames, continued.free)].ravel()
        x[-len(continued.free)] += .006
        result = continued.evaluate(x)
        assert result[2][-1] < 0.  # 12mm cumulative move exceeds original 10mm radius.
        _, _, cones = constraints(continued, x)
        assert cones[-1]['kind'] == 'root_radius'
        assert np.linalg.norm(cones[-1]['vector']) > cones[-1]['cap']


def test_saved_half_frame_floor_failure_is_rejected_on_the_audit_clock():
    folder = ROOT/'reports/coupled-clip-sequence-v1/takes/motion-036-rig-03'
    if not (folder/'parameters.npz').exists():
        pytest.skip('Completed rejected sequence fixture required')
    request = read(folder/'request.json')
    request['frames'] = request['windows'][2]['frames']
    values = np.load(folder/'parameters.npz')['parameters']
    with threadpool_limits(limits=1):
        p = make_problem(folder, request, initial_parameters=values)
        assert p.evaluator.sample_clock == 'float32'
        assert not p.geometric_guard(values)
        p.evaluator.sample_clock = 'float64'
        assert p.geometric_guard(values)
