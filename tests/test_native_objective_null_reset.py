"""Objective-null coordinates never bypass complete bounds or motion gates."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_objective_null_reset.py').is_file())
sys.path.insert(0,str(root/'scripts'))
from native_objective_null_reset import reset_objective_null_block

def fixture():
    return [np.array([-.4,.2]),np.array([[1.,0.,0.],[0.,1.,0.]]),np.full(3,-1.),np.ones(3),np.array([[.1,0,0],[.2,0,0]]),
        sparse.csr_matrix(np.eye(6,3)*.05),np.ones(2),np.array([.1,.1,.6]),[2]]


def test_valid_origin_proposal_preserves_full_primary_and_lowers_secondary_objective():
    a=fixture();r=reset_objective_null_block(*a);p=r['proposal'];assert r['report']['accepted'] and p.tolist()==[.1,.1,0.]
    np.testing.assert_array_equal(a[0]+a[1]@a[7],a[0]+a[1]@p)
    assert r['report']['columns']==3 and r['report']['original_norms']==2 and r['report']['l1_reduction']>0
    assert not r['report']['nonlinear_invariance_claimed'] and not r['report']['coordinate_clipping']


def test_constraint_dependent_null_variable_is_not_reset_when_its_value_is_needed():
    a=fixture();a[4]=np.array([[.6,0,0]]);a[5]=sparse.csr_matrix(([-1.],([0],[2])),shape=(3,3));a[6]=np.array([.1])
    r=reset_objective_null_block(*a);assert r['proposal'] is None and not r['report']['accepted']
    assert r['report']['after']['maximum_norm_excess']>0


def test_all_hard_rows_including_last_column_are_checked():
    a=fixture();h=sparse.csr_matrix(([-1.],([8999],[2])),shape=(9000,3));upper=np.zeros(9000);upper[-1]=-.5
    r=reset_objective_null_block(*a,extra_matrix=h,extra_upper=upper)
    assert r['proposal'] is None and r['report']['original_hard_rows']==9000 and r['report']['after']['maximum_hard_residual']==.5


def test_origin_outside_original_box_is_rejected_without_clipping():
    a=fixture();a[2][2]=.2;r=reset_objective_null_block(*a)
    assert r['proposal'] is None and r['report']['after']['maximum_box_excess']==.2


def test_valid_original_boundary_origin_is_allowed():
    a=fixture();a[3][2]=0.;a[7][2]=-.2;r=reset_objective_null_block(*a)
    assert r['report']['accepted'] and r['proposal'][2]==0 and r['report']['after']['maximum_box_excess']==0


def test_no_op_never_claims_a_new_proposal():
    a=fixture();a[7][2]=0;r=reset_objective_null_block(*a);assert r['proposal'] is None and r['report']['l1_reduction']==0


def test_tiny_nonzero_primary_column_is_rejected_without_a_cutoff():
    a=fixture();a[1][0,2]=1e-300
    with pytest.raises(ValueError,match='exactly zero'):reset_objective_null_block(*a)


def test_invalid_initial_point_cannot_be_rescued_by_an_origin_replacement():
    a=fixture();a[7][2]=1.1
    with pytest.raises(ValueError,match='Initial proposal'):reset_objective_null_block(*a)


@pytest.mark.parametrize('fmt',['csr','csc'])
def test_inputs_and_output_are_unshared_and_sparse_layouts_supported(fmt):
    a=fixture();a[5]=a[5].asformat(fmt);snap=[x.copy() if hasattr(x,'copy') else x[:] for x in a]
    r=reset_objective_null_block(*a);r['proposal'][:]=99;r['report']['reset_columns'].clear()
    for x,y in zip(a,snap):
        if sparse.issparse(x):assert (x!=y).nnz==0
        else:np.testing.assert_array_equal(x,y)


def test_large_original_population_is_retained_without_a_solver_cone_limit_change():
    a=fixture();a[4]=np.zeros((68900,3));a[5]=sparse.csr_matrix((206700,3));a[6]=np.ones(68900)
    r=reset_objective_null_block(*a);assert r['report']['original_norms']==68900 and r['report']['accepted']


@pytest.mark.parametrize('fault',['nan','bool','shape','norm_shape','negative_radius','matrix_nan','sparse_index','columns_duplicate','columns_unknown','columns_bool','hard_pair','hard_shape','budget'])
def test_bad_or_incomplete_model_is_rejected_whole(fault):
    a=fixture();kw={}
    if fault=='nan':a[7][0]=np.nan
    elif fault=='bool':a[0]=np.ones(2,dtype=bool)
    elif fault=='shape':a[0]=np.ones(1)
    elif fault=='norm_shape':a[4]=np.zeros((2,2))
    elif fault=='negative_radius':a[6][0]=0
    elif fault=='matrix_nan':a[5].data[0]=np.inf
    elif fault=='sparse_index':a[5].indices[-1]=99
    elif fault=='columns_duplicate':a[-1]=[2,2]
    elif fault=='columns_unknown':a[-1]=[3]
    elif fault=='columns_bool':a[-1]=[True]
    elif fault=='hard_pair':kw['extra_matrix']=sparse.csr_matrix((1,3))
    elif fault=='hard_shape':kw.update(extra_matrix=sparse.csr_matrix((1,2)),extra_upper=np.ones(1))
    else:kw['maximum_working_bytes']=1
    with pytest.raises(ValueError):reset_objective_null_block(*a,**kw)
