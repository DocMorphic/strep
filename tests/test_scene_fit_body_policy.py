from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_fit_body_policy import arguments, validate_mode


def motion(frames=4):
    return {'posed_joints': np.zeros((frames, 77, 3), dtype=np.float32)}


def test_references_keep_complete_clocks_and_are_independent_snapshots():
    raw, limb, previous = motion(), motion(), motion()
    raw['posed_joints'][:, 0, 0] = [0, 1, 2, 3]
    options = arguments(raw, limb, previous)
    raw['posed_joints'].fill(99)
    options['native_body_references']['limb']['posed_joints'].fill(10)
    assert np.array_equal(options['native_body_references']['raw']['posed_joints'][:, 0, 0], [0, 1, 2, 3])
    assert not limb['posed_joints'].any()
    assert not options['native_body_references']['previous']['posed_joints'].any()
    assert all(ref['posed_joints'].dtype == np.float64 and ref['posed_joints'].shape == (4, 77, 3)
               for ref in options['native_body_references'].values())


@pytest.mark.parametrize('bad', [None, {}, {'posed_joints': np.zeros((1, 77, 3))},
    {'posed_joints': np.zeros((4, 76, 3))}, {'posed_joints': np.zeros((4, 77, 2))},
    {'posed_joints': np.zeros((4, 77, 3), dtype=bool)},
    {'posed_joints': np.full((4, 77, 3), np.nan)}, {'posed_joints': np.full((4, 77, 3), np.inf)}])
def test_invalid_reference_rejected(bad):
    with pytest.raises(ValueError):
        arguments(motion(), bad, motion())


def test_clock_mismatch_rejected_before_any_fit():
    with pytest.raises(ValueError):
        arguments(motion(), motion(5), motion())


@pytest.mark.parametrize('flag', [None, 0, 1, 'true'])
def test_mode_requires_explicit_boolean(flag):
    with pytest.raises(ValueError):
        validate_mode(17, flag)


@pytest.mark.parametrize('version', [2, 8, 16, 18, '17', 17.0, True])
def test_enabled_mode_rejects_other_solver_versions(version):
    with pytest.raises(ValueError):
        validate_mode(version, True)


def test_disabled_mode_preserves_existing_baseline_versions():
    for version in [2, 8, 16, 17]:
        validate_mode(version, False)
    validate_mode(17, True)
