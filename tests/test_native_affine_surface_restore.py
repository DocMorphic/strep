import sys
from pathlib import Path
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_affine_surface_restore import restore


def fixture():
    return [NormRows([[0.,0,0]],[1.],[1.]),sparse.csr_matrix([[1.],[0.],[0.]]),
            np.array([-2.]),sparse.csr_matrix([[1.]]),[],np.array([0.]),np.array([2.]),np.array([-3.]),np.array([3.])]


def test_restores_violating_target_without_relaxing_native_caps():
    args=fixture();original=[getattr(args[0],n).copy() for n in ('vectors','caps','scales')]
    value,info=restore(*args,depth_limit=.5,depth_bound=0.,scale=1.)
    assert .99999999<value[0]<=1. and info['status']=='RestoredSurfaceDirection'
    assert not info['target']['passed'] and info['selected']['native_excess']<=0.
    assert len(info['probes'])==34 and not info['quality_approved']
    for n,p in zip(('vectors','caps','scales'),original):np.testing.assert_array_equal(getattr(args[0],n),p)


def test_full_three_vector_norm_controls_segment_boundary():
    args=fixture();args[1]=sparse.csr_matrix([[1.,0.],[0.,1.],[0.,0.]])
    args[3]=sparse.csr_matrix([[1.,1.]])
    args[5:]=[np.array([.1,.1]),np.array([1.,1.]),np.array([-2.,-2.]),np.array([2.,2.])]
    value,info=restore(*args,depth_limit=.5,depth_bound=0.,scale=1.)
    assert np.linalg.norm(value)<=1. and np.linalg.norm(value)>1.-1e-8
    assert info['selected']['surface_excess']<info['anchor']['surface_excess']


def test_depth_priority_blocks_otherwise_native_feasible_surface_target():
    args=fixture();args[2]=np.array([-2.,-.1]);args[3]=sparse.csr_matrix([[1.],[-1.]])
    args[4]=[1];args[6]=np.array([.8])
    value,info=restore(*args,depth_limit=.5,depth_bound=0.,scale=1.)
    assert .4-1e-8<value[0]<=.4 and info['selected']['depth_deficit']==0.
    assert info['target']['native_excess']<0. and not info['target']['passed']


def test_already_feasible_better_target_retained_exactly():
    args=fixture();args[6]=np.array([.75]);value,info=restore(*args,depth_limit=.5,depth_bound=0.,scale=1.)
    np.testing.assert_array_equal(value,args[6]);assert info['fraction']==1. and len(info['probes'])==2


def test_late_surface_row_prevents_false_improvement():
    args=fixture();args[2]=np.array([-2.,-3.]);args[3]=sparse.csr_matrix([[1.],[-1.]])
    args[6]=np.array([.5]);value,info=restore(*args,depth_limit=.5,depth_bound=0.,scale=1.)
    np.testing.assert_array_equal(value,args[5]);assert info['status']=='NoSurfaceImprovement'


def test_no_feasible_positive_step_retains_anchor():
    args=fixture();args[5]=np.array([1.]);value,info=restore(*args,depth_limit=.5,depth_bound=0.,scale=1.)
    np.testing.assert_array_equal(value,args[5]);assert info['fraction']==0.


def test_invalid_anchor_not_used_as_restoration_origin():
    args=fixture();args[5]=np.array([1.01])
    with pytest.raises(ValueError,match='feasible'):restore(*args,depth_limit=.5,depth_bound=0.)


@pytest.mark.parametrize('bad',[-1,0,65,True,2.5])
def test_unbounded_or_invalid_iteration_budget_rejected(bad):
    with pytest.raises(ValueError,match='bounded'):restore(*fixture(),depth_limit=.5,depth_bound=0.,iterations=bad)


@pytest.mark.parametrize('kind',['outside','nan','witness','matrix'])
def test_bad_endpoints_or_incomplete_population_rejected(kind):
    args=fixture()
    if kind=='outside':args[6]=np.array([4.])
    elif kind=='nan':args[6]=np.array([np.nan])
    elif kind=='witness':args[4]=[1]
    else:args[1]=sparse.csr_matrix([[np.inf],[0.],[0.]])
    with pytest.raises(ValueError):restore(*args,depth_limit=.5,depth_bound=0.)


def test_every_native_row_checked_including_late_violation():
    args=fixture();args[0]=NormRows([[0.,0,0],[0.,0,0]],[3.,.2],[1.,1.])
    args[1]=sparse.csr_matrix([[1.],[0.],[0.],[1.],[0.],[0.]])
    value,info=restore(*args,depth_limit=.5,depth_bound=0.,scale=1.)
    assert .2-1e-8<value[0]<=.2 and info['complete_native_norm_rows']==2
