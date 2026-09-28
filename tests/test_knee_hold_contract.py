import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_knee_hold_contract import interval_metrics


def test_single_touch_does_not_pass_a_hold():
    points=np.array([[0.,0.,0.],[.03,0.,0.],[.06,0.,0.]])
    result=interval_metrics(points,[0.,0.,0.],100.,.02)
    assert result['contact_samples_passed']==1
    assert not result['all_contact_samples_passed']
    assert result['peak_speed_m_s']==pytest.approx(3.)
    assert result['horizontal_drift_from_first_max_m']==pytest.approx(.06)


def test_stationary_offset_and_translation_invariance():
    points=np.tile([1.,.015,2.],(5,1));target=np.array([1.,0.,2.])
    a=interval_metrics(points,target,240.,.02)
    b=interval_metrics(points+10,target+10,240.,.02)
    assert a['all_contact_samples_passed'] and b['all_contact_samples_passed']
    assert a['contact_error_max_m']==pytest.approx(b['contact_error_max_m'])
    assert a['peak_speed_m_s']==0 and a['vertical_range_m']==0


@pytest.mark.parametrize('points,fps', [([[0,0,0]],240), ([[0,0,0],[0,0,float('nan')]],240), ([[0,0,0],[0,0,0]],0)])
def test_invalid_tracks_fail(points,fps):
    with pytest.raises(ValueError):interval_metrics(points,[0,0,0],fps,.02)
