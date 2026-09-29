import sys,copy
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from plan_point_rate_window import plan,describe


def fixture():
    points=np.zeros((12,3));points[:,0]=.2
    rows=[dict(region='Foot',vertex_id=0,phase=phase,contact_frame=frame,target=[0.,0.,0.],
               tolerance_m=0.,speed_limit_m_s=3.,acceleration_limit_m_s2=7.)
          for phase,frame in [('approach',4),('release',7)]]
    return {0:points},rows,[3,8]


def test_nearest_expansion_keeps_original_caps_and_input_unchanged():
    tracks,rows,window=fixture();before=copy.deepcopy(rows)
    result=plan(tracks,rows,window,12)
    assert result['requested_conflicts']==2
    assert result['proposed_window']==[2,9]
    assert rows==before and window==[3,8]
    assert result['original_phase_limits']==before and not result['rate_limits_recomputed']
    assert result['quality_approved'] is False


def test_checks_all_candidates_without_assuming_monotone_reachability():
    tracks,rows,window=fixture();tracks[0][2,0]=2.
    assert plan(tracks,rows,window,12)['proposed_window']==[1,9]


def test_no_solution_does_not_free_clip_endpoint_or_raise_rate_caps():
    tracks,rows,window=fixture();tracks[0][:,0]=10.
    result=plan(tracks,rows,window,12)
    assert result['proposed_window'] is None
    assert min(r['boundary_frame'] for r in result['approach_candidates'])==1
    assert max(r['boundary_frame'] for r in result['release_candidates'])==10
    assert 'No range is proposed.' in describe(result)
    assert 'Proposed range:' not in describe(result)


def test_already_possible_window_is_not_expanded():
    tracks,rows,window=fixture();tracks[0][:]=0.
    result=plan(tracks,rows,window,12)
    assert result['proposed_window']==window and not result['changes_requested_scope']


def test_all_points_must_pass_at_common_boundary():
    tracks,rows,window=fixture();tracks[1]=tracks[0].copy();tracks[1][:,0]=.3
    more=[dict(r,region='OtherFoot',vertex_id=1) for r in rows]
    assert plan(tracks,rows+more,window,12)['proposed_window']==[1,10]


def test_missing_phase_or_duplicate_rows_cannot_produce_a_proposal():
    tracks,rows,window=fixture()
    for incomplete in [rows[:1],rows+[rows[0]]]:
        with pytest.raises(ValueError):plan(tracks,incomplete,window,12)


@pytest.mark.parametrize('window',[[0,8],[3,11],[3.,8],[8,3]])
def test_nonheld_or_invalid_window_rejected(window):
    tracks,rows,_=fixture()
    with pytest.raises(ValueError):plan(tracks,rows,window,12)
