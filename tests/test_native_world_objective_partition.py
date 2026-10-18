from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_world_objective_partition import partition_world_objective


def fixture():
    return [np.array([1.,-2.]),np.array([[0.,1.],[1.,0.]]),np.array([40,9,77,2]),
            np.array([.5,-1.,.2,-.4]),np.array([.4,-.7,-.1,-.3]),np.arange(1.,9.).reshape(4,2),[40]]


def test_complete_group_order_and_both_roles_are_preserved():
    r=partition_world_objective(*fixture())
    assert r['objective_row_ids'].tolist()==[9,77,2] and r['hard_row_ids'].tolist()==[40,77] and r['overlap_row_ids'].tolist()==[77]
    np.testing.assert_array_equal(r['objective_margins'],[1.,-2.,-1.,-.1,-.4])
    np.testing.assert_array_equal(r['objective_jacobian'],[[0,1],[1,0],[3,4],[5,6],[7,8]])
    np.testing.assert_array_equal(r['hard_passing_margins'],[.4,.2])
    assert r['report']['model_rows']==5 and r['report']['all_supplied_rows_have_objective_or_hard_role']
    assert not r['report']['quality_approved'] and not r['report']['release_approved']


def test_all_passing_rows_remain_hard_without_duplicate_objective_rows():
    a=fixture();a[3][:]=.4;a[4][:]=.3;r=partition_world_objective(*a)
    assert r['objective_jacobian'].shape==(2,2) and r['hard_row_ids'].tolist()==a[2].tolist() and not len(r['objective_row_ids'])


def test_all_failing_rows_remain_in_objective():
    a=fixture();a[3][:]=-1;a[4][:]=-2;a[6]=[];r=partition_world_objective(*a)
    assert r['objective_jacobian'].shape==(6,2) and not len(r['hard_row_ids']) and r['objective_row_ids'].tolist()==a[2].tolist()


def test_mixed_mode_row_is_never_discarded_from_either_role():
    a=fixture();a[3][0]=-.5;a[4][0]=.1;a[6]=[];r=partition_world_objective(*a)
    assert 40 in r['objective_row_ids'] and 40 in r['hard_row_ids']
    assert r['objective_margins'][2]==-.5 and r['hard_passing_margins'][0]==.1


def test_omitted_zero_cost_terms_are_zero_for_retained_feasible_linear_hard_constraints():
    rng=np.random.default_rng(42);n=90;c=5;raw=rng.uniform(-1.,1.,n);saved=raw+rng.uniform(-.1,.1,n);j=rng.normal(size=(n,c))
    args=[np.array([-.1,.2]),rng.normal(size=(2,c)),np.arange(n)+17,raw,saved,j,[]];r=partition_world_objective(*args)
    for _ in range(30):
        delta=rng.normal(size=c)*1e-5;hard=r['hard_indices'];change=j[hard]@delta
        ratio=np.max(np.divide(-change,.5*r['hard_passing_margins'],out=np.zeros_like(change),where=change<0),initial=0.)
        if ratio>1:delta/=ratio
        assert np.all(change/max(ratio,1)>=-.5*r['hard_passing_margins']-1e-15)
        full=np.maximum(-(args[0]+args[1]@delta),0).sum()+np.maximum(-(np.minimum(raw,saved)+j@delta),0).sum()
        reduced=np.maximum(-(r['objective_margins']+r['objective_jacobian']@delta),0).sum()
        assert reduced==pytest.approx(full,abs=1e-12)


def test_large_affected_population_is_not_truncated_to_model_row_limit():
    n=8072;g=1106;raw=np.ones(n);raw[42]=-1
    r=partition_world_objective(np.ones(g),np.zeros((g,1)),np.arange(n)+100,raw,raw.copy(),np.zeros((n,1)),[100])
    assert n+g>8192 and r['report']['supplied_rows']==8072 and r['report']['model_rows']==1107
    assert len(r['hard_row_ids'])==8071 and r['objective_row_ids'].tolist()==[142]
    assert set(r['hard_row_ids'])|set(r['objective_row_ids'])==set(range(100,100+n))


