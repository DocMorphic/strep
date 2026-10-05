"""Strict complete affine checks are not decoded-motion approval."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import checked_native_proposal as checked
from native_scene_norms import NormRows


def model():
    return NormRows([[0.,0,0],[1.,0,0]],[.3,.2],[1.,1.]), sparse.csc_matrix([[2.],[0],[0],[1.],[0],[0]])


def test_projection_rechecks_every_row_then_backs_off_to_feasibility():
    system,jac=model()
    delta,record=checked.select(system,jac,[0],[-1],[1],.2,[-.3],hard_rows=1)
    np.testing.assert_array_equal(delta,[-.1])
    assert record['selected_backoff']==1 and len(record['trials'])==2
    assert record['trials'][0]['protected_failed_rows']==1
    assert all(t['complete_rows_recomputed']==2 for t in record['trials'])
    assert record['trials'][1]['protected_rows_pass'] and not record['release_approved']
    np.testing.assert_array_equal(system.caps,[.3,.2])


def test_one_ulp_protected_failure_is_rejected_without_slack():
    system=NormRows([[1.,0,0],[1.,0,0]],[1.,0.],[1.,1.])
    jac=sparse.csc_matrix([[1.],[0],[0],[-1.],[0],[0]])
    delta,record=checked.select(system,jac,[0],[-1],[1],1.,[np.spacing(1.)],hard_rows=1,backoffs=1)
    assert delta is None and record['trials'][0]['protected_failed_rows']==1
    assert record['trials'][0]['protected_maximum_excess']==np.spacing(1.)
    assert not record['protected_slack_added']


def test_valid_origin_is_required_even_if_raw_direction_would_repair_it():
    system=NormRows([[1.,0,0],[2.,0,0]],[.9,0.],[1.,1.])
    jac=sparse.csc_matrix([[1.],[0],[0],[1.],[0],[0]])
    delta,record=checked.select(system,jac,[0],[-1],[1],.2,[-.2],hard_rows=1)
    assert delta is None and record['selection_status']=='InfeasibleAffineAnchor' and record['trials']==[]


def test_an_ignored_late_hard_row_cannot_be_hidden():
    system=NormRows([[0.,0,0],[0.,0,0],[1.,0,0]],[1.,0.,0.],[1.,1.,1.])
    jac=sparse.csc_matrix([[0.],[0],[0],[1.],[0],[0],[-1.],[0],[0]])
    delta,record=checked.select(system,jac,[0],[-1],[1],.2,[.2],hard_rows=2)
    assert delta is None and all(t['protected_failed_rows']==1 for t in record['trials'])


def test_no_soft_improvement_or_zero_direction_is_not_progress():
    system,jac=model()
    for raw in ([0.],[.1]):
        delta,record=checked.select(system,jac,[0],[-1],[1],.2,raw,hard_rows=1)
        assert delta is None and record['selection_status']=='NoFeasibleImprovingStep'


def test_control_addition_rounding_never_escapes_exact_trust_box():
    value=np.array([.999]);raw=np.array([-.005000000000001])
    system=NormRows([[value[0],0,0]],[0.],[1.]);jac=sparse.csc_matrix([[1.],[0],[0]])
    delta,record=checked.select(system,jac,value,[-1],[1],.005,raw)
    assert np.all(abs(delta)<=.005) and np.all(abs(np.asarray(record['selected_controls'])-value)<=.005)


def test_both_dense_and_sparse_complete_models_agree():
    system,jac=model()
    sparse_step,sparse_record=checked.select(system,jac,[0],[-1],[1],.2,[-.3],hard_rows=1)
    dense=jac.toarray().reshape(2,3,1)
    step,record=checked.select(system,dense,[0],[-1],[1],.2,[-.3],hard_rows=1)
    np.testing.assert_array_equal(step,sparse_step);assert record==sparse_record


def test_solver_status_cannot_bypass_failed_affine_guard(monkeypatch):
    system=NormRows([[0.,0,0],[1.,0,0]],[0.,0.],[1.,1.]);jac=sparse.csc_matrix([[1.],[0],[0],[-1.],[0],[0]])
    monkeypatch.setattr(checked,'legacy_direction',lambda *a,**k:(np.array([.1]),dict(status='Solved')))
    delta,record=checked.direction(system,jac,[0],[-1],[1],.1,hard_rows=1)
    assert delta is None and record['status']=='Solved' and not record['returned_direction_available']


def test_real_small_conic_candidate_is_checked_before_return():
    system,jac=model()
    delta,record=checked.direction(system,jac,[0],[-1],[1],.2,hard_rows=1)
    assert delta is not None and np.all(system.residual(jac,delta)[:1]<=0)
    assert record['checked_affine_proposal']['selection_status']=='Selected'


def test_no_solver_direction_preserves_terminal_status(monkeypatch):
    system,jac=model()
    monkeypatch.setattr(checked,'legacy_direction',lambda *a,**k:(None,dict(status='MaxTime')))
    delta,record=checked.direction(system,jac,[0],[-1],[1],.2,hard_rows=1)
    assert delta is None and record['status']=='MaxTime' and record['checked_affine_proposal'] is None


@pytest.mark.parametrize('field,bad',[('hard_rows',-1),('hard_rows',3),('hard_rows',True),
    ('backoffs',0),('backoffs',17),('backoffs',1.),('trust',0),('trust',True),('trust',np.nan),
    ('raw_delta',[np.nan]),('raw_delta',[0,0])])
def test_invalid_selection_inputs_rejected(field,bad):
    system,jac=model();kw=dict(hard_rows=1,backoffs=10);args=dict(trust=.2,raw_delta=[-.1])
    if field in kw:kw[field]=bad
    else:args[field]=bad
    with pytest.raises(ValueError):checked.select(system,jac,[0],[-1],[1],**args,**kw)


def test_nonfinite_affine_arithmetic_cannot_be_approved():
    system=NormRows([[1e200,0,0]],[0.],[1.]);jac=sparse.csc_matrix((3,1))
    with np.errstate(over='ignore', invalid='ignore'):
        with pytest.raises(ValueError,match='finite affine anchor'):checked.select(system,jac,[0],[-1],[1],.1,[0.])
