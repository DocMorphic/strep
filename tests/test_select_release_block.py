from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from select_release_block import select_block


def fixture(frame, centers, value=5., limit=3., side='Right'):
    return (dict(side=side, release_frame=frame, candidate_m_s2=value, limit_m_s2=limit, candidate_passed=False),
        dict(side=side, release_frame=frame, centers=centers, original_limit_m_s2=limit))


def test_selects_worst_failure_and_retains_other_failures_on_long_clip():
    early = fixture(45, [44,45,46,47], 4.6, 3.85)
    late = fixture(193, [192,193,194,195], 9.09, 4.11)
    result = select_block([early[0],late[0]], [early[1],late[1]], 210)
    assert result['release_frame'] == 193 and result['frames'] == list(range(190,198))
    assert len(result['failed_population']) == 2


def test_clips_boundaries_and_tie_break_is_input_order_independent():
    right = fixture(2,[1,2], side='Right'); left = fixture(2,[1,2], side='Left')
    a = select_block([right[0],left[0]], [right[1],left[1]], 5)
    b = select_block([left[0],right[0]], [left[1],right[1]], 5)
    assert a == b and a['side'] == 'Left' and a['frames'] == list(range(5))


def test_rejects_missing_failure_or_inconsistent_clock_and_limit():
    event, release = fixture(2,[1,2])
    with pytest.raises(ValueError): select_block([], [release], 5)
    with pytest.raises(ValueError): select_block([event], [{**release,'centers':[1,3]}], 5)
    with pytest.raises(ValueError): select_block([event], [{**release,'original_limit_m_s2':4.}], 5)
