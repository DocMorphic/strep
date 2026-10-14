"""Approximate solver status must not override full affine refinement checks."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_scene_conic as conic
from native_scene_norms import NormRows


def solve(monkeypatch,second,*,hard=0,status='AlmostSolved',retry=None,primary=.5,jacobian_scale=1.):
    actual=conic.solver_module();answers=iter([
        SimpleNamespace(status='Solved',iterations=1,x=np.array([primary,0.])),
        SimpleNamespace(status=status,iterations=1,x=np.array([second,0.])),
        SimpleNamespace(status=status,iterations=1,x=np.array([second if retry is None else retry,0.]))])
    module=SimpleNamespace(__version__=actual.__version__,DefaultSettings=actual.DefaultSettings,
        NonnegativeConeT=actual.NonnegativeConeT,SecondOrderConeT=actual.SecondOrderConeT,
        DefaultSolver=lambda *args:SimpleNamespace(solve=lambda:next(answers)))
    monkeypatch.setattr(conic,'solver_module',lambda:module)
    # A soft target at .5; optional hard row limits the point to <=.5.
    vectors=[[-.5,0,0]];caps=[0.]
    if hard:vectors.insert(0,[0.,0,0]);caps.insert(0,.5)
    model=NormRows(vectors,caps,np.ones(len(caps)))
    jac=np.zeros((len(caps),3,1));jac[:,0,0]=jacobian_scale
    return conic.direction(model,jac,np.zeros(1),-np.ones(1),np.ones(1),1.,hard_rows=hard)


@pytest.mark.parametrize('status',['Solved','AlmostSolved'])
def test_secondary_error_above_minimax_bound_keeps_primary(monkeypatch,status):
    delta,info=solve(monkeypatch,.5+5e-9,status=status)
    np.testing.assert_array_equal(delta,[.5])
    assert not info['minimum_norm_selected']
    assert info['minimum_norm_affine_soft_excess']>info['minimum_norm_affine_bound']


def test_secondary_violating_hard_prefix_keeps_primary(monkeypatch):
    delta,info=solve(monkeypatch,.5+5e-10,hard=1)
    np.testing.assert_array_equal(delta,[.5])
    assert not info['minimum_norm_selected'] and not info['minimum_norm_affine_hard_rows_pass']
    assert info['minimum_norm_affine_soft_excess']<=info['minimum_norm_affine_bound']


def test_secondary_that_preserves_both_populations_is_selected(monkeypatch):
    delta,info=solve(monkeypatch,.5-5e-10,hard=1)
    assert delta[0]<.5 and info['minimum_norm_selected']
    assert info['minimum_norm_affine_hard_rows_pass']
    assert len(info['minimum_norm_attempts'])==1


def test_stricter_retry_must_pass_same_full_model_checks(monkeypatch):
    delta,info=solve(monkeypatch,.5+5e-9,hard=1,retry=.5-5e-10)
    assert delta[0]<.5 and info['minimum_norm_selected']
    assert [a['selected'] for a in info['minimum_norm_attempts']]==[False,True]
    assert info['minimum_norm_attempts'][1]['phase']=='retry'


def test_reported_primary_objective_cannot_hide_its_measured_affine_error(monkeypatch):
    delta,info=solve(monkeypatch,.5+2e-9,primary=.5+5e-9)
    assert info['primary_affine_soft_excess']>info['affine_optimum']
    assert info['minimum_norm_selected'] and delta[0]<.5+5e-9
    assert info['minimum_norm_affine_soft_excess']<=info['minimum_norm_affine_bound']


def test_proposal_tie_comparison_records_its_tiny_arithmetic_reserve(monkeypatch):
    delta,info=solve(monkeypatch,.5+1e-9+1e-14)
    assert info['minimum_norm_selected']
    assert info['minimum_norm_affine_bound']<info['minimum_norm_affine_soft_excess']
    assert info['minimum_norm_affine_soft_excess']<=info['minimum_norm_affine_bound']+info['minimum_norm_comparison_reserve']
    assert info['minimum_norm_comparison_reserve']<1e-12


def test_finite_solver_point_with_overflowed_affine_rows_is_rejected(monkeypatch):
    with np.errstate(over='ignore',invalid='ignore'):
        delta,info=solve(monkeypatch,.5,primary=0.,jacobian_scale=1e308)
    np.testing.assert_array_equal(delta,[0.])
    assert not info['minimum_norm_selected']
    assert all(not a['finite_affine_rows'] for a in info['minimum_norm_attempts'])


def test_secondary_outside_original_box_is_not_rescued_by_clipping(monkeypatch):
    delta,info=solve(monkeypatch,1.01)
    np.testing.assert_array_equal(delta,[.5])
    assert not info['minimum_norm_selected'] and not info['minimum_norm_control_box_pass']


@pytest.mark.parametrize('second,status',[(float('nan'),'AlmostSolved'),(.5,'MaxIterations')])
def test_invalid_secondary_keeps_finite_primary(monkeypatch,second,status):
    delta,info=solve(monkeypatch,second,status=status)
    np.testing.assert_array_equal(delta,[.5])
    assert not info['minimum_norm_selected']
