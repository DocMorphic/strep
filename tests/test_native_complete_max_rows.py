"""Complete populations, independent logsumexp/FD, exact gates and budgets."""
from pathlib import Path
import sys,hashlib
import numpy as np
import pytest
from scipy.special import logsumexp,softmax
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_scene_world_rows.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts')]
from native_complete_max_rows import CompleteMaxRows


def aggregate(values,jacobians=None,chunk=7,temperature=.03):
    columns=0 if jacobians is None else jacobians[0].shape[1]
    result=CompleteMaxRows([dict(id=f'g{i}',rows=len(v)) for i,v in enumerate(values)],derivative_columns=columns,temperature=temperature,maximum_chunk_rows=chunk)
    for start in range(0,max(map(len,values)),chunk):
        for group in reversed(range(len(values))):
            if start>=len(values[group]):continue
            result.append(group,start,values[group][start:start+chunk],jacobian=None if jacobians is None else jacobians[group][start:start+chunk])
    return result.finalize()


@pytest.mark.parametrize('chunk',[1,3,17,256])
def test_all_values_hashes_extrema_and_derivatives_match_complete_reference(chunk):
    rng=np.random.default_rng(13);values=[rng.normal(size=n) for n in [17,4,113]];jac=[rng.normal(size=(len(v),5)) for v in values]
    result=aggregate(values,jac,chunk=chunk)
    np.testing.assert_array_equal(result['exact_margins'],[-v.max() for v in values])
    np.testing.assert_allclose(result['smooth_margins'],[-.03*logsumexp(v/.03) for v in values],atol=2e-14,rtol=0)
    np.testing.assert_allclose(result['smooth_jacobian'],[-softmax(v/.03)@j for v,j in zip(values,jac)],atol=2e-13,rtol=0)
    assert result['report']['total_original_rows']==134 and result['report']['grouped_jacobian_bytes']==3*5*8
    for row,v in zip(result['report']['groups'],values):
        assert row['rows']==row['rows_seen']==len(v) and row['worst_row']==int(np.argmax(v)) and row['failed_rows']==int(np.count_nonzero(v>0))
        assert row['values_sha256']==hashlib.sha256(v.astype('<f8').tobytes()).hexdigest()
    assert not result['report']['quality_approved'] and not result['report']['release_approved']


def test_complete_smooth_chain_matches_every_independent_finite_difference_column():
    rng=np.random.default_rng(94);matrices=[rng.normal(size=(n,5)) for n in [11,37]];other=[rng.normal(size=a.shape) for a in matrices];x=rng.normal(size=5)*.1
    def measured(point):
        values=[np.sin(a@point)+.3*np.cos(b@point) for a,b in zip(matrices,other)]
        jac=[np.cos(a@point)[:,None]*a-.3*np.sin(b@point)[:,None]*b for a,b in zip(matrices,other)]
        return aggregate(values,jac,chunk=3)
    actual=measured(x)
    for column in range(5):
        delta=np.eye(5)[column]*1e-6;finite=(measured(x+delta)['smooth_margins']-measured(x-delta)['smooth_margins'])/2e-6
        np.testing.assert_allclose(actual['smooth_jacobian'][:,column],finite,atol=3e-7,rtol=3e-7)


def test_exact_pass_can_coexist_with_negative_stronger_smooth_guidance():
    result=aggregate([np.zeros(257)],chunk=13)
    assert result['report']['original_scalar_conditions_pass'] and result['report']['failed_exact_groups']==0
    assert result['exact_margins'][0]==0 and result['smooth_margins'][0]<0 and result['smooth_jacobian'] is None


def test_extreme_rescaling_retains_every_failed_row_and_earliest_exact_tie():
    values=np.array([-1e6,1e6,0.,1e6,1.,-0.]);jac=np.arange(18,dtype=float).reshape(6,3)
    result=aggregate([values],[jac],chunk=1,temperature=1e-9)
    assert result['report']['groups'][0]['worst_row']==1 and result['report']['failed_original_rows']==3
    np.testing.assert_allclose(result['smooth_jacobian'][0],-(jac[1]+jac[3])/2,atol=0,rtol=0)
    assert np.isfinite(result['smooth_margins']).all()


