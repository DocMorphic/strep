import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compare_kneel_timing import pause_measures
from inspect_motion import skeleton_metadata


def fixture(intervals):
    names, _, _ = skeleton_metadata(77)
    joints = np.zeros((120, 77, 3))
    joints[:, names.index('Chest'), 1] = 1
    return dict(trace=[{}] * 120, kneeling_proxy_intervals=intervals), dict(posed_joints=joints)


def test_partial_pause_overlap_and_exclusive_boundaries():
    trace, motion = fixture([dict(start_frame=55, end_frame_exclusive=65),
                             dict(start_frame=80, end_frame_exclusive=100)])
    result = pause_measures(trace, motion)
    assert result['sustained_kneeling_proxy_frames'] == 15
    assert result['sustained_kneeling_proxy_fraction'] == .5
    trace['kneeling_proxy_intervals'] = [dict(start_frame=0, end_frame_exclusive=60),
                                       dict(start_frame=90, end_frame_exclusive=120)]
    assert pause_measures(trace, motion)['sustained_kneeling_proxy_frames'] == 0


def test_still_upright_torso_does_not_imply_kneeling():
    trace, motion = fixture([])
    result = pause_measures(trace, motion)
    assert result['torso_from_vertical_p95_degrees'] == 0
    assert result['pelvis_speed_p95_m_s'] == 0
    assert result['sustained_kneeling_proxy_fraction'] == 0


def test_bad_window_cannot_be_reported_as_zero_error():
    trace, motion = fixture([])
    with pytest.raises(ValueError):
        pause_measures(trace, motion, start=90, end=90)
