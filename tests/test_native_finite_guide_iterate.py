"""Stalled iterates need original strict bounds and remain unapproved."""
import sys
from pathlib import Path
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
import native_finite_guide_iterate as probe


def args():
    return [NormRows([[0., 0., 0.]], [.004], [1.]), sparse.csr_matrix([[1.], [0.], [0.]]),
            np.array([-.015]), sparse.eye(1), np.zeros(1), -np.ones(1), np.ones(1), .02]


@pytest.mark.parametrize('status', probe.ITERATE_STATUSES)
def test_finite_iterate_preserves_status_and_every_original_norm(status):
    a=args(); snapshots=[v.copy() for v in (a[0].vectors, a[0].caps, a[0].scales)]
    delta,info=probe.assess(*a,solver_status=status,solver_point=[.5,.005])
    assert delta is not None and 0 < delta[0] <= .004
    assert info['solver_status']==status and info['status']=='ProvisionalStrictAffineIterate'
    assert info['raw_original_native_failed_rows']==1 and info['selected_original_native_maximum_excess']<=0
    assert info['guide_squared_error_after'] < info['guide_squared_error_before']
    assert info['diagnostic_only'] and info['actual_export_required'] and not info['solver_optimality_verified']
    assert not info['quality_approved'] and not info['release_approved']
    for v,original in zip((a[0].vectors,a[0].caps,a[0].scales),snapshots): np.testing.assert_array_equal(v,original)


@pytest.mark.parametrize('status',['PrimalInfeasible','DualInfeasible','AlmostPrimalInfeasible','AlmostDualInfeasible','NumericalError','Unsolved','unknown'])
def test_certificates_and_other_statuses_never_use_the_returned_point(monkeypatch,status):
    monkeypatch.setattr(probe,'project',lambda *a:pytest.fail('No motion candidate'))
    delta,info=probe.assess(*args(),solver_status=status,solver_point=[.1,.1])
    assert delta is None and info['status']=='NotMotionIterateStatus' and info['raw_control_step'] is None


@pytest.mark.parametrize('point',[None,[],[0.],[[0.,0.]],[np.nan,0.],[0.,np.inf],['bad',0.]])
def test_missing_nonfinite_or_incomplete_returned_points_are_recorded(monkeypatch,point):
    monkeypatch.setattr(probe,'project',lambda *a:pytest.fail('Invalid iterate'))
    delta,info=probe.assess(*args(),solver_status='InsufficientProgress',solver_point=point)
    assert delta is None and info['status']=='InvalidReturnedPoint'


@pytest.mark.parametrize('point,status',[
    ([2.,.1],'IterateOutsideOriginalProposalBox'),
    ([.1,-.001],'UnverifiedReturnedGuideSlacks'),
    ([.1,.001],'UnverifiedReturnedGuideSlacks'),
])
def test_original_box_and_all_returned_slack_inequalities_gate_the_ray(monkeypatch,point,status):
    monkeypatch.setattr(probe,'project',lambda *a:pytest.fail('Invalid proposal'))
    delta,info=probe.assess(*args(),solver_status='MaxIterations',solver_point=point)
    assert delta is None and info['status']==status and info['raw_control_step'] is not None


def test_every_coupled_norm_row_and_unchanged_scale_are_checked():
    a=args(); a[0]=NormRows([[0.,0.,0.],[0.,0.,0.],[.001,0.,0.]],[.01,.0002,.001],[1.,.1,1.])
    a[1]=sparse.csr_matrix([[1.],[0.],[0.],[2.],[3.],[0.],[0.],[0.],[0.]])
    delta,info=probe.assess(*a,solver_status='InsufficientProgress',solver_point=[.5,.005])
    assert delta is not None and np.sqrt(13)*delta[0]<=.0002
    residual=(np.sqrt(((a[0].vectors+(a[1]@delta).reshape(3,3))**2).sum(axis=1))-a[0].caps)/a[0].scales
    assert np.all(residual<=0) and max(residual)==info['selected_original_native_maximum_excess']
    assert info['original_norm_rows']==3 and info['all_original_rows_columns_caps_scales_retained']


def test_parameter_rows_cannot_be_discarded_to_recover_a_stalled_iterate():
    delta,info=probe.assess(*args(),solver_status='InsufficientProgress',solver_point=[.1,.02],parameter_rows=[[1.]])
    assert delta is None and info['status']=='UnverifiedParameterRows'
    assert info['parameter_row_maximum_absolute_residual']>1e-9


def test_all_guide_rows_and_parameter_columns_remain_present():
    a=args(); a[0]=NormRows([[0.,0.,0.]],[.02],[1.]); a[1]=sparse.csr_matrix([[1.,0.],[0.,1.],[0.,0.]])
    a[2]=np.array([-.015,.1]); a[3]=sparse.csr_matrix([[1.,0.],[-1.,0.]])
    a[4]=np.zeros(2); a[5]=-np.ones(2); a[6]=np.ones(2)
    delta,info=probe.assess(*a,solver_status='MaxTime',solver_point=[.1,-.1,.02,0.],parameter_rows=[[1.,1.]])
    assert delta is not None and abs(delta.sum())<=1e-9 and info['guide_scalar_rows']==2
    assert len(info['raw_guide_slacks'])==2 and info['parameter_rows']==1


def test_nonpassing_original_anchor_never_attempts_a_ray(monkeypatch):
    a=args(); a[0].vectors[0,0]=.005
    monkeypatch.setattr(probe,'project',lambda *a:pytest.fail('Invalid anchor'))
    delta,info=probe.assess(*a,solver_status='Solved',solver_point=[0.,.015])
    assert delta is None and info['status']=='OriginalAnchorNotStrictlyPassing'


@pytest.mark.parametrize('kind',['zero-cap','zero-step','wrong-direction','satisfied-guidance'])
def test_a_stationary_or_nonimproving_iterate_cannot_be_promoted(kind):
    a=args(); point=[.1,.1]
    if kind=='zero-cap': a[0].caps[0]=0.
    elif kind=='zero-step': point=[0.,.1]
    elif kind=='wrong-direction': point=[-.1,.1]
    else: a[2][0]=.1
    delta,info=probe.assess(*a,solver_status='InsufficientProgress',solver_point=point)
    assert delta is None and info['status'] in ('NoStrictPositiveIterateRay','NoStrictGuideImprovement')


@pytest.mark.parametrize('fault',['norm-shape','native-jac','guide-jac','guide-population','native-nan','cap','scale','bounds','anchor-box','trust-bool','trust-nan','status-type','parameters'])
def test_invalid_or_incomplete_original_models_reject(fault):
    a=args();kw={}
    if fault=='norm-shape': a[0].vectors=np.zeros((1,2))
    elif fault=='native-jac': a[1]=sparse.eye(3)
    elif fault=='guide-jac': a[3]=sparse.eye(2)
    elif fault=='guide-population': a[2]=np.zeros(4097);a[3]=sparse.csr_matrix((4097,1))
    elif fault=='native-nan': a[0].vectors[0,0]=np.nan
    elif fault=='cap': a[0].caps[0]=-1.
    elif fault=='scale': a[0].scales[0]=0.
    elif fault=='bounds': a[5]=a[6].copy()
    elif fault=='anchor-box': a[4][0]=2.
    elif fault=='trust-bool': a[7]=True
    elif fault=='trust-nan': a[7]=np.nan
    elif fault=='status-type': kw['solver_status']=True
    else: kw['parameter_rows']=[[1.,0.]]
    kw.setdefault('solver_status','InsufficientProgress')
    with pytest.raises(ValueError): probe.assess(*a,solver_point=[.1,.1],**kw)
