from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_witness_clock import enrich


def curve(failures):
    frames=[i*.5 for i in range(299)]
    return dict(frames=frames,body_depth_m=[.01 if f in failures else 0. for f in frames])


def test_all_methods_and_adjacent_half_frames_retained_without_mutating_base():
    base=[45.,66.,67.,75.,105.]
    result=enrich(base,dict(raw=curve([67]),strict=curve([66.5]),screen=curve([69.5])))
    assert set(base)<=set(result['frames'])
    assert {66.,66.5,67.,67.5,69.,69.5,70.}<=set(result['frames'])
    assert base==[45.,66.,67.,75.,105.]
    assert result['source_failure_frames']['screen']==[69.5]


def test_uneditable_failures_remain_explicit_and_neighbors_stop_at_window():
    result=enrich([45.,105.],dict(raw=curve([44.5,45.,105.,105.5])))
    assert result['uneditable_failure_frames']==[44.5,105.5]
    assert result['frames']==[45.,45.5,104.5,105.]


@pytest.mark.parametrize('fault',['missing','nan','negative','unordered','duplicate'])
def test_invalid_clock_or_geometry_is_not_silently_filtered(fault):
    c=curve([66.5]);base=[45.,75.,105.]
    if fault=='missing':c['body_depth_m'].pop()
    if fault=='nan':c['body_depth_m'][3]=float('nan')
    if fault=='negative':c['body_depth_m'][3]=-.1
    if fault=='unordered':base.reverse()
    if fault=='duplicate':base.append(105.)
    with pytest.raises(ValueError):enrich(base,dict(raw=c))
