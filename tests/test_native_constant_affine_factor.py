"""Full objective cost/peak and hard conjunction survive exact factoring."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_constant_affine_factor.py').is_file())
sys.path.insert(0,str(root/'scripts'))
from native_constant_affine_factor import factor_affine_constants
from native_sparse_conic_step import conic_hinge_step

def fixture():
    g=np.array([-3.,-.3,.2,-.1,0.]);j=np.array([[0.,0.],[1.,0.],[0.,1.],[0.,0.],[0.,0.]])
    h=sparse.csr_matrix([[0.,0.],[1.,0.],[0.,0.],[0.,-1.]]);u=np.array([.5,.4,.1,.8])
    return g,j,h,u

@pytest.mark.parametrize('fmt',['csr','csc'])
def test_every_original_cost_peak_and_hard_predicate_is_reconstructed(fmt):
    g,j,h,u=fixture();h=h.asformat(fmt);f=factor_affine_constants(g,j,h,u)
    assert f['objective_original_rows'].tolist()==[1,2] and f['constant_objective_rows'].tolist()==[0,3,4]
    assert f['hard_original_rows'].tolist()==[1,3,2] and f['original_hard_to_factor'].tolist()==[2,0,2,1]
    assert f['constant_hinge_offset']==3.1 and f['constant_maximum_violation']==3.
    points=np.vstack([np.random.default_rng(17).uniform(-2,2,size=(50,2)),[[0,0],[.3,-.2],[.3,0]]])
    for p in points:
        full=np.maximum(-(g+j@p),0);reduced=np.maximum(-(f['margins']+f['jacobian']@p),0)
        assert float(full.sum())==pytest.approx(float(reduced.sum())+f['constant_hinge_offset'],abs=2e-15)
        assert full.max()==max(reduced.max(),f['constant_maximum_violation'])
        original=h@p-u;factored=f['hard_matrix']@p-f['hard_upper']
        assert original.max()==factored.max() and np.all(original<=0)==np.all(factored<=0)

def test_failed_final_constant_hard_row_is_retained_as_a_conflict():
    g,j,h,u=fixture();h=sparse.csr_matrix((10000,2));u=np.ones(10000);u[-1]=-.01
    f=factor_affine_constants(g,j,h,u)
    assert f['report']['factor_hard_rows']==1 and f['hard_original_rows'].tolist()==[9999]
    assert not f['report']['constant_hard_conditions_pass'] and f['report']['maximum_constant_hard_residual']==.01
    assert np.all(f['original_hard_to_factor']==0)

def test_tiny_nonzero_final_column_in_both_populations_is_retained():
    g=np.array([-.1,-.2]);j=np.zeros((2,768));j[-1,-1]=1e-300
    h=sparse.csr_matrix(([1e-300],([9999],[767])),shape=(10000,768));f=factor_affine_constants(g,j,h,np.ones(10000))
    assert f['report']['responsive_objectives']==1 and f['jacobian'][0,-1]==1e-300
    assert f['report']['nonconstant_hard_rows']==1 and f['hard_matrix'][0,-1]==1e-300 and f['report']['columns']==768

def test_all_constant_objectives_and_empty_hard_population_are_explicit():
    f=factor_affine_constants(np.array([-3.,.2]),np.zeros((2,4)),sparse.csr_matrix((0,4)),np.empty(0))
    assert f['margins'].shape==(0,) and f['jacobian'].shape==(0,4) and f['hard_matrix'].shape==(0,4)
    assert f['report']['all_objectives_constant'] and f['constant_hinge_offset']==3 and f['original_objective_to_factor'].tolist()==[-1,-1]

def test_no_constant_rows_leave_every_original_row_and_value_present():
    f=factor_affine_constants(np.array([-.2,-.3]),np.eye(2),sparse.eye(2,format='csr'),np.ones(2))
    assert f['objective_original_rows'].tolist()==[0,1] and f['hard_original_rows'].tolist()==[0,1]
    assert f['constant_hinge_offset']==0 and f['report']['constant_hard_representative_original_row'] is None

def test_constant_peak_conflict_cannot_be_hidden_by_responsive_rows():
    g,j,h,u=fixture();f=factor_affine_constants(g,j,h,u,maximum_model_violation=1.)
    assert f['constant_maximum_violation']==3 and not f['report']['constant_peak_conditions_pass']
    f=factor_affine_constants(g,j,h,u,maximum_model_violation=3.)
    assert f['report']['constant_peak_conditions_pass']

def test_explicit_zero_storage_does_not_make_a_nonzero_row():
    h=sparse.csr_matrix(([0.],([0],[1])),shape=(2,2));f=factor_affine_constants(np.array([-.1]),np.zeros((1,2)),h,np.array([.2,.1]))
    assert f['report']['constant_hard_rows']==2 and f['hard_original_rows'].tolist()==[1] and h.nnz==1

def test_inputs_and_all_returned_arrays_are_owned():
    args=list(fixture());snap=[a.copy() for a in args];f=factor_affine_constants(*args)
    for value in f.values():
        if isinstance(value,np.ndarray):value[:]=99
        elif sparse.issparse(value):value.data[:]=99
    for a,b in zip(args,snap):
        if sparse.issparse(a):assert (a!=b).nnz==0
        else:np.testing.assert_array_equal(a,b)

def test_factored_real_solver_point_is_checked_in_the_complete_original_model():
    g,j,h,u=fixture();f=factor_affine_constants(g,j,h,u)
    v=np.zeros((1,3));m=sparse.csr_matrix((3,2));r=np.ones(1)
    point,info=conic_hinge_step(f['margins'],f['jacobian'],np.full(2,-.5),np.full(2,.5),v,m,r,extra_matrix=f['hard_matrix'],extra_upper=f['hard_upper'],maximum_model_violation=3.)
    assert point is not None and info['usable_direction']
    assert np.all(h@point<=u) and np.all(point>=-.5) and np.all(point<=.5)
    assert np.maximum(-(g+j@point),0).sum()<np.maximum(-g,0).sum()

@pytest.mark.parametrize('fault',['nan','bool','margins_shape','jacobian_shape','upper_shape','matrix_shape','matrix_nan','sparse_index','duplicate_storage','budget'])
def test_bad_or_over_budget_complete_models_are_rejected(fault):
    g,j,h,u=fixture();kw={}
    if fault=='nan':g[0]=np.nan
    elif fault=='bool':j=j.astype(bool)
    elif fault=='margins_shape':g=g[:-1]
    elif fault=='jacobian_shape':j=j[:,None,:]
    elif fault=='upper_shape':u=u[:-1]
    elif fault=='matrix_shape':h=h[:,:-1]
    elif fault=='matrix_nan':h.data[0]=np.inf
    elif fault=='sparse_index':h.indices[-1]=99
    elif fault=='duplicate_storage':h=sparse.csr_matrix((np.array([1.,-1.]),np.array([0,0]),np.array([0,2,2,2,2])),shape=(4,2))
    else:kw['maximum_working_bytes']=1
    with pytest.raises(ValueError):factor_affine_constants(g,j,h,u,**kw)
