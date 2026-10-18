from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_motion_progress import compare_motion_rows


def modes(values):return {m:np.array(values,float) for m in ('raw_world','encoded_world')}


def test_fixed_worst_row_allows_strict_improvement_elsewhere():
    r=compare_motion_rows(modes([-10,-2,1]),modes([-10,-1,1]),[2])
    assert r['sampled_world_progress'] and r['rows_per_mode']==3
    for c in r['comparisons'].values():
        assert c['before_peak']==c['after_peak']==10 and c['squared_improvement']==3 and c['new_failures']==c['required_failures']==0
    assert not r['quality_approved'] and not r['release_approved']


def test_new_failure_rejected_even_with_better_peak_and_score():
    r=compare_motion_rows(modes([-10,-2,1]),modes([-9,-1,-.000001]),[])
    assert not r['sampled_world_progress']
    assert all(c['new_failures']==1 and c['squared_improvement']>0 for c in r['comparisons'].values())


def test_lost_repaired_witness_rejected_exactly():
    r=compare_motion_rows(modes([-10,-2,0]),modes([-9,-1,-1e-15]),[2])
    assert not r['sampled_world_progress'] and all(c['required_failures']==1 for c in r['comparisons'].values())
    assert r['physical_margin_tolerance_added']==0


def test_peak_regression_rejected_despite_lower_total_error():
    r=compare_motion_rows(modes([-10,-10,1]),modes([-11,0,1]),[2])
    assert not r['sampled_world_progress'] and r['comparisons']['raw_world']['squared_improvement']==79


def test_saved_representation_must_improve_independently():
    before=modes([-10,-2,1]);after=modes([-10,-1,1]);after['encoded_world']=before['encoded_world'].copy()
    r=compare_motion_rows(before,after,[])
    assert r['comparisons']['raw_world']['progress'] and not r['sampled_world_progress']


def test_reports_exact_repair_identities_in_both_modes():
    r=compare_motion_rows(modes([-3,-2,1]),modes([0,-1,.5]),[2])
    assert r['sampled_world_progress'] and all(c['repaired_rows']==[0] and c['after_failed']==1 for c in r['comparisons'].values())


def test_no_error_improvement_is_not_progress():
    assert not compare_motion_rows(modes([1.,0.]),modes([2.,1.]),[])['sampled_world_progress']


def test_threshold_is_strict_and_does_not_change_margin_decisions():
    r=compare_motion_rows(modes([-2.,1.]),modes([-1.,1.]),[],minimum_squared_improvement=3.)
    assert not r['sampled_world_progress']


def test_signed_zero_is_a_pass_not_a_negative_margin():
    r=compare_motion_rows(modes([-2.,0.]),modes([-1.,-0.]),[1])
    assert r['sampled_world_progress'] and r['comparisons']['raw_world']['required_failures']==0


def test_input_values_and_required_order_unchanged():
    before=modes([-3,-2,1,2]);after=modes([-2,-1,.5,1]);old=copy.deepcopy(before);new=copy.deepcopy(after);required=[3,2]
    compare_motion_rows(before,after,required)
    for m in before:np.testing.assert_array_equal(before[m],old[m]);np.testing.assert_array_equal(after[m],new[m])
    assert required==[3,2]


@pytest.mark.parametrize('change',['missing','extra','mismatched','nonfinite','complex','bool','matrix','empty','too_large'])
def test_rejects_incomplete_or_invalid_mode_population(change):
    before=modes([-3,-2,1]);after=modes([-2,-1,1])
    if change=='missing':del after['encoded_world']
    elif change=='extra':after['extra']=np.ones(3)
    elif change=='mismatched':after['encoded_world']=np.ones(2)
    else:
        after['encoded_world']={'nonfinite':np.array([0,1,np.nan]),'complex':np.ones(3,dtype=complex),
            'bool':np.ones(3,dtype=bool),'matrix':np.ones((1,3)),'empty':np.empty(0),'too_large':np.array([0,0,1e7])}[change]
    with pytest.raises(ValueError):compare_motion_rows(before,after,[])


@pytest.mark.parametrize('required',[[2,2],[-1],[3],[True],[1.5],(2,)])
def test_rejects_invalid_repair_identities(required):
    with pytest.raises(ValueError):compare_motion_rows(modes([-3,-2,1]),modes([-2,-1,1]),required)


def test_baseline_must_already_pass_its_required_witnesses():
    with pytest.raises(ValueError):compare_motion_rows(modes([-3,-2,1]),modes([-2,-1,1]),[0])


@pytest.mark.parametrize('kwargs',[dict(maximum_rows=2),dict(maximum_rows=True),dict(maximum_input_bytes=95),
    dict(maximum_input_bytes=0),dict(minimum_squared_improvement=-1),dict(minimum_squared_improvement=float('nan')),
    dict(minimum_squared_improvement=True)])
def test_rejects_invalid_or_incomplete_budgets(kwargs):
    with pytest.raises(ValueError):compare_motion_rows(modes([-3,-2,1]),modes([-2,-1,1]),[],**kwargs)


def test_exact_complete_input_budget_is_admitted():
    assert compare_motion_rows(modes([-3,-2,1]),modes([-2,-1,1]),[],maximum_input_bytes=96)['sampled_world_progress']
