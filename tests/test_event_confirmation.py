"""Unknown timing must survive loop/transition remapping and runtime packaging."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from rig_events import edit, remap, runtime_markers
from rig_event_retime import retime


MISSING = object()


def document(flag):
    event = dict(id='grasp', name='grasp', frame=1, time_s=1/30, kind='authored')
    if flag is not MISSING: event['requires_review'] = flag
    return dict(fps=30, events=[event])


@pytest.mark.parametrize('flag', [MISSING, None, 0, 0., '', [], {}, True, 'false'])
def test_unknown_or_nonboolean_confirmation_never_dispatches(flag):
    source = document(flag); original = copy.deepcopy(source)
    assert len(runtime_markers(source, 3)[0]) == 1  # generated cycle boundary only
    mapped = remap([source], [[dict(source=0, frame=1, weight=1.)]], [])
    assert mapped['events'][0]['requires_review'] is True
    assert len(runtime_markers(mapped, 3)[0]) == 1
    assert runtime_markers(mapped, 3)[1][0]['event'] == mapped['events'][0]
    assert source == original


def test_repeated_contributions_and_exact_retime_cannot_promote_unknown_timing():
    source = document(MISSING)
    loop = remap([source], [[dict(frame=1, weight=1., cycle_offset=0)],
                           [dict(frame=1, weight=1., cycle_offset=1)]], [])
    assert len(loop['events']) == 2 and len({e['id'] for e in loop['events']}) == 2
    result, _ = retime(loop, [0., 1.], 'source-glb')
    transition = remap([result], [[dict(frame=0, weight=1.)], [dict(frame=1, weight=1.)]], [])
    assert all(e['requires_review'] is True for e in transition['events'])
    assert len(runtime_markers(transition, 2)[0]) == 1
    assert all([step['operation'] for step in e['lineage']] ==
               ['source_contribution', 'clip_retime', 'source_contribution'] for e in transition['events'])


def test_confirmed_full_weight_retained_but_partial_needs_explicit_reconfirmation():
    source = document(False)
    mapped = remap([source], [[dict(frame=1, weight=.5)], [dict(frame=1, weight=1.)]], [])
    assert [e['requires_review'] for e in mapped['events']] == [True, False]
    assert [e['phase_frame'] for e in runtime_markers(mapped, 2)[0] if 'event_id' in e] == [1]
    markers = [dict(id=e['id'], name=e['name'], frame=e['frame'], confirmed=True) for e in mapped['events']]
    confirmed = edit(mapped, markers, 'new-glb', 2)
    assert len(runtime_markers(confirmed, 2)[0]) == 3
    assert mapped['events'][0]['requires_review'] is True
    assert confirmed['events'][0]['lineage'][:-1] == mapped['events'][0]['lineage']
