"""Rejected poses cannot reset source caps or their preceding contact anchor."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from recentered_coupled_contacts import RecenteredCoupledContactModel,reference_rows
from central_coupled_contacts import CentralCoupledContactModel,contact_linearize
from native_contact_norms import ContactNorms
from native_scene_norms import NormRows,rows
from test_native_contact_norms import prepared


def exported(problem,value,folder):
    folder.mkdir()
    files={n:folder/(n+'.glb') for n in problem.edits.actors}
    for n,p in files.items():problem.edits.export(n,value,p)
    native,worlds=problem.decoded(files,value)
    return native,worlds


@pytest.mark.parametrize('partner',[False,True])
@pytest.mark.parametrize('hold',[False,True])
def test_rejected_native_origin_keeps_all_rows_and_previous_uncached_contact_guards(tmp_path,partner,hold):
    problem,p,digest=prepared(tmp_path,partner=partner,hold=hold)
    previous=problem.initial.copy();current=previous.copy();current[0]=.001
    before,anchor=exported(problem,previous,tmp_path/'anchor')
    native,worlds=exported(problem,current,tmp_path/'current')
    assert np.all(before<=0) and np.any(native>0)
    with pytest.raises(ValueError,match='feasible'):
        CentralCoupledContactModel(problem,p,digest).linearize(current,worlds,.02)
    model=RecenteredCoupledContactModel(problem,p,digest)
    source_caps={n:[c.copy() for c in rate.caps] for n,rate in problem.caps.items()}
    system,jac,meta=model.linearize(current,worlds,previous,anchor,.02,step=1e-4)
    reference=ContactNorms(problem,p,digest)
    contact_before=reference.residual(anchor);contact_after=reference.residual(worlds)
    original=rows(problem,current,worlds);n=len(native);c=len(contact_before)
    assert len(system.caps)==n+2*c and jac.shape==(3*(n+2*c),problem.size) and meta['hard_rows']==n+c
    np.testing.assert_allclose(system.residual()[:n],native,atol=1e-9,rtol=0)
    np.testing.assert_array_equal(system.vectors[:n],original.vectors)
    np.testing.assert_array_equal(system.caps[:n],original.caps)
    np.testing.assert_array_equal(system.scales[:n],original.scales)
    np.testing.assert_allclose(system.residual()[n:n+c],contact_after-np.maximum(contact_before,0),atol=1e-10,rtol=0)
    np.testing.assert_allclose(system.residual()[n+c:],contact_after,atol=1e-10,rtol=0)
    assert (jac[3*n:3*(n+c)]!=jac[3*(n+c):]).nnz==0
    for name,caps in source_caps.items():
        for old,new in zip(caps,problem.caps[name].caps):np.testing.assert_array_equal(old,new)
    assert meta['current_native_failed_rows']==int((native>0).sum()) and meta['previous_native_feasible']
    assert not meta['rejected_pose_becomes_new_baseline'] and not meta['full_geometry_in_proposal']
    assert not meta['quality_approved'] and not meta['release_approved']


def test_worsened_failed_contact_row_remains_a_positive_hard_guard(tmp_path):
    problem,p,digest=prepared(tmp_path);previous=problem.initial;current=previous.copy();current[0]=-.001
    _,anchor=exported(problem,previous,tmp_path/'anchor');_,worlds=exported(problem,current,tmp_path/'current')
    reference=ContactNorms(problem,p,digest);before=reference.residual(anchor);after=reference.residual(worlds)
    assert after[0]>before[0]>0
    system,_,meta=RecenteredCoupledContactModel(problem,p,digest).linearize(current,worlds,previous,anchor,.02)
    n=meta['complete_native_rows']
    assert system.residual()[n]>0
    assert system.residual()[n]==pytest.approx(after[0]-before[0],abs=1e-10)


def test_nonzero_preceding_controls_keep_original_source_rate_epoch(tmp_path):
    problem,p,digest=prepared(tmp_path);previous=problem.initial.copy();previous[0]=1e-7
    current=previous.copy();current[0]+=.001
    before,anchor=exported(problem,previous,tmp_path/'anchor');_,worlds=exported(problem,current,tmp_path/'current')
    assert np.all(before<=0)
    model=RecenteredCoupledContactModel(problem,p,digest)
    _,_,meta=model.linearize(current,worlds,previous,anchor,.02)
    assert meta['source_caps_unchanged'] and meta['original_contact_anchor_preserved']


def test_infeasible_previous_native_anchor_is_rejected(tmp_path):
    problem,p,digest=prepared(tmp_path);previous=problem.initial.copy();previous[0]=.001
    _,anchor=exported(problem,previous,tmp_path/'anchor')
    with pytest.raises(ValueError,match='previously feasible'):
        RecenteredCoupledContactModel(problem,p,digest).linearize(previous,anchor,previous,anchor,.02)


@pytest.mark.parametrize('fault',['cap','tolerance','dt','uniform'])
def test_changed_source_rate_baseline_cannot_enter_restoration(tmp_path,fault):
    problem,p,digest=prepared(tmp_path);model=RecenteredCoupledContactModel(problem,p,digest)
    if fault=='cap':problem.caps['A'].caps[0][0,0]+=1e-8
    if fault=='tolerance':problem.caps['A'].tolerance+=1e-8
    if fault=='dt':problem.caps['A'].dt+=1e-8
    if fault=='uniform':problem.uniform[1]+=1e-8
    with pytest.raises(ValueError,match='source-rate'):
        model.linearize(problem.initial,problem.source_world,problem.initial,problem.source_world,.02)


@pytest.mark.parametrize('fault',['missing','extra','shape','nan','previous-box','current-box'])
def test_incomplete_worlds_and_outside_controls_reject(tmp_path,fault):
    problem,p,digest=prepared(tmp_path);model=RecenteredCoupledContactModel(problem,p,digest)
    current=problem.initial.copy();previous=current.copy();worlds=copy.deepcopy(problem.source_world);anchor=problem.source_world
    if fault=='missing':worlds={}
    if fault=='extra':worlds['extra']=worlds['A']
    if fault=='shape':worlds['A']=worlds['A'][:-1]
    if fault=='nan':worlds['A'][0,0,0,0]=np.nan
    if fault=='previous-box':previous[0]=1.01
    if fault=='current-box':current[0]=1.01
    with pytest.raises(ValueError):model.linearize(current,worlds,previous,anchor,.02)


def encoding():
    baseline=NormRows([[0.,.5,0.]],[.25],[.25])
    current=NormRows([[0.,.6,0.],[1.2,0.,0.],[.7,0.,0.]],[.25,1.,1.],[.25,.005,.005])
    return current,np.array([-.2,.3]),baseline,np.array([2.,-.1])


def test_reference_offsets_can_expand_without_changing_any_physical_gap_residual():
    current,gaps,baseline,before=encoding();original=current.residual().copy()
    adjusted,reference,meta=reference_rows(current,gaps,baseline,before)
    assert meta['reference_side_offset_expansions']==1 and meta['maximum_reference_side_offset_increase_m']==2.
    np.testing.assert_allclose(adjusted.residual(),original,atol=1e-10,rtol=0)
    np.testing.assert_allclose(reference.residual(),np.r_[baseline.residual(),-before/.005],atol=1e-10,rtol=0)
    assert reference.vectors[1,0]>=1.
    np.testing.assert_array_equal(reference.caps,adjusted.caps)
    np.testing.assert_array_equal(reference.scales,adjusted.scales)


@pytest.mark.parametrize('fault',['current-type','baseline-type','shape','nan','cap','scale','offset','nonzero-side','gap'])
def test_invalid_or_changed_contact_encoding_rejects(fault):
    current,gaps,baseline,before=encoding()
    if fault=='current-type':current=None
    if fault=='baseline-type':baseline=None
    if fault=='shape':gaps=gaps[:1]
    if fault=='nan':before[0]=np.nan
    if fault=='cap':baseline.caps[0]+=.01
    if fault=='scale':baseline.scales[0]+=.01
    if fault=='offset':current.caps[1]=.9
    if fault=='nonzero-side':current.vectors[1,1]=.1
    if fault=='gap':gaps[0]+=.01
    with pytest.raises((ValueError,AssertionError)):reference_rows(current,gaps,baseline,before)


def test_contact_derivatives_match_complete_current_origin_before_reference_reencoding(tmp_path):
    problem,p,digest=prepared(tmp_path,hold=True);model=RecenteredCoupledContactModel(problem,p,digest)
    previous=problem.initial.copy();current=previous.copy();current[0]=.001
    _,anchor=exported(problem,previous,tmp_path/'anchor');_,worlds=exported(problem,current,tmp_path/'current')
    extra,expected,identity=contact_linearize(model.contact,current,worlds,.02,step=1e-4)
    _,actual,meta=model.linearize(current,worlds,previous,anchor,.02,step=1e-4)
    n=meta['complete_native_rows'];c=len(extra.caps)
    assert (actual[3*n:3*(n+c)]!=expected).nnz==0 and (actual[3*(n+c):]!=expected).nnz==0
    assert meta['contact']['actual_difference_offsets']==identity['actual_difference_offsets']
