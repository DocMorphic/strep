from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_scene_conic_sum import direction


def solve(vectors,caps,jac,*,hard=0,scales=None,trust=1.,value=None):
    n=np.asarray(jac).shape[-1];value=np.zeros(n) if value is None else value
    rows=NormRows(vectors,caps,np.ones(len(caps)) if scales is None else scales)
    delta,info=direction(rows,sparse.csc_matrix(np.asarray(jac).reshape(-1,n)),value,-np.ones(n),np.ones(n),trust,hard_rows=hard)
    return rows,delta,info


def test_aggregate_can_improve_many_rows_while_worst_row_is_invariant():
    rows,delta,info=solve([[10,0,0],[2,0,0],[2,0,0]],[0,0,0],[[[0],[0],[0]],[[-1],[0],[0]],[[-1],[0],[0]]])
    assert delta[0]>.999999 and info['fixed_soft_positive_sum']==10
    assert info['scalar_soft_rows']==2 and info['vector_soft_rows']==0
    assert np.maximum(rows.residual(),0).sum()>info['affine_positive_soft_sum']+1.99


def test_hard_vector_norm_preserves_perpendicular_components():
    rows,delta,info=solve([[0,.8,0],[2,0,0]],[1,0],[[[1],[0],[0]],[[-1],[0],[0]]],hard=1)
    assert .59999<delta[0]<.60001 and rows.residual(sparse.csr_matrix([[1],[0],[0],[-1],[0],[0]]),delta)[0]<1e-8
    assert info['affine_hard_rows_pass']


def test_scalar_negative_side_uses_absolute_norm_and_positive_hinge():
    _,delta,info=solve([[-2,0,0]],[0],[[[1],[0],[0]]])
    assert delta[0]>.99999 and .99999<info['affine_positive_soft_sum']<1.00001


def test_vector_soft_rows_retain_full_soc():
    _,delta,info=solve([[0,2,0]],[0],[[[0],[-1],[0]]])
    assert delta[0]>.99999 and info['vector_soft_rows']==1 and info['scalar_soft_rows']==0


def test_fixed_protected_conflict_never_returns_direction():
    _,delta,info=solve([[2,0,0],[2,0,0]],[1,0],[[[0],[0],[0]],[[-1],[0],[0]]],hard=1)
    assert delta is None and info['status']=='FixedProtectedConflict'


def test_box_clipped_controls_and_row_units_are_preserved():
    _,delta,info=solve([[2,0,0]],[0],[[[-2],[0],[0]]],scales=[.01],trust=.5,value=np.array([.9]))
    assert .09999<delta[0]<=.10000000001 and info['maximum_control_step']<=.10000000001


def test_no_active_soft_rows_uses_minimum_norm_feasible_step():
    _,delta,info=solve([[0,0,0]],[1],[[[1],[0],[0]]],hard=1)
    assert abs(delta[0])<1e-8 and info['responsive_soft_rows']==0


@pytest.mark.parametrize('fault',['shape','nan','budget','hard','trust'])
def test_invalid_or_overbudget_population_rejects(fault):
    rows=NormRows([[2,0,0],[2,0,0]],[0,0],[1,1]);jac=sparse.csc_matrix([[-1],[0],[0],[-1],[0],[0]],dtype=float)
    kwargs=dict(hard_rows=0,maximum_soft_rows=100000);trust=1.
    if fault=='shape':jac=jac[:3]
    elif fault=='nan':jac.data[0]=np.nan
    elif fault=='budget':kwargs['maximum_soft_rows']=1
    elif fault=='hard':kwargs['hard_rows']=True
    else:trust=True
    with pytest.raises(ValueError):direction(rows,jac,np.zeros(1),-np.ones(1),np.ones(1),trust,**kwargs)
