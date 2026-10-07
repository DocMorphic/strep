"""Empirical tightening with unchanged ceilings and independent hard gates."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_component_trajectory_step import args, positive_last
from native_empirical_material_margins import build
import native_component_trajectory_step as old
import native_component_trajectory_margin_step as step

MODEL='a'*64


def policy(kw, error=0.):
    size=len(kw['material_gaps_m'])
    kw['material_margins']=build(np.zeros((1,size)), np.full((1,size),error),
        material_model_sha256=MODEL, sample_sha256=['b'*64], required_sample_sha256=['b'*64],
        row_indices=list(range(size)), required_rows=size)
    kw['material_model_sha256']=MODEL


def fake(monkeypatch, status='InsufficientProgress', point=(.025,.1,.1,.1)):
    class Settings:pass
    solver=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
        ZeroConeT=lambda n:n,DefaultSettings=Settings,
        DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=point,iterations=1)))
    monkeypatch.setattr(step,'solver_module',lambda:solver)


def test_zero_margin_keeps_old_conic_objective_ceilings_and_candidate_exact():
    a,k=args();baseline=[];d0,r0=old.direction(*a,**k,solver_sink=baseline.append)
    policy(k);captured=[];d1,r1=step.direction(*a,**k,solver_sink=captured.append)
    for key in ('quadratic','matrix'):np.testing.assert_array_equal(captured[0][key].toarray(),baseline[0][key].toarray())
    for key in ('linear','rhs'):np.testing.assert_array_equal(captured[0][key],baseline[0][key])
    np.testing.assert_array_equal(d1,d0)
    for key in ('solver_status','selected_fraction','original_material_depth_ceiling_m','original_triangle_deficit_ceiling_m'):
        assert r1[key]==r0[key]
    assert r1['original_material_ceilings_unchanged'] and not r1['quality_approved'] and not r1['release_approved']


def test_tightening_changes_only_legacy_rhs_without_recomputing_original_ceilings():
    a,k=args();baseline=[];old.direction(*a,**k,solver_sink=baseline.append)
    k['material_gap_jacobian']=sparse.csr_matrix(np.ones((10,1)))
    policy(k,.0002);captured=[];delta,info=step.direction(*a,**k,solver_sink=captured.append)
    assert delta is not None and delta[0]>=.0002
    assert info['original_material_depth_ceiling_m']==.003 and info['original_triangle_deficit_ceiling_m']==.0041
    np.testing.assert_array_equal(captured[0]['rhs'][6:16],baseline[0]['rhs'][6:16]-.0002/.005)
    np.testing.assert_array_equal(captured[0]['matrix'][6:16,1:].toarray(),np.zeros((10,3)))
    assert info['selected_empirical_material_maximum_excess_m']<=0
    assert info['selected_material_peak_depth_m']<=.003 and info['selected_worst_legacy_triangle_deficit_m']<=.0041
    # Anchor fails the new buffer but remains legitimate under original bounds.
    assert np.any(np.array(info['tightened_material_lower_bounds_m'])>k['material_gaps_m'])


def test_distinct_row_margins_follow_containment_and_triangle_conic_order():
    a,k=args();baseline=[];old.direction(*a,**k,solver_sink=baseline.append)
    error=np.arange(1,11)*1e-5
    k['material_margins']=build(np.zeros((1,10)),error[None,:],material_model_sha256=MODEL,
        sample_sha256=['b'*64],required_sample_sha256=['b'*64],row_indices=list(range(10)),required_rows=10)
    k['material_model_sha256']=MODEL;k['material_gap_jacobian']=sparse.csr_matrix(np.ones((10,1)))
    captured=[];delta,info=step.direction(*a,**k,solver_sink=captured.append)
    assert delta is not None
    ordered=error[np.r_[9,np.arange(9)]]
    np.testing.assert_array_equal(captured[0]['rhs'][6:16],baseline[0]['rhs'][6:16]-ordered/.005)
    np.testing.assert_array_equal(info['empirical_material_margin_policy']['margins_m'],error)


def test_complete_trajectory_still_exceeds_separate_legacy_row_limit():
    a,k=args(tuple(np.linspace(0.,1.,70)));policy(k)
    delta,info=step.direction(*a,**k)
    assert delta is not None and info['complete_component_rows']==4480 and info['material_rows']==10


def test_impossible_buffer_cannot_retreat_to_original_ceiling_or_anchor(monkeypatch):
    a,k=args();policy(k,.0002);fake(monkeypatch)
    delta,info=step.direction(*a,**k)
    assert delta is None and info['status']=='NoStrictImprovingTrajectoryRay'
    assert len(info['records'])==81 and info['solver_status']=='InsufficientProgress'
    assert all(r['empirical_material_maximum_excess_m']>0 for r in info['records'])
    assert all(r['material_peak_depth_m']==.003 and r['worst_legacy_triangle_deficit_m']==.0041 for r in info['records'])


def test_strict_retreat_accepts_only_overlap_of_native_cap_and_material_buffer(monkeypatch):
    a,k=args();policy(k,.0002);k['material_gap_jacobian']=sparse.csr_matrix(np.ones((10,1)))
    a[0].caps[0]=.00035;fake(monkeypatch)
    delta,info=step.direction(*a,**k)
    assert delta is not None and .0002<=delta[0]<=.00035
    assert info['selected_fraction']==.5 and info['solver_status']=='InsufficientProgress'
    assert info['records'][0]['original_native_maximum_excess']>0
    assert info['records'][-1]['original_native_maximum_excess']<=0
    assert info['records'][-1]['empirical_material_maximum_excess_m']<=0


@pytest.mark.parametrize('gate',['native','mesh','positive','equality','box'])
def test_original_hard_gate_conflict_cannot_be_paid_with_margin_or_objective_slack(monkeypatch,gate):
    a,k=args();policy(k,.0002);k['material_gap_jacobian']=sparse.csr_matrix(np.ones((10,1)))
    if gate=='native':a[0].caps[0]=.0001
    elif gate=='mesh':
        k['separation_guards'].gaps_m[0]=.0002;k['separation_guards'].jacobian=sparse.csr_matrix([[-1.]])
    elif gate=='positive':positive_last(a)
    elif gate=='equality':k['parameter_rows']=np.ones((1,1))
    elif gate=='box':a[5][0]=.0001
    fake(monkeypatch);delta,info=step.direction(*a,**k)
    assert delta is None
    assert info['status'] in ('NoStrictImprovingTrajectoryRay','IterateOutsideOriginalBox')


def test_strict_margin_rejects_near_pass_without_tolerance(monkeypatch):
    a,k=args();policy(k,.0002);k['material_gap_jacobian']=sparse.csr_matrix(np.ones((10,1)))
    fake(monkeypatch,point=(.0001999999999/.02,.1,.1,.1))
    delta,info=step.direction(*a,**k)
    assert delta is None and len(info['records'])==81
    assert 0<info['records'][0]['empirical_material_maximum_excess_m']<1e-12
    assert info['strict_empirical_material_tolerance_m']==0.


def test_solver_callback_report_and_matrices_do_not_alias_policy_or_return():
    a,k=args();policy(k);original=k['material_margins'].report['margins_m'].copy()
    def sink(m):m['rhs'].fill(np.nan);m['record']['empirical_material_margin_policy']['margins_m'].clear()
    delta,info=step.direction(*a,**k,solver_sink=sink)
    assert delta is not None and k['material_margins'].report['margins_m']==original
    assert info['empirical_material_margin_policy']['margins_m']==original


@pytest.mark.parametrize('fault',['missing-type','stale-source','incomplete-rows','mutated-error','invalid-model'])
def test_invalid_policy_or_complete_model_stops_before_solver(monkeypatch,fault):
    a,k=args();policy(k)
    if fault=='missing-type':k['material_margins']=k['material_margins'].report
    elif fault=='stale-source':k['material_model_sha256']='c'*64
    elif fault=='incomplete-rows':k['material_margins'].report['row_indices'].pop()
    elif fault=='mutated-error':k['material_margins'].report['margins_m'][0]=1.
    elif fault=='invalid-model':a[2].report['times_s'][1]=2.
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Invalid full model or margin policy'))
    with pytest.raises(ValueError):step.direction(*a,**k)


@pytest.mark.parametrize('status,point,expected',[
    ('PrimalInfeasible',[.1,.1,.1,.1],'NotMotionIterateStatus'),
    ('NumericalError',[.1,.1,.1,.1],'NotMotionIterateStatus'),
    ('Solved',[np.nan,.1,.1,.1],'InvalidReturnedPoint'),
    ('Solved',[0.],'InvalidReturnedPoint'),
    ('InsufficientProgress',[2.,.1,.1,.1],'IterateOutsideOriginalBox')])
def test_solver_statuses_and_invalid_points_preserved(monkeypatch,status,point,expected):
    a,k=args();policy(k);fake(monkeypatch,status,point)
    delta,info=step.direction(*a,**k)
    assert delta is None and info['status']==expected and info['solver_status']==status


@pytest.mark.parametrize('anchor',['native','mesh'])
def test_original_nonpassing_anchor_is_not_excused_by_policy(monkeypatch,anchor):
    a,k=args();policy(k)
    if anchor=='native':a[0].vectors[0,0]=.1
    elif anchor=='mesh':k['separation_guards'].gaps_m[0]=0.
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Original nonpassing anchor'))
    delta,info=step.direction(*a,**k)
    assert delta is None and info['status'] in ('OriginalAnchorNotStrictlyPassing','OriginalSeparationGuardAnchorNotPassing')
