from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_affine_sum_segment import restore
from native_scene_norms import NormRows


def problem():return NormRows([[0,.8,0],[2,0,0]],[1,0],[1,1]),sparse.csr_matrix([[1],[0],[0],[-1],[0],[0]])


def test_three_dimensional_hard_norm_limits_a_lower_aggregate_proposal():
    rows,jac=problem();caps=rows.caps.copy();point,info=restore(rows,jac,[0],[1],[-1],[1],hard_rows=1)
    assert .59999<point[0]<.600001 and np.all(rows.residual(jac,point)[:1]<=1e-8)
    assert info['status']=='RestoredAggregateDirection' and info['target']['failed_hard_rows']==1
    assert info['selected']['positive_soft_sum']<info['anchor']['positive_soft_sum']
    assert len(info['probes'])==34 and info['hard_postcheck_tolerance']==1e-8
    np.testing.assert_array_equal(rows.caps,caps)


def test_every_hard_row_is_retained():
    rows=NormRows([[0,0,0],[0,0,0],[2,0,0]],[1,.25,0],[1,1,1]);jac=sparse.csr_matrix([[1],[0],[0],[1],[0],[0],[-1],[0],[0]])
    point,info=restore(rows,jac,[0],[1],[-1],[1],hard_rows=2)
    assert .24999<point[0]<.250001 and info['hard_rows']==2 and np.all(rows.residual(jac,point)[:2]<=1e-8)


def test_feasible_lower_loss_target_is_returned_whole():
    rows,jac=problem();point,info=restore(rows,jac,[0],[.5],[-1],[1],hard_rows=1)
    np.testing.assert_array_equal(point,[.5]);assert info['fraction']==1 and len(info['probes'])==2


def test_feasible_worse_target_does_not_claim_improvement():
    rows=NormRows([[0,0,0],[0,0,0]],[1,0],[1,1]);jac=sparse.csr_matrix([[1],[0],[0],[1],[0],[0]])
    point,info=restore(rows,jac,[0],[.5],[-1],[1],hard_rows=1)
    np.testing.assert_array_equal(point,[0]);assert info['status']=='NoAggregateImprovement' and info['fraction']==0 and info['positive_soft_sum_gain']==0


def test_failed_anchor_is_not_silently_rebased():
    rows,jac=problem()
    with pytest.raises(ValueError,match='Anchor'):restore(rows,jac,[.7],[.8],[-1],[1],hard_rows=1)


@pytest.mark.parametrize('fault',['shape','nonfinite','outside','budget','hard','iterations'])
def test_invalid_or_incomplete_problem_rejects(fault):
    rows,jac=problem();anchor=[0];target=[1];kwargs=dict(hard_rows=1)
    if fault=='shape':jac=jac[:3]
    elif fault=='nonfinite':target=[np.nan]
    elif fault=='outside':target=[2]
    elif fault=='budget':kwargs['maximum_nonzeros']=1
    elif fault=='hard':kwargs['hard_rows']=True
    else:kwargs['iterations']=0
    with pytest.raises(ValueError):restore(rows,jac,anchor,target,[-1],[1],**kwargs)
