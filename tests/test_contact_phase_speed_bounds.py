from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_phase_speed_bounds import transition_bounds


def phase(start, end, target, vertex=4):
    return dict(start_time_s=start,end_time_s=end,target_m=target,vertex=vertex)


def test_both_contact_balls_reduce_required_travel_and_native_gap_is_used():
    result=transition_bounds([phase(0.,1.,[0.,0.,0.]),phase(1.25,2.,[.3,0.,.4])],contact_error_m=.02)
    row=result['pairs'][0]
    assert row['target_separation_m']==pytest.approx(.5)
    assert row['minimum_travel_m']==pytest.approx(.46)
    assert row['minimum_average_speed_m_s']==pytest.approx(1.84)
    assert not result['actual_motion_assessed'] and not result['quality_approved']


@pytest.mark.parametrize('start,end',[(.5,1.5),(1.,1.),(0.,2.)])
def test_disjoint_target_balls_during_overlap_or_touch_are_incompatible(start,end):
    result=transition_bounds([phase(0.,1.,[0.,0.,0.]),phase(start,end,[.1,0.,0.])],contact_error_m=.02)
    assert result['simultaneous_target_conflicts']==1
    assert result['pairs'][0]['minimum_average_speed_m_s'] is None


def test_overlapping_balls_do_not_impose_positive_speed_or_claim_feasibility():
    result=transition_bounds([phase(0.,1.,[0.,0.,0.]),phase(.5,2.,[.03,0.,0.])],contact_error_m=.02)
    assert result['simultaneous_target_conflicts']==0
    assert result['pairs'][0]['minimum_travel_m']==0.
    assert result['pairs'][0]['minimum_average_speed_m_s']==0.
    assert not result['actual_motion_assessed']


def test_vertex_identity_sorting_and_original_indices_are_retained():
    phases=[phase(2.,3.,[1.,0.,0.]),phase(0.,1.,[0.,0.,0.]),phase(1.,2.,[99.,0.,0.],vertex=5)]
    result=transition_bounds(phases,contact_error_m=.02)
    assert len(result['pairs'])==1
    assert result['pairs'][0]['first_phase_index']==1
    assert result['pairs'][0]['second_phase_index']==0
    assert phases[0]['start_time_s']==2.


def test_nonadjacent_overlaps_are_checked_and_empty_input_is_explicit():
    phases=[phase(0.,10.,[0.,0.,0.]),phase(1.,2.,[.01,0.,0.]),phase(3.,4.,[.1,0.,0.])]
    result=transition_bounds(phases,contact_error_m=.02)
    assert len(result['pairs'])==3
    assert result['simultaneous_target_conflicts']==1
    assert transition_bounds([],contact_error_m=.02)['pairs']==[]


@pytest.mark.parametrize('fault',['negative_time','reversed','nan_time','vertex','short_target','nan_target','zero_tolerance','bool_tolerance','overflow'])
def test_invalid_or_unrepresentable_requests_reject(fault):
    first=phase(0.,1.,[0.,0.,0.]);second=phase(2.,3.,[.1,0.,0.]);tolerance=.02
    if fault=='negative_time':first['start_time_s']=-1.
    if fault=='reversed':first['end_time_s']=-1.
    if fault=='nan_time':first['start_time_s']=float('nan')
    if fault=='vertex':first['vertex']=True
    if fault=='short_target':first['target_m']=[0.,0.]
    if fault=='nan_target':first['target_m'][0]=float('nan')
    if fault=='zero_tolerance':tolerance=0.
    if fault=='bool_tolerance':tolerance=True
    if fault=='overflow':first['target_m'][0]=-1e308;second['target_m'][0]=1e308
    with pytest.raises(ValueError):transition_bounds([first,second],contact_error_m=tolerance)
