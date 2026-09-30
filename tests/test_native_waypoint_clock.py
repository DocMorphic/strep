import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_waypoint_clock import guide_clock,guarded_approach_window
from timed_rotation_edit import editable_keys


def test_support_ends_at_frozen_keys_inside_guard_window():
    clock=np.arange(11,dtype=np.float32)/10
    times=guide_clock([clock]*6,[.15,.45,.85],[])
    np.testing.assert_array_equal(times,clock[2:9].astype(float))
    ids=editable_keys(clock,[.15,.85],[])
    np.testing.assert_array_equal(times[1:-1],clock[ids])
    assert times[0]>.15 and times[-1]<.85


def test_protected_span_splits_support_without_crossing_guard():
    clock=np.arange(11,dtype=float)
    np.testing.assert_array_equal(guide_clock([clock],[0,2,10],[[5,6]]),[0,1,2,3,4,5])
    np.testing.assert_array_equal(guide_clock([clock],[0,8,10],[[5,6]]),[6,7,8,9,10])
    with pytest.raises(ValueError,match='No editable'):guide_clock([clock],[0,5.5,10],[[5,6]])


@pytest.mark.parametrize('fault',['empty','asynchronous','duplicate','no_support','peak_boundary','nan'])
def test_unsupported_clocks_fail_explicitly(fault):
    clocks=[np.arange(11,dtype=float)]*2;window=[0,4,10];protected=[]
    if fault=='empty':clocks=[]
    if fault=='asynchronous':clocks=[clocks[0],clocks[1]+.001]
    if fault=='duplicate':clocks=[np.array([0,1,1,2])]
    if fault=='no_support':protected=[[0,10]]
    if fault=='peak_boundary':window=[0,0,10]
    if fault=='nan':window=[0,np.nan,10]
    with pytest.raises(ValueError):guide_clock(clocks,window,protected)


def test_full_approach_uses_existing_authored_window_and_nearest_guards():
    assert guarded_approach_window([1,8],4,[[2,3],[6,7]])==(3.,4.,6.)
    assert guarded_approach_window([1,8],4,[])==(1.,4.,8.)
    assert guarded_approach_window([1,8],4,[[6,6],[20,21]])==(1.,4.,6.)
    with pytest.raises(ValueError,match='protected'):guarded_approach_window([1,8],4,[[4,4]])
    with pytest.raises(ValueError):guarded_approach_window([1,8],4,[[6,5]])
    with pytest.raises(ValueError):guarded_approach_window([1,8],9,[])


def test_float32_key_just_before_contact_remains_frozen_boundary():
    clock=np.arange(21,dtype=np.float32)/10;contact=float(clock[14])+1e-7
    window=guarded_approach_window([.15,1.9],.6,[[contact,contact]])
    native=guide_clock([clock]*6,window,[[contact,contact]])
    assert native[-1]==clock[14] and native[-1]<contact
    assert 14 not in editable_keys(clock,[window[0],window[2]],[[contact,contact]])
