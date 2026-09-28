from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from frame_guarded_partner_step import solve


def problem(jac,locked=None):
    return solve(np.zeros(3),[-.02,-.01],jac,[.02,.01],np.zeros(3,bool) if locked is None else locked,
                 [.2],np.eye(3),.01)


def test_global_peak_cannot_improve_by_worsening_other_failed_frame():
    candidate,report=problem([[1,0,0],[-1,0,0]])
    assert candidate is not None
    assert abs(candidate[0])<1e-8
    assert report['predicted_peak_m']==pytest.approx(.02,abs=1e-8)
    assert report['per_frame_cap_excess_m']<1e-8


def test_jointly_feasible_improvement_respects_balls_and_caps():
    candidate,report=problem([[1,0,0],[.2,0,0]])
    assert candidate is not None and candidate[0]>.009
    assert report['predicted_peak_m']<.011
    assert np.linalg.norm(candidate)<=.01+1e-8


def test_contact_event_controls_stay_exact():
    candidate,report=problem([[1,0,0],[.2,0,0]],np.array([True,False,False]))
    assert candidate[0]==0 and report['event_controls_exact']
    assert report['predicted_peak_m']==.02


def test_invalid_source_cap_is_not_relaxed():
    with pytest.raises(ValueError,match='retained caps'):
        solve(np.zeros(3),[-.02],[[1,0,0]],[.01],np.zeros(3,bool),[.2],np.eye(3),.01)


def test_adjacent_edit_norm_is_hard_even_with_loose_trust():
    candidate,report=solve(np.zeros(6),[-.2],[[1,0,0,0,0,0]],[.2],
        [False,False,False,True,True,True],[.3,.3],np.c_[np.eye(3),-np.eye(3)],.2)
    assert candidate is not None
    assert candidate[0]>.08
    assert np.linalg.norm(candidate[:3]-candidate[3:])<=np.radians(5)+1e-8
    assert np.array_equal(candidate[3:],np.zeros(3))


def test_control_rotation_ball_stays_hard():
    candidate,report=solve(np.array([.019,0,0]),[-.02],[[1,1,0]],[.02],np.zeros(3,bool),[.02],np.eye(3),.1)
    assert candidate is not None
    assert np.linalg.norm(candidate)<=.02+1e-8


def test_immovable_overlap_is_reported_without_invented_clearance():
    candidate,report=problem([[0,0,0],[0,0,0]])
    assert report['predicted_peak_m']==.02
    assert np.linalg.norm(candidate)<1e-8


def test_proposal_buffer_is_tightening_not_acceptance_relaxation():
    candidate,report=solve(np.zeros(3),[-.02,-.01],[[1,0,0],[0,1,0]],[.02,.01],
        np.zeros(3,bool),[.2],np.eye(3),.01,tightening=[0,.001])
    assert candidate is not None and candidate[1]>=.001-1e-8
    assert report['tightened_cap_excess_m']<=1e-8
    assert report['per_frame_cap_excess_m']==0


def test_impossible_buffer_does_not_return_a_relaxed_candidate():
    candidate,report=solve(np.zeros(3),[-.02],[[0,0,0]],[.02],np.zeros(3,bool),[.2],np.eye(3),.01,tightening=[.001])
    assert candidate is None and not report['proposal_hard_checks']
