import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_pair_proposal import motion_rows,check_step


def test_motion_cones_cover_every_changed_stencil_and_overlapping_caps():
    frames=np.arange(17)/4;positions=np.zeros((17,2,3));positions[:,0,0]=np.sin(frames)
    derivative=np.ones((17,2,3,3));active=np.zeros(17,bool);active[8]=True
    values,jac,caps,orders=motion_rows(positions,derivative,positions,frames,dict(left=[0,2],right=[2,4]),[0],active)
    assert (orders==1).sum()==2 and (orders==2).sum()==3
    assert np.all(np.linalg.norm(values,axis=1)<=caps+1e-12)
    np.testing.assert_array_equal(jac,0)  # Common translation cannot alter rates.
    with pytest.raises(ValueError,match='declared window'):
        motion_rows(positions,derivative,positions,frames,dict(left=[0,1]),[0],active)


def test_clearance_improvement_cannot_hide_motion_or_trust_violation():
    gaps=np.array([-.01]);gj=np.array([[1.,0,0,-1,0,0]]);caps=np.array([.01])
    vectors=np.array([[1.,0,0]]);j=np.zeros((1,3,6));j[0,0,0]=1
    step=np.array([.002,0,0,-.002,0,0])
    result=check_step(step,gaps,gj,caps,vectors,j,np.array([1.]),.001)
    assert result['predicted_peak_m']==pytest.approx(.006)
    assert result['per_frame_cap_excess_m']==0
    assert result['norm_excess']==pytest.approx(.002)
    assert result['trust_excess_radians']==pytest.approx(.001)


def test_each_time_keeps_its_own_collision_allowance():
    result=check_step(np.array([.002,0,0]),np.array([-.01,-.004]),np.array([[1,0,0],[-1,0,0]]),
                      np.array([.01,.005]),np.zeros((0,3)),np.zeros((0,3,3)),np.zeros(0),.003)
    assert result['predicted_peak_m']==pytest.approx(.008)
    assert result['per_frame_cap_excess_m']==pytest.approx(.001)
