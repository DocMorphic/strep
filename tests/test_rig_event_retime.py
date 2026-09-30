import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_event_retime import retime
from rig_events import edit,runtime_markers


def document():
    return edit({'events':[]},[dict(id=str(f),name='cue-'+str(f),frame=f,confirmed=f!=4)
        for f in [0,1,2,3,4,5,6]],'original',7)


def test_speed_edit_excludes_shifted_confirmed_events_from_runtime_until_reconfirmation():
    before=document();untouched=copy.deepcopy(before)
    result,audit=retime(before,np.arange(0,7,2),'source')
    assert before==untouched
    assert [e['frame'] for e in result['events']]==[0,1,1,2,2,3,3]
    assert [e['requires_review'] for e in result['events']]==[False,True,False,True,True,True,False]
    assert audit['shifted_event_count']==3 and audit['maximum_absolute_timing_error_s']==pytest.approx(1/60)
    eligible,_=runtime_markers(result,4)
    assert [e['name'] for e in eligible]==['cycle_boundary','cue-0','cue-2','cue-6']
    confirmed=edit(result,[dict(id=e['id'],name=e['name'],frame=e['frame'],confirmed=True) for e in result['events']],'edited',4)
    assert len(runtime_markers(confirmed,4)[0])==8
    assert confirmed['events'][1]['lineage'][-2]['timing_error_s']==pytest.approx(1/60)


def test_trim_endpoints_stable_order_omissions_and_repeated_edit_lineage():
    first,audit=retime(document(),[1,3,5],'first')
    assert audit['dropped_event_indices']==[0,6]
    assert [e['id'] for e in first['events']]==['1','2','3','4','5']
    assert [e['frame'] for e in first['events']]==[0,1,1,2,2]
    second,_=retime(first,[0,.5,1,1.5,2],'second')
    event=next(e for e in second['events'] if e['id']=='2')
    assert event['requires_review'] and event['frame']==2
    assert [e['source_glb_sha256'] for e in event['lineage']]==['original','first','second']
    assert [e['source_frame'] for e in event['lineage'][1:]]==[2,1]


def test_slowdown_exact_mapping_retains_confirmation_and_empty_events_are_valid():
    result,audit=retime(document(),np.arange(13)/2,'source')
    assert [e['frame'] for e in result['events']]==list(range(0,13,2))
    assert audit['shifted_event_count']==0
    assert [e['requires_review'] for e in result['events']]==[False]*4+[True,False,False]
    result,audit=retime({'events':[]},[0,1],'source')
    assert not result['events'] and audit['maximum_absolute_timing_error_s']==0


def test_rounding_can_advance_events_and_missing_confirmation_stays_unknown():
    source=document();del source['events'][0]['requires_review']
    result,audit=retime(source,[0,3,6],'source')
    assert result['events'][0]['requires_review']
    row=next(r for r in audit['events'] if r['source_frame']==1)
    assert row['output_frame']==0 and row['timing_error_s']==pytest.approx(-1/90)
    assert row['rounded_timing_requires_review']


@pytest.mark.parametrize('clock',[[0,0],[1,0],[0,float('nan')],[0,float('inf')],[0]])
def test_invalid_clock_is_rejected(clock):
    with pytest.raises(ValueError):retime(document(),clock,'source')


@pytest.mark.parametrize('frame',[float('nan'),float('inf'),True,'1'])
def test_invalid_event_clock_is_rejected(frame):
    source=document();source['events'][0]['frame']=frame
    with pytest.raises(ValueError):retime(source,[0,1],'source')
