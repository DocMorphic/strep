"""Complete empirical endpoint envelopes and source/mutation rejection."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_empirical_material_margins import build, validate

MODEL = 'a'*64


def inputs():
    return dict(actual_gaps_m=np.array([[.001, -.002, .003], [.002, -.003, .004]]),
        affine_gaps_m=np.array([[.0011, -.0022, .0033], [.0024, -.0025, .0039]]),
        material_model_sha256=MODEL, sample_sha256=['b'*64, 'c'*64],
        required_sample_sha256=['b'*64, 'c'*64], row_indices=[0, 1, 2], required_rows=3)


def test_complete_worst_loss_is_directional_and_extra_buffer_is_explicit():
    kw=inputs();kw['extra_buffer_m']=1e-7;p=build(**kw)
    expected=np.maximum(0., (kw['affine_gaps_m']-kw['actual_gaps_m']).max(axis=0))+1e-7
    np.testing.assert_array_equal(p.margins_m, expected)
    assert p.margins_m[0] == kw['affine_gaps_m'][1,0]-kw['actual_gaps_m'][1,0]+1e-7
    assert p.margins_m[1] == kw['affine_gaps_m'][1,1]-kw['actual_gaps_m'][1,1]+1e-7
    assert not p.report['nonlinear_certificate'] and not p.report['continuous_certificate']
    assert not p.report['quality_approved'] and not p.report['release_approved']
    observed,report=validate(p, material_model_sha256=MODEL, required_rows=3)
    np.testing.assert_array_equal(observed, expected);assert report == p.report


def test_improving_actual_gaps_need_no_error_margin_and_zero_is_valid():
    kw=inputs();kw['affine_gaps_m']=kw['actual_gaps_m']-.0001;p=build(**kw)
    np.testing.assert_array_equal(p.margins_m, np.zeros(3))


def test_snapshots_and_validation_returns_do_not_alias_caller_or_policy():
    kw=inputs();p=build(**kw);original=copy.deepcopy(p.report)
    kw['actual_gaps_m'].fill(9.);kw['sample_sha256'].clear();kw['row_indices'].clear()
    margin,report=validate(p, material_model_sha256=MODEL, required_rows=3)
    margin.fill(8.);report['sample_sha256'].clear()
    assert p.report==original and not np.any(p.actual_gaps_m==9.) and not np.any(p.margins_m==8.)
    assert not p.margins_m.flags.writeable and not p.actual_gaps_m.flags.writeable


@pytest.mark.parametrize('fault', ['source','uppercase-source','sample-missing','sample-order','sample-repeat',
    'sample-invalid','row-missing','row-order','row-bool','rows-bool','rows-zero','rows-over',
    'samples-budget','rows-budget','elements-budget','budget-bool','buffer-negative','buffer-nan',
    'buffer-large','buffer-bool','actual-shape','affine-shape','actual-nan','affine-inf',
    'actual-bool','actual-string','overflow','error-large'])
def test_invalid_or_incomplete_populations_reject_whole(fault):
    k=inputs()
    if fault=='source':k['material_model_sha256']='x'
    elif fault=='uppercase-source':k['material_model_sha256']='A'*64
    elif fault=='sample-missing':k['sample_sha256'].pop()
    elif fault=='sample-order':k['sample_sha256'].reverse()
    elif fault=='sample-repeat':k['sample_sha256']=k['required_sample_sha256']=['b'*64]*2
    elif fault=='sample-invalid':k['sample_sha256']=k['required_sample_sha256']=['b'*64,'x']
    elif fault=='row-missing':k['row_indices'].pop()
    elif fault=='row-order':k['row_indices'].reverse()
    elif fault=='row-bool':k['row_indices'][0]=False
    elif fault=='rows-bool':k['required_rows']=True
    elif fault=='rows-zero':k['required_rows']=0
    elif fault=='rows-over':k['required_rows']=4097
    elif fault=='samples-budget':k['maximum_samples']=1
    elif fault=='rows-budget':k['maximum_rows']=2
    elif fault=='elements-budget':k['maximum_elements']=5
    elif fault=='budget-bool':k['maximum_samples']=True
    elif fault=='buffer-negative':k['extra_buffer_m']=-1e-9
    elif fault=='buffer-nan':k['extra_buffer_m']=np.nan
    elif fault=='buffer-large':k['extra_buffer_m']=.00100001
    elif fault=='buffer-bool':k['extra_buffer_m']=False
    elif fault=='actual-shape':k['actual_gaps_m']=k['actual_gaps_m'][:1]
    elif fault=='affine-shape':k['affine_gaps_m']=k['affine_gaps_m'][:,:2]
    elif fault=='actual-nan':k['actual_gaps_m'][0,0]=np.nan
    elif fault=='affine-inf':k['affine_gaps_m'][0,0]=np.inf
    elif fault=='actual-bool':k['actual_gaps_m']=np.zeros((2,3),bool)
    elif fault=='actual-string':k['actual_gaps_m']=np.full((2,3),'1')
    elif fault=='overflow':k['actual_gaps_m'][0,0]=-1e308;k['affine_gaps_m'][0,0]=1e308
    elif fault=='error-large':k['affine_gaps_m'][0,0]=1.
    with pytest.raises(ValueError):build(**k)


def test_budget_rejection_precedes_endpoint_conversion():
    class Forbidden:
        def __array__(self, *args, **kwargs):pytest.fail('Complete population budget must reject first')
    k=inputs();k['maximum_elements']=5;k['actual_gaps_m']=k['affine_gaps_m']=Forbidden()
    with pytest.raises(ValueError):build(**k)


def test_exact_whole_population_budget_and_float32_snapshot_are_supported():
    samples=[f'{i:064x}' for i in range(32)]
    actual=np.zeros((32,4096),np.float32);affine=actual.copy();affine[-1,-1]=1e-6
    p=build(actual,affine,material_model_sha256=MODEL,sample_sha256=samples,
        required_sample_sha256=samples.copy(),row_indices=list(range(4096)),required_rows=4096)
    assert p.actual_gaps_m.dtype==np.float64 and p.margins_m[-1]==float(affine[-1,-1])
    assert p.report['samples']==32 and p.report['required_rows']==4096
    assert np.count_nonzero(p.margins_m)==1


@pytest.mark.parametrize('fault', ['type','source','rows','margin','actual','affine','sample',
    'report-margin','report-digest','report-scope','report-bool','report-extra'])
def test_stale_or_mutated_policy_rejected(fault):
    p=build(**inputs());model=MODEL;rows=3
    if fault=='type':p=p.report
    elif fault=='source':model='d'*64
    elif fault=='rows':rows=2
    elif fault in ('margin','actual','affine'):
        a=getattr(p, {'margin':'margins_m','actual':'actual_gaps_m','affine':'affine_gaps_m'}[fault])
        a.setflags(write=True);a.flat[0]+=1e-8
    elif fault=='sample':p.report['sample_sha256'][0]='d'*64
    elif fault=='report-margin':p.report['margins_m'][0]+=1e-8
    elif fault=='report-digest':p.report['actual_gaps_sha256']='e'*64
    elif fault=='report-scope':p.report['nonlinear_certificate']=True
    elif fault=='report-bool':p.report['samples']=True
    elif fault=='report-extra':p.report['unknown']='x'
    with pytest.raises(ValueError):validate(p, material_model_sha256=model, required_rows=rows)
