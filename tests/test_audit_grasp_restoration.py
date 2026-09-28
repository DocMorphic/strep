import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_grasp_restoration import compare_record, coordinates, mapped
from grasp_pose_witness_bounded import physical_parameters


def test_independent_map_agrees_at_small_and_large_coordinates():
    limits = np.deg2rad([5., 12., 40.])
    rng = np.random.default_rng(91)
    for scale in [1e-8, .01, 1., 20.]:
        raw = np.r_[rng.normal(size=9)*scale, .002]
        expected = physical_parameters(torch.tensor(raw), limits).numpy()
        np.testing.assert_allclose(mapped(raw, limits), expected, atol=1e-14)
        np.testing.assert_allclose(coordinates(expected, limits), raw, atol=1e-8, rtol=1e-8)


def test_replay_rejects_changed_gate_error_or_missing_row():
    actual = dict(contacts=[dict(error_m=.004)], pose_witness_passed=False)
    compare_record(actual, actual)
    with pytest.raises(AssertionError):
        compare_record(actual, dict(contacts=[dict(error_m=.003)], pose_witness_passed=False))
    with pytest.raises(ValueError):
        compare_record(actual, dict(contacts=[dict(error_m=.004)], pose_witness_passed=True))
    with pytest.raises(ValueError):
        compare_record(actual, dict(contacts=[], pose_witness_passed=False))
