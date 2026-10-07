"""Projection preserves original absolute bounds and verified peak priority."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
import native_material_priority_projection as projection


def args():
    return [NormRows([[0.,0.,0.]],[.015],[1.]),sparse.csr_matrix([[1.,0.],[0.,1.],[0.,0.]]),
        np.array([-.006,-.001,-.01]),sparse.csr_matrix([[1.,0.],[-1.,0.],[0.,1.]]),
        [{'kind':'penetrating-vertex'},{'kind':'penetrating-vertex'},{'kind':'triangle-separation'}],
        np.zeros(2),-np.ones(2),np.ones(2),.02,np.array([.002,0.]),np.array([.0035,.004])]


def test_projection_can_reduce_complete_guidance_without_changing_peak_ceiling():
    a=args();step,info=projection.project(*a)
    assert step is not None and step[1]>.003
    assert info['selected_material_peak_depth_m']<=info['verified_depth_ceiling_m']==.004
    assert info['selected_complete_guide_squared_deficit']<info['baseline_complete_guide_squared_deficit']
    assert np.all(a[0].residual(a[1],step)<=0) and info['depth_priority_acceptance_allowance_m']==0
    assert not info['quality_approved'] and not info['release_approved'] and not info['solver_optimality_verified']


def test_full_absolute_trust_box_is_preserved_when_baseline_is_near_a_boundary():
    a=args();a[0].caps[0]=.05;a[9][1]=-.019;a[10][1]=.019
    step,info=projection.project(*a)
    assert step is not None and step[1]>.005 and abs(step[1]-a[9][1])>.02
    assert np.all(abs(step)<=a[8]) and info['absolute_original_trust_box_retained']


def test_all_original_coupled_norms_and_scales_remain_hard():
    a=args();a[0]=NormRows([[0.,0.,0.],[0.,0.,0.],[.001,0.,0.]],[.015,.004,.001],[1.,.1,1.])
    a[1]=sparse.csr_matrix([[1.,0.],[0.,1.],[0.,0.],[1.,0.],[0.,1.],[0.,0.],[0.,0.],[0.,0.],[0.,0.]])
    step,info=projection.project(*a)
    assert step is not None and np.linalg.norm(step)<=.004 and np.all(a[0].residual(a[1],step)<=0)
    assert info['original_norm_rows']==3 and info['active_original_norm_cones']==2 and info['omitted_exactly_fixed_passing_norms']==1


def test_full_parameter_equations_cannot_be_removed_for_a_secondary_gain():
    step,info=projection.project(*args(),parameter_rows=[[0.,1.]])
    if step is not None:assert abs(step[1])<=1e-9
    assert info['parameter_rows']==1


def test_capture_has_complete_conic_model_and_copies_are_isolated():
    seen=[]
    def sink(data):seen.append(data['matrix'].shape);data['rhs'].fill(np.nan)
    step,info=projection.project(*args(),solver_sink=sink)
    assert step is not None and seen==[(10,2)] and np.isfinite(step).all()


@pytest.mark.parametrize('fault',['base-box','base-native','base-parameter','target-box'])
def test_unverified_baseline_or_invalid_target_never_solves(monkeypatch,fault):
    a=args();kw={}
    if fault=='base-box':a[9][0]=.03
    elif fault=='base-native':a[0].caps[0]=.001
    elif fault=='base-parameter':kw['parameter_rows']=[[1.,0.]]
    else:a[10][0]=.03
    monkeypatch.setattr(projection,'solver_module',lambda:pytest.fail('Unverified baseline or target'))
    step,info=projection.project(*a,**kw);assert step is None


@pytest.mark.parametrize('fault',['native-jac','guide-jac','witnesses','kind','gap-sign','empty-depth','nan','cap','scale','box','trust','clearance','metric','parameters','sink'])
def test_invalid_complete_models_reject_before_solving(monkeypatch,fault):
    a=args();kw={}
    if fault=='native-jac':a[1]=sparse.eye(3)
    elif fault=='guide-jac':a[3]=sparse.eye(3)
    elif fault=='witnesses':a[4].pop()
    elif fault=='kind':a[4][0]['kind']='invented'
    elif fault=='gap-sign':a[2][0]=.1
    elif fault=='empty-depth':a[4]=[{'kind':'triangle-separation'}]*3
    elif fault=='nan':a[10][0]=np.nan
    elif fault=='cap':a[0].caps[0]=-1.
    elif fault=='scale':a[0].scales[0]=0.
    elif fault=='box':a[6]=a[7].copy()
    elif fault=='trust':a[8]=True
    elif fault=='clearance':kw['clearance_m']=True
    elif fault=='metric':kw['scale_m']=np.nan
    elif fault=='parameters':kw['parameter_rows']=[[1.,0.,0.]]
    else:kw['solver_sink']=True
    monkeypatch.setattr(projection,'solver_module',lambda:pytest.fail('Invalid model'))
    with pytest.raises(ValueError):projection.project(*a,**kw)


@pytest.mark.parametrize('status,point,expected',[
    ('PrimalInfeasible',[0.,0.],'NotMotionIterateStatus'),('NumericalError',[0.,0.],'NotMotionIterateStatus'),
    ('Solved',[np.nan,0.],'InvalidReturnedCorrection'),('Solved',[0.],'InvalidReturnedCorrection'),
    ('InsufficientProgress',[3.,0.],'CorrectionOutsideOriginalBox')])
def test_invalid_returns_do_not_relabel_a_solver_as_success(monkeypatch,status,point,expected):
    class Settings:pass
    fake=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
        ZeroConeT=lambda n:n,DefaultSettings=Settings,DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=point,iterations=1)))
    monkeypatch.setattr(projection,'solver_module',lambda:fake)
    step,info=projection.project(*args());assert step is None and info['status']==expected and info['solver_status']==status
