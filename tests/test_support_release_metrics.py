from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_release_metrics import dynamics,release_windows


def test_vector_acceleration_detects_turn_at_constant_speed():
    p=np.array([[0,0,0],[1,0,0],[1,0,1],[0,0,1]],float)
    v,a=dynamics(p,2)
    np.testing.assert_allclose(np.linalg.norm(v,axis=1),2)
    np.testing.assert_allclose(np.linalg.norm(a,axis=1),4*np.sqrt(2))


def test_release_window_contains_last_stance_and_first_swing_samples():
    p=np.zeros((10,3));p[7:,0]=1
    r=release_windows(p,[dict(start_frame=1,end_frame_exclusive=5)],10)['releases'][0]
    assert r['acceleration_frames']==[4,5,6,7]
    assert r['acceleration_max_m_s2']==100 and r['horizontal_speed_max_m_s']==10


def test_boundaries_never_extrapolate_or_invent_eof_release():
    p=np.zeros((4,3));r=release_windows(p,[dict(start_frame=0,end_frame_exclusive=1),dict(start_frame=2,end_frame_exclusive=4)],30)
    assert len(r['releases'])==1 and r['releases'][0]['acceleration_frames']==[1,2]
    assert r['global_acceleration_max_m_s2']==0


@pytest.mark.parametrize('points,fps',[(np.zeros((2,3)),30),(np.zeros((4,2)),30),(np.full((4,3),np.nan),30),(np.zeros((4,3)),0)])
def test_invalid_tracks_fail(points,fps):
    with pytest.raises(ValueError):dynamics(points,fps)