def test_incomplete_duplicate_gap_and_escaping_rows_never_yield_partial_success():
    p=CompleteMaxRows([dict(id='all',rows=3)],maximum_chunk_rows=3)
    p.append(0,0,[-.1])
    for start,values in [(0,[-.1]),(2,[-.1]),(1,[-.1]*3)]:
        with pytest.raises(ValueError):p.append(0,start,values)
    with pytest.raises(ValueError,match='Incomplete'):p.finalize()
    p.append(0,1,[-.2,.00001]);result=p.finalize()
    assert result['report']['groups'][0]['rows_seen']==3 and result['report']['failed_original_rows']==1
    with pytest.raises(ValueError,match='closed'):p.append(0,3,[-1.])


def test_inputs_results_and_group_metadata_do_not_alias_internal_state():
    groups=[dict(id='x',rows=2)];p=CompleteMaxRows(groups,derivative_columns=2);groups[0]['rows']=1
    values=np.array([-.1,-.2]);jac=np.array([[1.,2.],[3.,4.]])
    p.append(0,0,values,jacobian=jac);values[:]=999;jac[:]=0
    first=p.finalize();before=first['smooth_jacobian'].copy();first['smooth_jacobian'][:]=0;first['report']['groups'].clear()
    second=p.finalize();np.testing.assert_array_equal(second['smooth_jacobian'],before);assert len(second['report']['groups'])==1


def test_input_and_output_jacobian_budgets_are_complete_not_truncated():
    groups=[dict(id='a',rows=3),dict(id='b',rows=1)]
    with pytest.raises(ValueError):CompleteMaxRows(groups,derivative_columns=3,maximum_jacobian_bytes=47)
    p=CompleteMaxRows(groups,derivative_columns=3,maximum_chunk_rows=3,maximum_jacobian_bytes=48)
    with pytest.raises(ValueError):p.append(0,0,np.zeros(3),jacobian=np.zeros((3,3)))
    p.append(0,0,np.zeros(2),jacobian=np.zeros((2,3)));p.append(0,2,np.zeros(1),jacobian=np.zeros((1,3)))
    p.append(1,0,np.zeros(1),jacobian=np.zeros((1,3)));assert p.finalize()['smooth_jacobian'].nbytes==48


@pytest.mark.parametrize('fault',['nan','bool','shape','magnitude','integer_min','missing_jac','bad_jac','value_mode_jac','group_bool','offset_bool'])
def test_bad_chunks_fail_without_committing_any_original_row(fault):
    columns=0 if fault=='value_mode_jac' else 2;p=CompleteMaxRows([dict(id='g',rows=1)],derivative_columns=columns)
    group=0;offset=0;values=np.array([0.]);jac=None if not columns else np.zeros((1,2))
    if fault=='nan':values[0]=np.nan
    elif fault=='bool':values=np.array([False])
    elif fault=='shape':values=np.zeros((1,1))
    elif fault=='magnitude':values[0]=1e6+1
    elif fault=='integer_min':values=np.array([np.iinfo(np.int64).min])
    elif fault=='missing_jac':jac=None
    elif fault=='bad_jac':jac=np.full((1,2),np.nan)
    elif fault=='value_mode_jac':jac=np.zeros((1,2))
    elif fault=='group_bool':group=True
    else:offset=True
    with pytest.raises(ValueError):p.append(group,offset,values,jacobian=jac)
    p.append(0,0,[-.1],jacobian=None if not columns else np.zeros((1,2)))
    assert p.finalize()['report']['groups'][0]['rows_seen']==1


@pytest.mark.parametrize('groups,settings',[
    ([],{}),([dict(id='same',rows=1)]*2,{}),([dict(id='g',rows=True)],{}),
    ([dict(id='g',rows=2000001)],{}),([dict(id='a',rows=1500000),dict(id='b',rows=1500000)],{}),
    ([dict(id='g',rows=1)],dict(temperature=0)),([dict(id='g',rows=1)],dict(derivative_columns=769)),
    ([dict(id='g',rows=1)],dict(maximum_chunk_rows=0)),([dict(id='g',rows=1)],dict(maximum_jacobian_bytes=67108865)),
])
def test_invalid_complete_partitions_and_settings_reject(groups,settings):
    with pytest.raises(ValueError):CompleteMaxRows(groups,**settings)
