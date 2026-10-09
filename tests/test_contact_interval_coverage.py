import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_interval_coverage import partition_frames,summarize_rows,rank_windows


@pytest.mark.parametrize('length',[2,3,4,5,6,7,11,62,1000])
@pytest.mark.parametrize('width',[2,3,4,5])
def test_complete_bounded_coverage_including_odd_pairs_and_short_tail(length,width):
    frames=list(range(60,60+length));windows=partition_frames(frames,width)
    assert sorted(set(sum(windows,[])))==frames
    assert all(2<=len(w)<=width and w==list(range(w[0],w[-1]+1)) for w in windows)


@pytest.mark.parametrize('frames,width',[([],3),([1],3),([1,3],3),([True,2],3),([-1,0],3),([1,2],True),([1,2],6)])
def test_invalid_coverage_is_rejected(frames,width):
    with pytest.raises(ValueError):partition_frames(frames,width)


def test_complete_row_families_and_failure_first_ranking_never_hide_other_frames():
    frames=list(range(60,66));labels=[name+':frame-'+str(f) for f in frames for name in ['point:left','floor']]
    slacks=np.ones(12);slacks[0]=-.1;slacks[8]=-2.;slacks[11]=-.5
    result=summarize_rows(frames,labels,slacks);ranked=rank_windows(frames,result)
    assert result['audited_frames']==frames and not result['complete_keyed_rows_passed']
    assert result['frames'][4]['failed_families']=={'point':1}
    assert ranked[0]['frames']==[63,64,65] and ranked[1]['frames']==[60,61,62]
    assert sorted(set(sum([r['frames'] for r in ranked],[])))==frames
    assert not result['quality_approved'] and not result['release_approved']


def test_equal_failures_have_stable_frame_order():
    frames=list(range(8));summary=summarize_rows(frames,['floor:frame-'+str(f) for f in frames],-np.ones(8))
    assert [w['frames'][0] for w in rank_windows(frames,summary,width=2)]==[0,2,4,6]


def test_maximum_contact_interval_keeps_both_exterior_boundaries():
    contact_frames=list(range(1,1001));audited_frames=list(range(1002))
    summary=summarize_rows(audited_frames,['speed:frame-'+str(f) for f in audited_frames],np.ones(1002))
    assert summary['audited_frames']==audited_frames
    assert summary['complete_keyed_rows_passed']
    assert sorted(set(sum([w['frames'] for w in rank_windows(contact_frames,summary)],[])))==contact_frames


def test_exterior_capacity_does_not_expand_requested_contact_interval():
    with pytest.raises(ValueError):partition_frames(list(range(1001)))
    with pytest.raises(ValueError):summarize_rows(list(range(1003)),['floor:frame-'+str(f) for f in range(1003)],np.ones(1003))


@pytest.mark.parametrize('labels,values',[
    (['floor:frame-1'],[1]),(['floor:frame-1','floor:frame-1'],[1,2]),
    (['floor:frame-1','floor:frame-3'],[1,2]),(['floor','floor:frame-2'],[1,2]),
    (['floor:frame-1','floor:frame-2'],[1,float('nan')]),(['floor:frame-1','floor:frame-2'],[1])])
def test_partial_duplicated_or_nonfinite_population_is_rejected(labels,values):
    with pytest.raises(ValueError):summarize_rows([1,2],labels,values)
