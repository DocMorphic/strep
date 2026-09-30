import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from boundary_motion import affected_positions,window_peaks,make_caps


def test_position_dependencies_include_fingers_but_not_own_rotation():
    # Root -> shoulder -> arm -> hand -> finger; another branch stays fixed.
    assert affected_positions([-1,0,1,2,3,0],[1,2,3])==[2,3,4]
    with pytest.raises(ValueError):affected_positions([-1,2,0],[0])


def test_join_acceleration_uses_fixed_neighbors_and_keeps_each_joint_separate():
    times=np.arange(1,7.001,.25);positions=np.zeros((len(times),2,3))
    positions[times==2,0,0]=.01
    positions[times==6,1,0]=.002
    speed,acceleration=window_peaks(times,positions,[3,4,5])
    np.testing.assert_allclose(speed,[1.2,.24])
    np.testing.assert_allclose(acceleration,[288.,57.6])
    changed=positions.copy();changed[:,0]*=.1;changed[:,1]*=2
    _,after=window_peaks(times,changed,[3,4,5])
    assert after.max()<acceleration.max() and after[1]>acceleration[1]


def test_missing_join_support_or_bad_sampling_rejected():
    times=np.arange(2,6.001,.25);positions=np.zeros((len(times),1,3))
    with pytest.raises(ValueError,match='stencils'):window_peaks(times,positions,[3,4,5])
    with pytest.raises(ValueError,match='quarter'):window_peaks(times*2,positions,[3,4,5])


def test_caps_use_lower_comparison_for_each_joint_and_keep_fitting_reserve_separate(monkeypatch):
    times=np.arange(1,7.001,.25);input_positions=np.zeros((len(times),2,3))
    input_positions[times==2,0,0]=.01;input_positions[times==6,1,0]=.002
    reference=input_positions.copy();reference[:,0]*=.2;reference[:,1]*=2
    monkeypatch.setattr('boundary_motion.sample_positions',lambda path,frames:(times,input_positions if path=='input' else reference))
    caps=make_caps('input','reference',[3,4,5],[0,1],['Arm','Finger'])
    np.testing.assert_allclose(caps['speed_caps_m_s'],[.24,.24])
    np.testing.assert_allclose(caps['acceleration_caps_m_s2'],[57.6,57.6])
    np.testing.assert_allclose(caps['fitting_acceleration_caps_m_s2'],np.array([57.6,57.6])*.99)
    with pytest.raises(ValueError):make_caps('input','reference',[3,4,5],[0,1],['Arm','Finger'],1.)
