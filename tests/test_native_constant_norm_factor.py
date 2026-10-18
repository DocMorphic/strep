"""Complete original cones survive exact affine constant factorization."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_constant_norm_factor.py').is_file())
sys.path.insert(0,str(root/'scripts'))
from native_constant_norm_factor import factor_constant_norms
from native_sparse_conic_step import conic_hinge_step


def fixture():
    v=np.array([[.1,0,0],[.2,.3,0],[.99,0,0],[.4,.1,.2],[.2,0,0]])
    m=np.zeros((15,4));m[3,0]=.1;m[10,3]=.2
    return v,sparse.csr_matrix(m),np.ones(5)


@pytest.mark.parametrize('fmt',['csr','csc'])
def test_every_original_row_maps_to_exact_conjunction_over_many_directions(fmt):
    v,m,r=fixture();m=m.asformat(fmt);f=factor_constant_norms(v,m,r)
    assert f['report']['original_norms']==5 and f['report']['factor_norms']==3
    assert f['retained_original_rows'].tolist()==[1,3,2] and f['original_to_factor'].tolist()==[2,0,2,1,2]
    assert f['matrix'].shape==(9,4) and np.any(f['matrix'].toarray()[:,-1])
    for point in np.random.default_rng(17).uniform(-10,10,size=(50,4)):
        old=np.linalg.norm(v+(m@point).reshape(-1,3),axis=1)-r
        new=np.linalg.norm(f['vectors']+(f['matrix']@point).reshape(-1,3),axis=1)-f['radii']
        assert np.max(old)==np.max(new) and np.array_equal(old[[1,3,2]],new)
        assert bool(np.all(old<=0))==bool(np.all(new<=0))


def test_failed_last_constant_cannot_be_hidden_by_many_passing_rows():
    v=np.zeros((70000,3));v[-1]=[1.01,0,0];m=sparse.csr_matrix((210000,3));r=np.ones(70000)
    f=factor_constant_norms(v,m,r)
    assert f['report']['factor_norms']==1 and f['report']['constant_representative_original_row']==69999
    assert not f['report']['all_constant_cones_pass'] and f['report']['maximum_original_unit_constant_excess']>0
    assert np.all(f['original_to_factor']==0) and np.linalg.norm(f['vectors'][0])>f['radii'][0]


def test_tiny_nonzero_final_column_is_never_folded_as_constant():
    v=np.zeros((3,3));m=sparse.csr_matrix(([1e-300],([8],[767])),shape=(9,768));r=np.ones(3)
    f=factor_constant_norms(v,m,r)
    assert f['report']['nonconstant_norms']==1 and f['retained_original_rows'][0]==2
    assert f['matrix'][2,767]==1e-300 and f['matrix'].shape[1]==768


def test_exact_duplicate_cancellation_and_explicit_zeros_are_canonicalized():
    m=sparse.csr_matrix((np.array([.2,-.2,0.]),np.array([0,0,1]),np.array([0,3,3,3,3,3,3])),shape=(6,2))
    f=factor_constant_norms(np.zeros((2,3)),m,np.ones(2))
    assert f['report']['constant_norms']==2 and f['matrix'].nnz==0
    assert m.nnz==3 and m.data.tolist()==[.2,-.2,0.]


def test_no_constant_and_all_constant_cases_keep_exact_original_radii():
    v,m,r=fixture();m=sparse.csr_matrix(np.eye(15,4));r=np.linspace(.2,1,5)
    f=factor_constant_norms(v,m,r)
    np.testing.assert_array_equal(f['radii'],r[f['retained_original_rows']])
    allchanging=factor_constant_norms(np.zeros((2,3)),sparse.eye(6,format='csr'),np.ones(2))
    assert allchanging['report']['constant_norms']==0 and allchanging['report']['constant_representative_original_row'] is None
    assert allchanging['original_to_factor'].tolist()==[0,1]


def test_original_inputs_and_outputs_are_unshared():
    v,m,r=fixture();before=(v.copy(),m.data.copy(),m.indices.copy(),m.indptr.copy(),r.copy())
    f=factor_constant_norms(v,m,r);f['vectors'][:]=99;f['radii'][:]=99;f['matrix'].data[:]=99
    for a,b in zip((v,m.data,m.indices,m.indptr,r),before):np.testing.assert_array_equal(a,b)


def test_seventy_thousand_original_cones_connect_to_existing_solver_and_all_recheck():
    v=np.zeros((70000,3));v[0]=[.1,0,0];v[-1]=[.9,0,0];r=np.ones(70000)
    m=sparse.csr_matrix(([.1],([0],[0])),shape=(210000,2))
    with pytest.raises(ValueError):conic_hinge_step(np.array([-.2]),np.array([[1.,0.]]),np.full(2,-.4),np.full(2,.4),v,m,r)
    f=factor_constant_norms(v,m,r)
    direction,report=conic_hinge_step(np.array([-.2]),np.array([[1.,0.]]),np.full(2,-.4),np.full(2,.4),f['vectors'],f['matrix'],f['radii'])
    assert direction is not None and report['usable_direction']
    original_excess=np.linalg.norm(v+(m@direction).reshape(-1,3),axis=1)-r
    assert len(original_excess)==70000 and np.all(original_excess<=1e-8)


@pytest.mark.parametrize('fault',['vector_shape','nan','radius_zero','radius_shape','bool','matrix_shape','matrix_1d','matrix_nan','columns','sparse_index','budget','factor_budget'])
def test_invalid_or_over_budget_whole_population_rejected(fault):
    v,m,r=fixture();kw={}
    if fault=='vector_shape':v=v[:,:2]
    elif fault=='nan':v[0,0]=np.nan
    elif fault=='radius_zero':r[-1]=0
    elif fault=='radius_shape':r=r[:-1]
    elif fault=='bool':v=v.astype(bool)
    elif fault=='matrix_shape':m=m[:-1]
    elif fault=='matrix_1d':m=sparse.csr_array(np.zeros(15))
    elif fault=='matrix_nan':m.data[0]=np.inf
    elif fault=='columns':m=sparse.csr_matrix((15,769))
    elif fault=='sparse_index':m.indices[-1]=999
    elif fault=='budget':kw['maximum_working_bytes']=1
    else:kw['maximum_output_norms']=1
    with pytest.raises(ValueError):factor_constant_norms(v,m,r,**kw)
