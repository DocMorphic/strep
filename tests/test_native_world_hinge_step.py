"""Analytic optima, explicit row cuts, full columns and scheduler compatibility."""
from pathlib import Path
import os,sys,subprocess,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_world_hinge_step as module
from native_world_hinge_step import hinge_step


def test_sum_hinge_repairs_both_independent_rows_in_hand_solution():
    direction,report=hinge_step([-1.,-.5],np.eye(2),[-.2,-.2],[.2,.2])
    np.testing.assert_allclose(direction,[.2,.2],atol=1e-9,rtol=0)
    assert abs(report['predicted_maximum_model_violation']-.8)<1e-9 and report['usable_direction']
    assert report['model_rows']==2 and report['complete_columns']==2 and report['linear_constraint_rows']==6
    assert report['original_selected'] and not report['quality_approved'] and not report['release_approved']


def test_both_equal_worst_rows_retained_and_repaired_together():
    direction,report=hinge_step([-1.,-1.],np.eye(2),[-.2,-.2],[.2,.2])
    np.testing.assert_allclose(direction,[.2,.2],atol=1e-9,rtol=0)
    assert abs(report['predicted_maximum_model_violation']-.8)<1e-9


def test_extra_observed_cut_constrains_direction_under_original_box():
    direction,report=hinge_step([-1.],[[1.,1.]],[-.3,-.3],[.3,.3],extra_matrix=[[1.,0.]],extra_upper=[.02])
    np.testing.assert_allclose(direction,[.02,.3],atol=1e-9,rtol=0)
    assert report['extra_proposal_rows']==1 and report['maximum_extra_cut_violation']<=1e-9
    assert abs(report['predicted_maximum_model_violation']-.68)<1e-9


def test_asymmetric_step_boxes_and_fixed_columns_are_never_clipped_or_removed():
    direction,report=hinge_step([-1.],[[-1.,-2.,7.]],[0.,-.1,0.],[.2,0.,0.])
    np.testing.assert_allclose(direction,[0.,-.1,0.],atol=1e-9,rtol=0)
    assert report['complete_columns']==3 and abs(report['predicted_maximum_model_violation']-.8)<1e-9


def test_last_column_remains_available_and_every_input_is_a_snapshot():
    margins=np.array([-.7]);jac=np.zeros((1,37));jac[0,-1]=2;lo=np.full(37,-.25);hi=-lo;before=[a.copy() for a in [margins,jac,lo,hi]]
    direction,report=hinge_step(margins,jac,lo,hi);expected=np.zeros(37);expected[-1]=.25
    np.testing.assert_allclose(direction,expected,atol=1e-9,rtol=0);assert report['complete_columns']==37
    for current,old in zip([margins,jac,lo,hi],before):np.testing.assert_array_equal(current,old)


def test_passing_model_and_zero_gradient_failure_do_not_imply_motion_acceptance_or_infeasibility():
    direction,report=hinge_step([1.,2.],[[1.,1.],[-1.,2.]],[-.2,-.2],[.2,.2])
    assert not np.any(direction) and report['predicted_maximum_model_violation']==0 and not report['quality_approved']
    direction,report=hinge_step([-1.],[[0.,0.]],[-.2,-.2],[.2,.2])
    assert not np.any(direction) and report['predicted_maximum_model_violation']==1
    assert 'not nonlinear motion feasibility/infeasibility' in report['scope']


def test_infeasible_extra_proxy_returns_no_direction_without_general_infeasibility_claim():
    direction,report=hinge_step([1.],[[1.]],[0.],[0.],extra_matrix=[[1.]],extra_upper=[-1.])
    assert direction is None and not report['solver_success'] and not report['usable_direction']
    assert report['original_selected'] and not report['release_approved']


