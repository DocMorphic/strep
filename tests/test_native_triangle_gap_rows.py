from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_triangle_gap_rows as module
from native_support_gap import triangle_support_gaps


def sample(pairs=3,columns=5):
    rng=np.random.default_rng(273)
    a=rng.normal(size=(pairs,3,3))*.003;b=rng.normal(size=a.shape)*.003
    n=np.tile([1.,0.,0.],(pairs,1));ja=rng.normal(size=a.shape+(columns,))*.1;jb=rng.normal(size=ja.shape)*.1
    return a,b,n,ja,jb


def test_canonical_rows_are_byte_identical_to_original_kernel():
    a,b,n,ja,jb=sample();old=triangle_support_gaps(a,b,n,temperature_m=.01)
    result=module.triangle_gap_rows(a,b,n,left_jacobian=ja,right_jacobian=jb,temperature_m=.01)
    assert result['exact_margins'].tobytes()==((old['projected_gap_m']-2e-5)/.01).tobytes()
    assert result['smooth_margins'].tobytes()==((old['smooth_gap_m']-2e-5)/.01).tobytes()
    assert np.all(result['smooth_margins']<=result['exact_margins'])
    assert not result['report']['quality_approved'] and not result['report']['release_approved']


def test_both_actor_chains_match_independent_nonlinear_column_differences():
    a,b,n,ja,jb=sample();result=module.triangle_gap_rows(a,b,n,left_jacobian=ja,right_jacobian=jb,temperature_m=.01)
    for column in range(ja.shape[-1]):
        step=1e-7
        plus=module.triangle_gap_rows(a+step*ja[...,column],b+step*jb[...,column],n,temperature_m=.01)
        minus=module.triangle_gap_rows(a-step*ja[...,column],b-step*jb[...,column],n,temperature_m=.01)
        finite=(plus['smooth_margins']-minus['smooth_margins'])/(2*step)
        np.testing.assert_allclose(result['jacobian'][:,column],finite,rtol=1e-6,atol=2e-8)


def test_common_self_pair_translation_chains_accumulate_and_cancel():
    a,b,n,ja,jb=sample();ja.fill(0);jb.fill(0);ja[...,0]=[1.,0.,0.];jb[...,0]=[1.,0.,0.]
    result=module.triangle_gap_rows(a,b,n,left_jacobian=ja,right_jacobian=jb)
    np.testing.assert_allclose(result['jacobian'],0,atol=3e-14,rtol=0)


def test_last_pair_vertex_and_768th_column_survive():
    a=np.zeros((3,3,3));b=a+.1;n=np.tile([1.,0.,0.],(3,1));j=np.zeros(a.shape+(768,));j[-1,-1,0,-1]=3.
    result=module.triangle_gap_rows(a,b,n,right_jacobian=j)
    assert result['jacobian'].shape==(3,768)
    assert result['jacobian'][-1,-1]==pytest.approx(100.)
    assert np.count_nonzero(result['jacobian'])==1 and result['report']['rows']==3


def test_constant_side_and_value_only_modes_are_explicit():
    a,b,n,ja,jb=sample()
    left=module.triangle_gap_rows(a,b,n,left_jacobian=ja)
    right=module.triangle_gap_rows(a,b,n,right_jacobian=jb)
    both=module.triangle_gap_rows(a,b,n,left_jacobian=ja,right_jacobian=jb)
    np.testing.assert_allclose(both['jacobian'],left['jacobian']+right['jacobian'])
    value=module.triangle_gap_rows(a,b,n);assert value['jacobian'] is None and value['report']['columns']==0


def test_complete_budget_rejects_before_kernel(monkeypatch):
    a,b,n,ja,jb=sample();monkeypatch.setattr(module,'triangle_support_gaps',lambda *a,**k:pytest.fail('kernel before admission'))
    with pytest.raises(ValueError,match='budget'):module.triangle_gap_rows(a,b,n,left_jacobian=ja,right_jacobian=jb,maximum_array_bytes=1)


def test_input_arrays_are_unchanged():
    arrays=sample();before=[v.copy() for v in arrays]
    module.triangle_gap_rows(*arrays[:3],left_jacobian=arrays[3],right_jacobian=arrays[4])
    for a,b in zip(arrays,before):np.testing.assert_array_equal(a,b)


@pytest.mark.parametrize('kind',['empty','count','right_shape','normal_shape','nonunit','nan','bool','complex','huge','jac_shape','column_mismatch','zero_columns','too_many_columns','jac_nan','jac_bool'])
def test_invalid_complete_inputs_reject(kind):
    a,b,n,ja,jb=sample()
    if kind=='empty':a=a[:0];b=b[:0];n=n[:0]
    elif kind=='count':a=np.zeros((module.MAXIMUM_PAIRS+1,3,3));b=a.copy();n=np.tile([1.,0.,0.],(len(a),1));ja=jb=None
    elif kind=='right_shape':b=b[:,:2]
    elif kind=='normal_shape':n=n[0]
    elif kind=='nonunit':n*=2
    elif kind=='nan':a[0,0,0]=np.nan
    elif kind=='bool':a=a.astype(bool)
    elif kind=='complex':b=b.astype(complex)
    elif kind=='huge':a[0,0,0]=1e6+1
    elif kind=='jac_shape':ja=ja[:,:2]
    elif kind=='column_mismatch':jb=jb[...,:2]
    elif kind=='zero_columns':ja=ja[...,:0]
    elif kind=='too_many_columns':ja=np.zeros(a.shape+(769,))
    elif kind=='jac_nan':ja[0,0,0,0]=np.nan
    elif kind=='jac_bool':jb=jb.astype(bool)
    with pytest.raises(ValueError):module.triangle_gap_rows(a,b,n,left_jacobian=ja,right_jacobian=jb)


@pytest.mark.parametrize('field,value',[('minimum_gap_m',-.1),('minimum_gap_m',True),('minimum_gap_m',.2),('length_scale_m',0),('length_scale_m',float('inf')),('temperature_m',True),('temperature_m',0),('temperature_m',float('nan')),('maximum_array_bytes',0),('maximum_array_bytes',True),('maximum_array_bytes',64*1024**2+1)])
def test_invalid_scalar_policy_rejects(field,value):
    with pytest.raises(ValueError):module.triangle_gap_rows(*sample()[:3],**{field:value})
