import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from contact_engine_events import contact_events


def specification(start=85, end=100, frames=120):
    return dict(fps=30, frame_count=frames, regions={
        'LeftFoot': dict(mode='explicit', segments=[dict(start_frame=start, end_frame=end)])})


def test_landing_boundaries_are_authored_not_fixed_probe_frames():
    spec = specification()
    original = copy.deepcopy(spec)
    result = contact_events(spec, 120)
    assert [e['frame'] for e in result['events']] == [85, 100]
    assert [e['time_s'] for e in result['events']] == [85 / 30, 100 / 30]
    assert [e['type'] for e in result['events']] == ['requested_pin_start', 'requested_pin_end']
    assert all(e['region'] == 'LeftFoot' and e['segment_index'] == 0 for e in result['events'])
    assert spec == original


def test_multiple_regions_single_frame_and_short_clip_keep_identity_and_order():
    spec = specification(0, 0, 9)
    spec['regions']['LeftFoot']['segments'].append(dict(start_frame=7, end_frame=8))
    spec['regions']['RightHand'] = dict(mode='explicit', segments=[dict(start_frame=0, end_frame=8)])
    spec['regions']['LeftHand'] = dict(mode='inferred')
    spec['regions']['RightFoot'] = dict(mode='disabled')
    events = contact_events(spec, 9)['events']
    assert [e['frame'] for e in events] == [0, 0, 0, 7, 8, 8]
    assert [(e['region'], e['segment_index']) for e in events] == [
        ('LeftFoot', 0), ('LeftFoot', 0), ('RightHand', 0),
        ('LeftFoot', 1), ('LeftFoot', 1), ('RightHand', 0)]


@pytest.mark.parametrize('start,end', [(85, 120), (-1, 2), (100, 85), (True, 10), (3.5, 10)])
def test_invalid_authored_frames_rejected(start, end):
    with pytest.raises(ValueError):
        contact_events(specification(start, end), 120)


def test_clock_mismatch_and_overlapping_segments_rejected():
    with pytest.raises(ValueError, match='clock'):
        contact_events(specification(), 121)
    spec = specification()
    spec['regions']['LeftFoot']['segments'].append(dict(start_frame=100, end_frame=110))
    with pytest.raises(ValueError, match='disjoint'):
        contact_events(spec, 120)


def test_no_authored_contacts_produces_no_fake_markers():
    assert contact_events(dict(fps=30, frame_count=4, regions={}), 4)['events'] == []
