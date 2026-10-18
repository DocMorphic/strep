import copy
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_temporal_failure_coverage import temporal_failure_coverage


def fixture():
    return np.arange(6.),[0,5],[
        dict(row=100,times_s=[1.],weight=4.),
        dict(row=101,times_s=[1.5],weight=3.),
        dict(row=102,times_s=[2.],weight=5.),
        dict(row=103,times_s=[3.5],weight=1.),
        dict(row=104,times_s=[4.],weight=8.)]


def test_complete_weights_and_unselected_candidates():
    args=fixture();r=temporal_failure_coverage(*args)
    assert r['candidate_keys']==[1,2,3,4] and r['selected_peaks']==[4,2,1]
    assert [s['newly_covered_weight'] for s in r['steps']]==[9.,8.,4.]
    np.testing.assert_array_equal(r['coverage'],[
        [1,1,0,0,0],[0,1,1,0,0],[0,0,0,1,0],[0,0,0,1,1]])
    assert r['row_ids']==[100,101,102,103,104] and r['covered_rows']==r['row_ids'] and r['uncovered_rows']==[]
    assert r['report']['all_rows_and_candidates_retained'] and not r['report']['quality_approved']


def test_initial_block_is_scheduling_context_not_repair():
    r=temporal_failure_coverage(*fixture(),initial_peaks=[1])
    assert r['selected_peaks']==[1,4,2] and r['initially_covered_rows']==[100,101]
    assert r['steps'][0]['initial'] and not r['steps'][1]['initial']
    assert r['report']['rows']==5 and not r['report']['release_approved']


def test_original_frozen_key_is_structurally_uncovered():
    clock,_,rows=fixture();r=temporal_failure_coverage(clock,[0,2,5],rows)
    assert r['uncovered_rows']==[102] and r['candidate_keys']==[1,3,4]
    assert r['report']['original_frozen_keys']==[0,2,5]


def test_all_keys_frozen_retains_every_row():
    clock,_,rows=fixture();r=temporal_failure_coverage(clock,list(range(6)),rows)
    assert r['coverage'].shape==(0,5) and r['selected_peaks']==[] and r['uncovered_rows']==r['row_ids']


def test_tie_uses_lowest_native_key_and_preserves_input_row_order():
    rows=[dict(row=9,times_s=[3.],weight=1.),dict(row=2,times_s=[1.],weight=1.)]
    r=temporal_failure_coverage(np.arange(5.),[0,4],rows)
    assert r['selected_peaks']==[1,3] and r['covered_rows']==[9,2]


def test_independent_nonuniform_scalar_impulses_cover_all_stencils():
    rng=np.random.default_rng(19);clock=np.cumsum(rng.uniform(.01,.3,18));frozen=[0,7,17]
    rows=[]
    for i in range(80):
        times=sorted(rng.uniform(clock[0],clock[-1],1+i%3).tolist())
        rows.append(dict(row=1000+i,times_s=times,weight=float(i+1)))
    rows += [dict(row=2000+i,times_s=[float(t)],weight=1.) for i,t in enumerate(clock)]
    r=temporal_failure_coverage(clock,frozen,rows)
    for k,peak in enumerate(r['candidate_keys']):
        impulse=np.zeros(len(clock));impulse[peak]=1.
        expected=[np.any(np.interp(row['times_s'],clock,impulse)!=0) for row in rows]
        np.testing.assert_array_equal(r['coverage'][k],expected)
    assert set(r['covered_rows'])|set(r['uncovered_rows'])=={x['row'] for x in rows}


def test_exact_keys_and_adjacent_representable_times_are_not_rounded():
    stamps=[0.,np.nextafter(0.,1.),np.nextafter(1.,0.),1.,np.nextafter(1.,2.),np.nextafter(2.,1.),2.]
    rows=[dict(row=i,times_s=[float(t)],weight=1.) for i,t in enumerate(stamps)]
    r=temporal_failure_coverage([0.,1.,2.],[0,2],rows)
    assert r['coverage'].tolist()==[[False,True,True,True,True,True,False]]


def test_three_sample_union_and_large_stable_row_identity():
    rows=[dict(row=2**80,times_s=[0.,2.,4.],weight=1.)]
    r=temporal_failure_coverage(np.arange(5.),[0,4],rows)
    assert r['candidate_keys']==[1,2,3] and r['coverage'].ravel().tolist()==[False,True,False]
    assert r['covered_rows']==[2**80]


def test_inputs_are_not_mutated():
    args=fixture();saved=copy.deepcopy(args);initial=[3]
    temporal_failure_coverage(*args,initial_peaks=initial)
    np.testing.assert_array_equal(args[0],saved[0]);assert args[1:]==saved[1:] and initial==[3]


@pytest.mark.parametrize('clock',[[0,1],[0,1,1],[2,1,0],[0,np.nan,2],[0,np.inf,2],
                                  [False,True,True],['0','1','2'],[-1e308,0,1e308],[[0,1,2]]])
def test_rejects_invalid_clock(clock):
    with pytest.raises(ValueError):temporal_failure_coverage(clock,[0,2],[dict(row=1,times_s=[1.],weight=1.)])


@pytest.mark.parametrize('frozen',[[0],[5],[0,5,5],[5,0],[0,True,5],[0,6],[0,1.5,5],(0,5)])
def test_rejects_invalid_original_locks(frozen):
    clock,_,rows=fixture()
    with pytest.raises(ValueError):temporal_failure_coverage(clock,frozen,rows)


@pytest.mark.parametrize('change',[
    dict(row=-1),dict(row=True),dict(times_s=[]),dict(times_s=[1.,1.]),dict(times_s=[2.,1.]),
    dict(times_s=[-1.]),dict(times_s=[6.]),dict(times_s=[float('nan')]),dict(times_s=[True]),
    dict(times_s=[0.,1.,2.,3.]),dict(weight=0.),dict(weight=-1.),dict(weight=float('inf')),
    dict(weight=True),dict(weight=1e13),dict(unexpected=1)])
def test_rejects_incomplete_or_invalid_stencil(change):
    clock,frozen,rows=fixture();rows[0].update(change)
    with pytest.raises(ValueError):temporal_failure_coverage(clock,frozen,rows)


@pytest.mark.parametrize('initial',[[0],[5],[1,1],[True],[2.5],{1}])
def test_rejects_invalid_initial_blocks(initial):
    with pytest.raises(ValueError):temporal_failure_coverage(*fixture(),initial_peaks=initial)


@pytest.mark.parametrize('budget',[True,0,19,8*1024**2+1])
def test_budget_rejection_never_prunes(budget):
    with pytest.raises(ValueError):temporal_failure_coverage(*fixture(),maximum_cells=budget)


def test_exact_complete_cell_budget_is_admitted():
    assert temporal_failure_coverage(*fixture(),maximum_cells=20)['coverage'].size==20


def test_duplicate_and_empty_population_rejected():
    clock,frozen,rows=fixture();rows.append(copy.deepcopy(rows[0]))
    for invalid in [rows,[],tuple(rows)]:
        with pytest.raises(ValueError):temporal_failure_coverage(clock,frozen,invalid)


def test_candidate_budget_is_complete_not_top_scored_subset():
    with pytest.raises(ValueError):
        temporal_failure_coverage(np.arange(515.),[0,514],[dict(row=1,times_s=[1.],weight=1.)])
