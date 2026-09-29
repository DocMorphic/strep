import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from region_floor_envelope import sample_weights,solve_lift


def test_subframe_constraint_drives_lift_with_fixed_endpoints():
    times=np.array([0,.5,1,1.5,2]);heights=np.array([.01,.001,.001,.001,.01]);delta,result=solve_lift(times,heights,np.full(3,.01),[1],target_height=.002)
    np.testing.assert_allclose(delta,[0,.002,0],atol=1e-9)
    assert np.min(heights+sample_weights(times,3)@delta)>=.002-1e-10


def test_locked_failure_and_insufficient_capacity_are_retained_as_errors():
    with pytest.raises(ValueError,match='locked'):solve_lift([0,1,2],[0,.01,.01],np.ones(3),[1])
    with pytest.raises(ValueError,match='capacity'):solve_lift([0,1,2],[.01,0,.01],np.full(3,.001),[1])


def test_safe_track_has_zero_correction():
    delta,result=solve_lift([0,.5,1,1.5,2],np.full(5,.01),np.full(3,.1),[1])
    np.testing.assert_array_equal(delta,np.zeros(3))
