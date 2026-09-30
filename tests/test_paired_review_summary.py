import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from paired_review_summary import partner_summary


def test_fractional_collision_times_and_failures_are_not_rounded_or_hidden():
    rows = [dict(frame=66.5, candidate_depth_m=.004), dict(frame=66.75, candidate_depth_m=.023), dict(frame=67., candidate_depth_m=.005)]
    data = partner_summary(rows)
    assert data['frames_checked'] == [66.5, 66.75, 67.]
    assert data['pairs'][0]['frames_over_tolerance'] == 1
    assert data['pairs'][0]['max_depth_m'] == .023
    assert data['quality_approved'] is False


@pytest.mark.parametrize('rows', [[], [dict(frame=1, candidate_depth_m=float('nan'))],
    [dict(frame=1, candidate_depth_m=-1)], [dict(frame=float('nan'), candidate_depth_m=0)],
    [dict(frame=1, candidate_depth_m=0), dict(frame=1, candidate_depth_m=0)],
    [dict(frame=2, candidate_depth_m=0), dict(frame=1, candidate_depth_m=0)]])
def test_bad_or_duplicate_geometry_is_rejected(rows):
    with pytest.raises(ValueError):
        partner_summary(rows)