def test_768th_column_and_nonconsecutive_ids_are_preserved():
    a=fixture();a[1]=np.zeros((2,768));a[5]=np.zeros((4,768));a[5][:,-1]=[2,3,4,5]
    r=partition_world_objective(*a)
    assert r['objective_jacobian'].shape==(5,768) and r['objective_jacobian'][2:,-1].tolist()==[3,4,5]


def test_zero_margin_stays_hard_without_an_added_tolerance():
    a=fixture();a[3][0]=-0.;a[4][0]=0.;r=partition_world_objective(*a)
    assert r['hard_row_ids'][0]==40 and r['hard_passing_margins'][0]==0 and r['report']['physical_margin_tolerance_added']==0


def test_inputs_are_not_modified():
    a=fixture();before=copy.deepcopy(a);partition_world_objective(*a)
    for x,y in zip(a[:-1],before[:-1]):np.testing.assert_array_equal(x,y)
    assert a[-1]==before[-1]


def test_exact_array_and_population_budgets_are_admitted():
    a=fixture();r=partition_world_objective(*a);size=r['report']['estimated_array_bytes']
    assert partition_world_objective(*a,maximum_array_bytes=size,maximum_model_rows=5,maximum_hard_rows=2)['report']['estimated_array_bytes']==size
    for kwargs in [dict(maximum_array_bytes=size-1),dict(maximum_model_rows=4),dict(maximum_hard_rows=1)]:
        with pytest.raises(ValueError):partition_world_objective(*a,**kwargs)


@pytest.mark.parametrize('required',[[40,40],[999],[True],[-1],[1.5],(40,),[9],[77]])
def test_required_witnesses_must_be_explicit_present_and_already_pass_both_modes(required):
    a=fixture();a[-1]=required
    with pytest.raises(ValueError):partition_world_objective(*a)


@pytest.mark.parametrize('fault',['group_shape','group_columns','row_shape','row_columns','raw_shape','saved_shape','ids_shape','duplicate_ids','negative_ids','float_ids','bool_ids','huge_ids','nan_group','nan_row','nan_margin','complex_matrix','bool_matrix'])
def test_invalid_or_incomplete_arrays_rejected(fault):
    a=fixture()
    if fault=='group_shape':a[0]=a[0][:,None]
    elif fault=='group_columns':a[1]=np.zeros((2,3))
    elif fault=='row_shape':a[5]=a[5][:-1]
    elif fault=='row_columns':a[5]=a[5][:,:1]
    elif fault=='raw_shape':a[3]=a[3][:,None]
    elif fault=='saved_shape':a[4]=a[4][:-1]
    elif fault=='ids_shape':a[2]=a[2][:,None]
    elif fault=='duplicate_ids':a[2][0]=9
    elif fault=='negative_ids':a[2][0]=-1
    elif fault=='float_ids':a[2]=a[2].astype(float)
    elif fault=='bool_ids':a[2]=a[2].astype(bool)
    elif fault=='huge_ids':a[2]=np.array([2**64-1,9,77,2],dtype=np.uint64)
    elif fault=='nan_group':a[1][0,0]=np.nan
    elif fault=='nan_row':a[5][0,0]=np.nan
    elif fault=='nan_margin':a[4][0]=np.nan
    elif fault=='complex_matrix':a[5]=a[5].astype(complex)
    elif fault=='bool_matrix':a[5]=a[5].astype(bool)
    with pytest.raises(ValueError):partition_world_objective(*a)


@pytest.mark.parametrize('kwargs',[dict(maximum_model_rows=0),dict(maximum_model_rows=True),dict(maximum_model_rows=8193),dict(maximum_hard_rows=0),dict(maximum_hard_rows=8193),dict(maximum_array_bytes=0),dict(maximum_array_bytes=True),dict(maximum_array_bytes=64*1024**2+1)])
def test_invalid_budgets_rejected(kwargs):
    with pytest.raises(ValueError):partition_world_objective(*fixture(),**kwargs)
