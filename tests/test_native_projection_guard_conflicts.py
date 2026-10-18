from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_projection_guard_conflicts import find_equal_row_conflicts as find


def fixture():return np.array([[1.,2.,3.],[2.,0.,1.]]),np.array([.2,.4]),np.array([[1.,2.,3.]]),np.array([.3])


def test_complete_rows_and_bounds_are_compared_against_independent_double_loop():
    g,u,r,l=fixture();g=np.vstack([g,g[0],g[1]]);u=np.r_[u,.1,.8];r=np.vstack([r,g[1],g[0]]);l=np.r_[l,.6,.05]
    expected=[(j,i) for i in range(len(r)) for j in range(len(g)) if all(g[j,k]==r[i,k] for k in range(g.shape[1])) and l[i]>u[j]]
    result=find(g,u,r,l);assert result['pairs'].tolist()==[list(p) for p in expected]
    np.testing.assert_array_equal(result['bound_gaps'],[l[i]-u[j] for j,i in expected]);assert result['report']['complete_pair_checks']==12
    assert result['report']['all_rows_and_columns_retained'] and not result['report']['guards_removed'] and not result['report']['nonlinear_infeasibility_proven']


def test_equal_bounds_touch_but_do_not_contradict():
    g,u,r,l=fixture();l[:]=u[0];assert find(g,u,r,l)['pairs'].shape==(0,2)


def test_near_equal_coefficients_are_never_collapsed():
    g,u,r,l=fixture();r[0,-1]=np.nextafter(r[0,-1],np.inf);assert len(find(g,u,r,l)['pairs'])==0


def test_last_of_768_columns_prevents_a_false_conflict():
    g=np.zeros((2,768));r=np.zeros((1,768));g[1,-1]=np.nextafter(0.,1.);result=find(g,np.zeros(2),r,np.ones(1))
    assert result['pairs'].tolist()==[[0,0]] and result['report']['columns']==768


def test_signed_zeros_and_mixed_exact_integer_float_inputs():
    g=np.array([[0,2]],np.int32);r=np.array([[-0.,2.]],np.float32);assert find(g,np.zeros(1),r,np.ones(1))['pairs'].tolist()==[[0,0]]


def test_every_duplicate_identity_is_retained_in_declared_order():
    result=find(np.ones((3,2)),np.zeros(3),np.ones((2,2)),np.ones(2));assert result['pairs'].tolist()==[[j,i] for i in range(2) for j in range(3)]


def test_zero_rows_report_conflicting_supplied_bounds_without_feasibility_claim():
    assert find(np.zeros((1,3)),np.array([-.1]),np.zeros((1,3)),np.array([0.]))['bound_gaps'].tolist()==[.1]


@pytest.mark.parametrize('sizes',[(0,2),(2,0),(0,0)])
def test_empty_populations_preserve_explicit_columns(sizes):
    g,r=sizes;result=find(np.zeros((g,7)),np.zeros(g),np.zeros((r,7)),np.ones(r));assert result['pairs'].shape==(0,2) and result['report']['columns']==7


def test_input_arrays_including_strided_views_remain_unchanged():
    g,u,r,l=fixture();g=g[:,::-1];r=r[:,::-1];arrays=[a.copy() for a in [g,u,r,l]];find(g,u,r,l)
    for before,after in zip(arrays,[g,u,r,l]):np.testing.assert_array_equal(before,after)


def test_exact_common_scaling_and_column_permutation_preserve_identities():
    g,u,r,l=fixture();expected=find(g,u,r,l)['pairs'];result=find(g[:,[2,0,1]]*8,u*8,r[:,[2,0,1]]*8,l*8)
    np.testing.assert_array_equal(result['pairs'],expected);np.testing.assert_array_equal(result['bound_gaps'],find(g,u,r,l)['bound_gaps']*8)


def test_proportional_rows_are_explicitly_outside_this_exact_equal_detector():
    g,u,r,l=fixture();assert len(find(g,u,2*r,2*l)['pairs'])==0


@pytest.mark.parametrize('bad',[np.nan,np.inf,-np.inf,1e13])
def test_invalid_values_in_final_coefficient_are_rejected(bad):
    g,u,r,l=fixture();g[-1,-1]=bad
    with pytest.raises(ValueError,match='finite'):find(g,u,r,l)


@pytest.mark.parametrize('which',[0,1,2,3])
def test_boolean_or_complex_arrays_rejected(which):
    a=list(fixture());a[which]=a[which].astype(bool if which%2 else complex)
    with pytest.raises(ValueError):find(*a)


@pytest.mark.parametrize('change',['missing_bound','wrong_columns','too_many_columns','list_input'])
def test_malformed_complete_inputs_rejected(change):
    g,u,r,l=fixture()
    if change=='missing_bound':u=u[:-1]
    elif change=='wrong_columns':r=r[:,:-1]
    elif change=='too_many_columns':g=np.zeros((1,769));r=g.copy();u=np.zeros(1)
    else:g=g.tolist()
    with pytest.raises(ValueError):find(g,u,r,l)


@pytest.mark.parametrize('option',[dict(maximum_pair_checks=1),dict(maximum_working_bytes=1),dict(maximum_matches=0),dict(maximum_pair_checks=True),dict(maximum_working_bytes=64*1024**2+1)])
def test_budget_admission_rejects_without_partial_result(option):
    with pytest.raises(ValueError):find(*fixture(),**option)


def test_output_limit_rejects_instead_of_truncating_duplicate_matches():
    with pytest.raises(ValueError,match='output'):find(np.ones((3,2)),np.zeros(3),np.ones((2,2)),np.ones(2),maximum_matches=5)


@pytest.mark.parametrize('which',[1,3])
def test_nonfinite_final_bound_rejected(which):
    a=list(fixture());a[which][-1]=np.nan
    with pytest.raises(ValueError,match='finite'):find(*a)


def test_single_column_and_one_ulp_conflicting_bound_are_retained():
    result=find(np.ones((1,1)),np.ones(1),np.ones((1,1)),np.array([np.nextafter(1.,2.)]))
    assert result['pairs'].tolist()==[[0,0]] and result['bound_gaps'][0]>0
