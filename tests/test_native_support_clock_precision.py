"""Distinct Float64 authoring times must not collapse onto Float32 key bounds."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_clock import NativeSupportSampler
from rig_clip_import import AnimationSampler


@pytest.fixture(params=[NativeSupportSampler,AnimationSampler],ids=['native-authoring','clip-import'])
def Sampler(request):return request.param


def test_query_before_float32_endpoint_is_interpolated_not_clamped(Sampler):
    times=np.array([0.,119/30],np.float32);end=float(times[-1]);query=119/30
    assert query<end
    actual=Sampler.value('translation',times,np.array([[0.],[1.]]),'LINEAR',query)[0]
    assert actual<1. and abs(actual-query/end)<1e-14


def test_step_changes_at_exact_final_key_only(Sampler):
    times=np.array([0.,119/30],np.float32);end=float(times[-1]);values=np.array([[2.],[5.]])
    assert Sampler.value('translation',times,values,'STEP',end-3.2e-8)[0]==2.
    assert Sampler.value('translation',times,values,'STEP',end)[0]==5.


def test_query_after_first_key_is_not_rounded_back_to_start(Sampler):
    times=np.array([1.,2.],np.float32);query=1.+2e-8
    actual=Sampler.value('translation',times,np.array([[0.],[1.]]),'LINEAR',query)[0]
    assert actual>0 and abs(actual-(query-1.))<1e-15


def test_rotation_after_first_key_retains_fractional_motion(Sampler):
    times=np.array([1.,2.],np.float32);query=1.+2e-8
    values=np.array([[0.,0.,0.,1.],[0.,0.,np.sin(.5),np.cos(.5)]])
    actual=Sampler.value('rotation',times,values,'LINEAR',query)
    np.testing.assert_allclose(actual,[0.,0.,np.sin((query-1.)/2),np.cos((query-1.)/2)],atol=1e-15,rtol=0)


@pytest.mark.parametrize('mode',['LINEAR','CUBICSPLINE'])
def test_interval_uses_exact_difference_of_stored_key_times(mode,Sampler):
    times=np.array([.1,.4],np.float32);a,b=map(float,times);query=.2;t=(query-a)/(b-a)
    if mode=='LINEAR':values=np.array([[0.],[2.]]);expected=2*t
    else:
        values=np.array([[0.],[0.],[3.],[-2.],[2.],[0.]])
        expected=(b-a)*(t**3-2*t*t+t)*3+(-2*t**3+3*t*t)*2+(b-a)*(t**3-t*t)*-2
    assert abs(Sampler.value('translation',times,values,mode,query)[0]-expected)<1e-14


def test_exact_keys_and_stored_clock_bytes_remain_unchanged(Sampler):
    times=np.array([.1,.4,1.2],np.float32);values=np.arange(9,dtype=float).reshape(3,3);original=times.tobytes()
    for i,time in enumerate(times):np.testing.assert_array_equal(Sampler.value('translation',times,values,'LINEAR',float(time)),values[i])
    Sampler.value('translation',times,values,'LINEAR',.2)
    assert times.dtype==np.float32 and times.tobytes()==original
