"""Exact rational checks of outward dominance and complete root certificates."""
from pathlib import Path
from fractions import Fraction
import copy, itertools, sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_pair_surface_reduction import reduce,verify,dominance_bounds


def f(value):
    return Fraction.from_float(float(value))


def test_every_outward_bound_encloses_exact_represented_arithmetic():
    rng=np.random.default_rng(73)
    for magnitude in (1e-200,1e-12,1.,1e100):
        gaps=rng.normal(size=(2,9))*magnitude;jac=rng.normal(size=(2,9,4))*magnitude
        lo=np.array([-.02,-.001,0.,-.01]);hi=np.array([.01,.02,.02,0.])
        bounds=dominance_bounds(gaps,jac,lo,hi)
        for block,i,j in itertools.product(range(2),range(9),range(9)):
            exact=f(gaps[block,i])-f(gaps[block,j])
            for k in range(4):
                coefficient=f(jac[block,i,k])-f(jac[block,j,k])
                exact+=max(coefficient*f(lo[k]),coefficient*f(hi[k]))
            assert f(bounds[block,i,j])>=exact


def test_ties_with_opposing_slopes_keep_all_distinct_halfspaces():
    gaps=np.zeros(9);jac=np.array([1,1,1,-1,-1,-1,0,0,0])[:,None]
    result=reduce(gaps,jac,[0,9],[0.],[-1.],[1.],.02)
    assert result.retained.tolist()==[0,3,6] and result.report['duplicate_rows']==6
    assert result.report['dominated_rows']==0
    assert verify(result,gaps,jac,[0,9],[0.],[-1.],[1.],.02)['affine_equivalent']


def test_strict_dominance_preserves_all_extrema_and_singleton_witnesses():
    gaps=np.r_[np.arange(9)*.002, -.1];jac=np.zeros((10,2));jac[:,0]=1.;jac[:9,1]=np.arange(9)*.01
    result=reduce(gaps,jac,[0,9,10],[0.,0.],[-1.,-1.],[1.,1.],.02)
    assert result.retained.tolist()==[0,9] and result.report['dominated_rows']==8
    assert result.roots[9]==9
    for delta in itertools.product([-.02,0.,.02],repeat=2):
        all_gaps=gaps+jac@delta
        assert all_gaps.min()==pytest.approx(all_gaps[result.retained].min(),abs=1e-14)
        assert np.all(all_gaps[result.roots]<=all_gaps+1e-14)
    assert verify(result,gaps,jac,[0,9,10],[0.,0.],[-1.,-1.],[1.,1.],.02)['all_certificate_rows_checked']


def test_small_gap_advantage_does_not_hide_larger_opposing_slope():
    gaps=np.arange(9)*1e-8;jac=np.arange(9)[:,None]*-1.
    result=reduce(gaps,jac,[0,9],[0.],[-1.],[1.],.02)
    assert len(result.retained)==9 and result.report['dominated_rows']==0


def test_box_boundary_and_rounding_padding_do_not_claim_zero_width_dominance():
    gaps=np.zeros(9);jac=np.arange(9)[:,None]*1.
    result=reduce(gaps,jac,[0,9],[-1.],[-1.],[1.],.02)
    assert result.report['proof_delta_lower'][0]<0 and len(result.retained)==9


def test_overflow_disables_uncertain_dominance():
    gaps=np.array([[1e308,-1e308]]);jac=np.array([[[1e308],[-1e308]]])
    bounds=dominance_bounds(gaps,jac,[-.02],[.02])
    assert np.isinf(bounds[0,0,1]) and np.isinf(bounds[0,1,0])


@pytest.mark.parametrize('change',['input','root_cycle','cross_block','bound','digest','approval','other','kind'])
def test_corrupted_or_rebound_certificate_rejects(change):
    gaps=np.r_[np.arange(9)*.002,-.1];jac=np.zeros((10,1));settings=([0,9,10],[0.],[-1.],[1.],.02)
    result=reduce(gaps,jac,*settings)
    if change=='input':gaps=gaps.copy();gaps[3]+=1e-9
    elif change=='root_cycle':result.roots[0]=1
    elif change=='cross_block':result.roots[2]=9
    elif change=='bound':result.upper_bounds[1]=-1.
    elif change=='digest':result.report['affine_inputs_sha256']='0'*64
    elif change=='approval':result.report['quality_approved']=0
    elif change=='other':result.roots[9]=0;result.kinds[9]=2;result.report['retained_rows']-=1;result.report['dominated_rows']+=1
    elif change=='kind':result.kinds=result.kinds.astype(float)
    with pytest.raises(ValueError):verify(result,gaps,jac,*settings)


@pytest.mark.parametrize('settings',[dict(trust=True),dict(trust=.03),dict(offsets=[0,8,9]),
    dict(offsets=[0.,9.]),dict(value=[2.]),dict(gaps=[np.nan]*9),dict(lower=[1.]),dict(jacobian=np.zeros((8,1)))])
def test_invalid_full_population_and_box_settings_reject(settings):
    values=dict(gaps=np.zeros(9),jacobian=np.zeros((9,1)),offsets=[0,9],value=[0.],lower=[-1.],upper=[1.],trust=.02)
    with pytest.raises(ValueError):reduce(**dict(values,**settings))