def test_sparse_budget_checked_before_matrix_allocation(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('sparse matrices allocated before complete budget admission')
    monkeypatch.setattr(module.sparse,'hstack',forbidden)
    with pytest.raises(ValueError,match='budget'):hinge_step([-1.],[[1.]],[0.],[.2],maximum_matrix_bytes=8)


@pytest.mark.parametrize('fault',['m_shape','j_shape','empty','columns','rows','nan','bool','complex','lo_shape','hi_shape','lo_positive','hi_negative','box_escape','missing_upper','missing_matrix','cut_shape','cut_cols','cut_nan','upper_shape','penalty_zero','penalty_bool','bytes_bool','bytes_large','time_zero','time_bool','iterations_bool','iterations_zero'])
def test_incomplete_numeric_data_and_budgets_reject_before_solver(fault,monkeypatch):
    args=dict(margins=[-1.],jacobian=[[1.,1.]],lower_delta=[-.2,-.2],upper_delta=[.2,.2])
    if fault=='m_shape':args['margins']=[[-1.]]
    elif fault=='j_shape':args['jacobian']=[1.,1.]
    elif fault=='empty':args['margins']=[];args['jacobian']=np.zeros((0,2))
    elif fault=='columns':args['jacobian']=np.zeros((1,769))
    elif fault=='rows':args['jacobian']=np.zeros((8193,2));args['margins']=np.zeros(8193)
    elif fault=='nan':args['jacobian']=[[1.,np.nan]]
    elif fault=='bool':args['jacobian']=[[True,False]]
    elif fault=='complex':args['jacobian']=[[1+0j,1]]
    elif fault=='lo_shape':args['lower_delta']=[-.2]
    elif fault=='hi_shape':args['upper_delta']=[.2]
    elif fault=='lo_positive':args['lower_delta']=[.1,-.2]
    elif fault=='hi_negative':args['upper_delta']=[-.1,.2]
    elif fault=='box_escape':args['lower_delta']=[-2.01,-.2]
    elif fault=='missing_upper':args['extra_matrix']=[[1.,1.]]
    elif fault=='missing_matrix':args['extra_upper']=[1.]
    elif fault=='cut_shape':args.update(extra_matrix=[1.,1.],extra_upper=[1.])
    elif fault=='cut_cols':args.update(extra_matrix=[[1.]],extra_upper=[1.])
    elif fault=='cut_nan':args.update(extra_matrix=[[np.nan,1.]],extra_upper=[1.])
    elif fault=='upper_shape':args.update(extra_matrix=[[1.,1.]],extra_upper=[1.,2.])
    elif fault=='penalty_zero':args['l1_penalty']=0
    elif fault=='penalty_bool':args['l1_penalty']=True
    elif fault=='bytes_bool':args['maximum_matrix_bytes']=True
    elif fault=='bytes_large':args['maximum_matrix_bytes']=64*1024**2+1
    elif fault=='time_zero':args['time_limit_seconds']=0
    elif fault=='time_bool':args['time_limit_seconds']=True
    elif fault=='iterations_bool':args['maximum_iterations']=True
    else:args['maximum_iterations']=0
    def forbidden(*args,**kwargs):raise AssertionError('solver ran with invalid or incomplete original rows')
    monkeypatch.setattr(module,'linprog',forbidden)
    with pytest.raises(ValueError):hinge_step(**args)


@pytest.mark.parametrize('threads',[1,2])
def test_existing_highs_thread_scheduler_is_preserved_in_fresh_owned_process(threads):
    code="""import sys,warnings
from scipy.optimize import linprog,OptimizeWarning
sys.path.insert(0,sys.argv[1])
with warnings.catch_warnings():
 warnings.simplefilter('ignore',OptimizeWarning)
 warm=linprog([1.],bounds=[(0.,1.)],method='highs',options={'threads':int(sys.argv[2])})
assert warm.success
from native_world_hinge_step import hinge_step
direction,report=hinge_step([-1.],[[1.]],[-.2],[.2])
assert report['usable_direction'] and abs(direction[0]-.2)<1e-9,report
"""
    completed=subprocess.run([sys.executable,'-c',code,str(Path(module.__file__).parent),str(threads)],capture_output=True,text=True,timeout=45,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert completed.returncode==0,completed.stdout+completed.stderr


def test_l1_picks_zero_for_flat_sum_but_explicit_peak_ceiling_requires_movement():
    direction,report=hinge_step([-1.,-.1],[[1.],[-1.]],[-.2],[.2])
    np.testing.assert_allclose(direction,[0.],atol=1e-9,rtol=0)
    assert abs(report['predicted_sum_model_violation']-1.1)<1e-9
    direction,report=hinge_step([-1.,-.1],[[1.],[-1.]],[-.2],[.2],maximum_model_violation=.8)
    np.testing.assert_allclose(direction,[.2],atol=1e-9,rtol=0)
    assert abs(report['predicted_maximum_model_violation']-.8)<1e-9 and report['maximum_model_violation']==.8


def test_unreachable_local_peak_ceiling_does_not_imply_motion_infeasibility():
    direction,report=hinge_step([-1.],[[0.]],[-.2],[.2],maximum_model_violation=.8)
    assert direction is None and not report['usable_direction'] and report['original_selected']


@pytest.mark.parametrize('ceiling',[True,-.1,float('nan'),float('inf'),1000001.,'1',[]])
def test_invalid_local_peak_ceiling_rejected_before_solver(ceiling,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('invalid ceiling reached solver')
    monkeypatch.setattr(module,'linprog',forbidden)
    with pytest.raises(ValueError):hinge_step([-1.],[[1.]],[-.2],[.2],maximum_model_violation=ceiling)


def test_complete_model_plus_peak_storage_admitted_before_sparse_allocation(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('matrix allocated before storage admission')
    monkeypatch.setattr(module.sparse,'hstack',forbidden)
    # Dense one-column Jacobian fits; complete sparse model with peak row does not.
    with pytest.raises(ValueError,match='budget'):hinge_step([-1.],[[1.]],[0.],[.2],maximum_model_violation=.9,maximum_matrix_bytes=90)


def test_unbounded_normalized_margins_reject_before_solver(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('unbounded margin reached solver')
    monkeypatch.setattr(module,'linprog',forbidden)
    with pytest.raises(ValueError):hinge_step([-1e308,-1e308],[[1.],[1.]],[-.2],[.2])
