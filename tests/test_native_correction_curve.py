from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_correction_curve import CorrectionCurve
from native_support_clock import NativeSupportSampler


def fixture():
    rng=np.random.default_rng(124)
    clock=np.array([0.,.0333333,.081, .12],np.float32)
    original=Rotation.from_rotvec(rng.normal(size=(12,3))*.6).as_quat().reshape(4,3,4)
    changed=(Rotation.from_quat(original.reshape(-1,4))*Rotation.from_rotvec(rng.normal(size=(12,3))*.04)).as_quat().reshape(4,3,4)
    times=np.unique(np.r_[clock.astype(float),np.linspace(0,float(clock[-1]),37),np.nextafter(float(clock[1]),0.),np.nextafter(float(clock[1]),1.)])
    return clock,original,changed,times


@pytest.mark.parametrize('variant',['normal','antipodal','near_equal','scaled'])
def test_complete_scalar_native_interpolation_and_relative_rates(variant):
    clock,source,changed,times=fixture()
    if variant=='antipodal':source[::2]*=-1;changed[1::2]*=-1
    if variant=='near_equal':source[:]=source[0];changed[:]=changed[0];changed[1:,:,:3]+=1e-9
    if variant=='scaled':source*=1.+2e-6;changed*=1.-2e-6
    curve=CorrectionCurve(clock,source,times)
    scalar=lambda q:np.array([[NativeSupportSampler.value('rotation',clock,q[:,j],'LINEAR',float(t)) for j in range(3)] for t in times])
    np.testing.assert_allclose(curve.sample(changed),scalar(changed),atol=5e-15,rtol=0)
    correction=Rotation.from_quat(scalar(source).reshape(-1,4)).inv()*Rotation.from_quat(scalar(changed).reshape(-1,4))
    angles=np.rad2deg(correction.magnitude()).reshape(-1,3)
    rates=np.array([np.rad2deg((correction[3*i:3*i+3].inv()*correction[3*i+3:3*i+6]).magnitude())/(v-u)
                    for i,(u,v) in enumerate(zip(times[:-1],times[1:]))])
    actual=curve.evaluate(changed,[25]*3,[40]*3)
    np.testing.assert_allclose(actual['angles_degrees'],angles,atol=1e-12,rtol=0)
    np.testing.assert_allclose(actual['rates_degrees_s'],rates,atol=1e-8,rtol=1e-9)
    assert actual['rates_degrees_s'].shape==(len(times)-1,3)
    assert not actual['report']['continuous_time_verified']


def test_between_key_correction_speed_can_fail_when_native_keys_pass():
    clock,source,changed,_=fixture()
    times=np.unique(np.concatenate([np.linspace(float(a),float(b),33) for a,b in zip(clock[:-1],clock[1:])]))
    native=CorrectionCurve(clock,source,clock.astype(float)).evaluate(changed,[25]*3,[173.6]*3)
    dense=CorrectionCurve(clock,source,times).evaluate(changed,[25]*3,[173.6]*3)
    assert native['speed_rows'].min()>0
    assert dense['speed_rows'].min()<0
    assert dense['rates_degrees_s'].max()>native['rates_degrees_s'].max()+.4


def test_original_copy_and_complete_last_joint_neighbor():
    clock,source,changed,times=fixture();original=source.copy();c=CorrectionCurve(clock,source,times)
    source[:]=0
    np.testing.assert_array_equal(c.reference,original)
    result=c.evaluate(original,[25]*3,[40]*3)
    assert result['rates_degrees_s'].max()<1e-9
    altered=original.copy();altered[-1,-1]=Rotation.from_rotvec([1.,0,0]).as_quat()
    bad=c.evaluate(altered,[25]*3,[40]*3)
    assert bad['speed_rows'][-1,-1]<0


@pytest.mark.parametrize('fault',['clock_empty','clock_repeat','clock_nan','shape','times_repeat','times_outside','times_bool','quaternion_zero','quaternion_nan','budget','budget_bool'])
def test_invalid_complete_inputs_reject(fault):
    clock,source,changed,times=fixture();kwargs={}
    if fault=='clock_empty':clock=clock[:0]
    elif fault=='clock_repeat':clock[1]=clock[0]
    elif fault=='clock_nan':clock[1]=np.nan
    elif fault=='shape':source=source[...,0]
    elif fault=='times_repeat':times[1]=times[0]
    elif fault=='times_outside':times[-1]+=1
    elif fault=='times_bool':times=np.array([False,True])
    elif fault=='quaternion_zero':source[0,0]=0
    elif fault=='quaternion_nan':source[0,0,0]=np.nan
    elif fault=='budget':kwargs['maximum_working_bytes']=1
    else:kwargs['maximum_working_bytes']=True
    with pytest.raises(ValueError):CorrectionCurve(clock,source,times,**kwargs)


@pytest.mark.parametrize('caps,limits',[([0]*3,[40]*3),([181]*3,[40]*3),([25],[40]*3),([25]*3,[0]*3),([25]*3,[float('nan')]*3),([True]*3,[40]*3)])
def test_invalid_limits_reject(caps,limits):
    clock,source,changed,times=fixture()
    with pytest.raises(ValueError):CorrectionCurve(clock,source,times).evaluate(changed,caps,limits)
