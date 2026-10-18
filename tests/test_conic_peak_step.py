from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
from conic_peak_step import peak_step
from native_scene_conic import solver_module


def model(columns=3):
    return dict(margins=np.array([-.5]),jacobian=np.ones((1,columns)),lower_delta=np.full(columns,-1.),upper_delta=np.ones(columns),norm_vectors=np.zeros((1,3)),norm_matrix=sparse.eye(3,columns,format='csr'),norm_radii=np.ones(1))


@pytest.mark.parametrize('dtype',[np.float32,np.float64,np.int64,np.uint64])
def test_peak_repair_analytic_solution_without_unsigned_sign_wrap(dtype):
    data=model(1);data['jacobian']=data['jacobian'].astype(dtype);delta,report=peak_step(**data);assert delta is not None and abs(delta[0]-.5)<1e-6 and report['predicted_peak_deficit']<1e-7 and report['variables']==3 and report['shared_peak_variables']==1 and report['per_row_deficit_variables']==0


def test_last_row_last_column_and_hard_constraints_are_not_reduced():
    data=model(3);data.update(margins=np.array([1.,1.,-.4]),jacobian=np.diag([0.,0.,1.]),extra_matrix=sparse.csr_matrix([[1.,0.,0.],[0.,1.,0.]]),extra_upper=np.full(2,1e-5));delta,r=peak_step(**data);assert delta is not None and delta[2]>.3999 and np.all(data['extra_matrix']@delta<=data['extra_upper']) and r['model_rows']==3 and r['complete_columns']==3 and r['hard_rows']==2 and r['omitted_rows']==r['omitted_columns']==0


def test_fixed_conflicting_norm_is_retained():
    data=model(1);data.update(norm_vectors=np.array([[2.,0,0]]),norm_matrix=sparse.csr_matrix((3,1)));delta,r=peak_step(**data);assert delta is None and r['solver_status']=='PrimalInfeasible'


@pytest.mark.parametrize('format',['csr','csc'])
def test_duplicate_sparse_coefficients_sum_and_inputs_are_owned(format):
    data=model(1);constructor=sparse.csr_matrix if format=='csr' else sparse.csc_matrix;pointer=[0,2,2,2] if format=='csr' else [0,2];data['norm_matrix']=constructor((np.array([2.,-1.]),np.array([0,0]),np.array(pointer)),shape=(3,1));data['extra_matrix']=sparse.csr_matrix((np.array([2.,-1.]),np.array([0,0]),np.array([0,2])),shape=(1,1));data['extra_upper']=np.array([.7]);assert data['norm_matrix'].nnz==2 and data['extra_matrix'].nnz==2;before={k:v.copy() for k,v in data.items()};delta,r=peak_step(**data);assert delta is not None and delta[0]<=.7
    for name,value in data.items():
        if sparse.issparse(value):assert (value!=before[name]).nnz==0 and np.array_equal(value.indices,before[name].indices)
        else:np.testing.assert_array_equal(value,before[name])


def fake_solver(monkeypatch,point):
    real=solver_module();fit=SimpleNamespace(status='Solved',x=point,iterations=1)
    fake=SimpleNamespace(__version__=real.__version__,DefaultSettings=real.DefaultSettings,NonnegativeConeT=real.NonnegativeConeT,SecondOrderConeT=real.SecondOrderConeT,DefaultSolver=lambda *args:SimpleNamespace(solve=lambda:fit))
    monkeypatch.setattr('conic_peak_step.solver_module',lambda:fake)


@pytest.mark.parametrize('failure',['norm','hard','box','nonfinite'])
def test_solved_status_never_overrides_strict_original_admission(failure,monkeypatch):
    data=model(1);point=[1e-5,1e-5,.5]
    if failure=='norm':data.update(norm_vectors=np.array([[1.,0,0]]),norm_matrix=sparse.csr_matrix([[0.],[1.],[0.]]))
    elif failure=='hard':data.update(extra_matrix=sparse.csr_matrix([[1.]]),extra_upper=np.array([0.]))
    elif failure=='box':data['upper_delta']=np.array([0.])
    else:point=[np.nan,0.,0.]
    fake_solver(monkeypatch,point);delta,r=peak_step(**data);assert delta is None and not r['usable_direction']


def test_auxiliary_peak_recomputed_without_changing_pose(monkeypatch):
    data=model(1);fake_solver(monkeypatch,[.2,.2,-1e-12]);delta,r=peak_step(**data);np.testing.assert_array_equal(delta,[.2]);assert r['predicted_peak_deficit']==pytest.approx(.3) and r['solver_peak']==-1e-12 and not r['optimality_certified']


