import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_scene_joint_rates import compare_rates


def test_impulse_is_localized_at_stencil_centers_not_keys_or_edges():
    before=np.zeros((9,1,3));after=before.copy();after[4,0,0]=1
    result=compare_rates(before,after,['hand'],{'center':[1.9,2.1],'whole':[0,4]},fps=1,subdivisions=2)
    speed=result['speed']['windows'];acceleration=result['acceleration']['windows']
    assert speed[0]['samples']==0 and speed[0]['joints']==[]
    assert speed[1]['candidate_peak']==2
    assert speed[1]['joints'][0]['candidate_peak_frame']==1.75
    assert acceleration[0]['samples']==1 and acceleration[0]['candidate_peak']==8
    assert acceleration[0]['joints'][0]['candidate_peak_frame']==2


def test_per_joint_increase_is_visible_with_unchanged_global_peak():
    before=np.zeros((9,2,3));after=before.copy()
    before[:,0,0]=np.arange(9);after[:,0,0]=np.arange(9)
    after[:,1,0]=np.arange(9)*.5
    row=compare_rates(before,after,['root','hand'],{'whole':[0,4]},fps=1,subdivisions=2)['speed']['windows'][0]
    assert row['source_peak']==row['candidate_peak']==2
    assert row['increased_joints_over_1e_5']==1 and row['joints'][1]['change']==1


def test_invalid_tracks_or_windows_rejected():
    x=np.zeros((9,1,3))
    for windows in [{'bad':[-1,2]},{'bad':[0,5]},{'bad':[3,2]}]:
        with pytest.raises(ValueError):compare_rates(x,x,['hand'],windows,subdivisions=2)
    y=x.copy();y[0,0,0]=np.nan
    with pytest.raises(ValueError):compare_rates(x,y,['hand'],{'whole':[0,2]})