@pytest.mark.parametrize('case',['shape','missing_margin','nan_last','large_last','bool_j','complex_j','negative_radius','zero_radius','norm_shape','dense_norm','dense_cut','oned_cut','missing_upper','nan_sparse','sum_overflow','box_without_zero','bad_penalty','bad_time','bad_iterations','bad_reserve','bad_norm_reserve','bad_cut_reserve','bad_budget'])
def test_invalid_complete_inputs_reject(case):
    data=model(3);kwargs={}
    if case=='shape':data['jacobian']=np.ones((1,385))
    elif case=='missing_margin':data['margins']=np.zeros(0)
    elif case=='nan_last':data['jacobian'][0,-1]=np.nan
    elif case=='large_last':data['jacobian'][0,-1]=1e7
    elif case=='bool_j':data['jacobian']=data['jacobian'].astype(bool)
    elif case=='complex_j':data['jacobian']=data['jacobian'].astype(complex)
    elif case=='negative_radius':data['norm_radii'][:]=-1
    elif case=='zero_radius':data['norm_radii'][:]=0
    elif case=='norm_shape':data['norm_matrix']=sparse.eye(4,3,format='csr')
    elif case=='dense_norm':data['norm_matrix']=np.eye(3)
    elif case=='dense_cut':kwargs.update(extra_matrix=np.ones((1,3)),extra_upper=np.ones(1))
    elif case=='oned_cut':kwargs.update(extra_matrix=sparse.csr_array([1.,0,0]),extra_upper=np.ones(1))
    elif case=='missing_upper':kwargs['extra_matrix']=sparse.eye(1,3,format='csr')
    elif case=='nan_sparse':data['norm_matrix'].data[0]=np.nan
    elif case=='sum_overflow':data['norm_matrix']=sparse.csr_matrix((np.array([1e6,1e6]),np.array([0,0]),np.array([0,2,2,2])),shape=(3,3))
    elif case=='box_without_zero':data['lower_delta'][0]=.1
    elif case=='bad_penalty':kwargs['l1_penalty']=0
    elif case=='bad_time':kwargs['time_limit_seconds']=61
    elif case=='bad_iterations':kwargs['maximum_iterations']=True
    elif case=='bad_reserve':kwargs['solver_box_reserve']=np.inf
    elif case=='bad_norm_reserve':kwargs['solver_norm_reserve']=-1e-9
    elif case=='bad_cut_reserve':kwargs['solver_cut_reserve']=np.nan
    elif case=='bad_budget':kwargs['maximum_bytes']=64*1024**2+1
    with pytest.raises(ValueError):peak_step(**data,**kwargs)


def test_complete_assembly_refuses_before_triplet_allocation(monkeypatch):
    data=model(3);data.update(extra_matrix=sparse.csr_matrix((0,3)),extra_upper=np.zeros(0));called=[]
    def forbidden(*args,**kwargs):called.append(True);raise AssertionError('Premature output allocation')
    monkeypatch.setattr('conic_peak_step.np.empty',forbidden)
    with pytest.raises(ValueError):peak_step(**data,maximum_bytes=1)
    assert not called


@pytest.mark.parametrize('field',['margins','jacobian','lower_delta','upper_delta','norm_vectors','norm_radii','extra_upper'])
def test_minimum_signed_integer_rejects_before_solver(field,monkeypatch):
    data=model(3);data.update(extra_matrix=sparse.eye(1,3,format='csr'),extra_upper=np.ones(1))
    data[field]=data[field].astype(np.int64);data[field].flat[-1]=np.iinfo(np.int64).min
    def forbidden():raise AssertionError('Out-of-range integer reached solver')
    monkeypatch.setattr('conic_peak_step.solver_module',forbidden)
    with pytest.raises(ValueError):peak_step(**data)


def test_agrees_with_existing_dense_norm_minimax_on_small_problem():
    from conic_pose_minimax import minimax_step
    margins=np.array([-.4,-.2,.1]);jac=np.eye(3);x=np.zeros(3);old,old_report=minimax_step(margins,jac,x,trust=1.);data=model(3);data.update(margins=margins,jacobian=jac,norm_radii=np.array([1-1e-8]));new,new_report=peak_step(**data,solver_box_reserve=1e-8);assert old is not None and new is not None;assert abs(old_report['predicted_maximum_model_violation']-new_report['predicted_peak_deficit'])<1e-7 and np.max(abs(old-new))<1e-6


@pytest.mark.parametrize('reserve',['norm','cut'])
def test_search_interior_keeps_original_admission_limits(reserve):
    data=model(1);data['margins']=np.array([-2.]);kwargs={}
    if reserve=='norm':kwargs['solver_norm_reserve']=1e-7
    else:data.update(extra_matrix=sparse.csr_matrix([[1.]]),extra_upper=np.array([.5]));kwargs['solver_cut_reserve']=1e-7
    delta,r=peak_step(**data,**kwargs);assert delta is not None and np.linalg.norm(data['norm_vectors']+(data['norm_matrix']@delta).reshape(-1,3))<=1 and all(r['strict_admission'].values()) and r['admission_uses_unshrunk_original_bounds']
    if reserve=='norm':assert delta[0]<1-5e-8
    else:assert delta[0]<.5-5e-8
