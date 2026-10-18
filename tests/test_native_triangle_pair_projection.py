"""All-pair rows, coplanar axis discovery and complete coupled derivatives."""
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from native_triangle_pair_projection import choose_directions,projection_rows
from triangle_crossing import classify


def fixture():
    a=np.array([[[0.,0,0],[0.,1,0],[0.,0,1]]]);b=a+[1.,0,0];return a,b,np.array([[1.,0,0]])


def test_all_nine_rows_equal_explicit_vertex_combinations_and_preserve_duplicates():
    a,b,n=fixture();a=np.repeat(a,2,axis=0);b=np.repeat(b,2,axis=0);n=np.repeat(n,2,axis=0);b[0,2,0]=.4
    result=projection_rows(a,b,n,minimum_gap_m=.001,length_scale_m=.02)
    expected=[(n[p]@(b[p,j]-a[p,i])-.001)/.02 for p in range(2) for i in range(3) for j in range(3)]
    np.testing.assert_array_equal(result['margins'],expected);assert result['jacobian'] is None and result['report']['rows']==18
    assert result['report']['all_vertex_combinations_retained'] and not result['report']['collision_certified']


def test_complete_body_and_prop_derivatives_match_independent_perturbations():
    a,b,n=fixture();rng=np.random.default_rng(17);ja=rng.normal(size=a.shape+(13,));jb=rng.normal(size=b.shape+(13,));base=projection_rows(a,b,n,left_jacobian=ja,right_jacobian=jb)
    for column in range(13):
        h=1e-6;plus=projection_rows(a+h*ja[...,column],b+h*jb[...,column],n);minus=projection_rows(a-h*ja[...,column],b-h*jb[...,column],n)
        np.testing.assert_allclose((plus['margins']-minus['margins'])/(2*h),base['jacobian'][:,column],atol=2e-8,rtol=1e-8)
    assert base['jacobian'].shape==(9,13)


@pytest.mark.parametrize('offset',[[0.,0.,1.],[2.,2.,0.],[-2.,-2.,0.]])
def test_parallel_and_coplanar_separated_triangles_have_valid_proposal_axes(offset):
    a=np.array([[[0.,0,0],[1.,0,0],[0.,1,0]]]);b=a+offset;n,info=choose_directions(a,b);result=projection_rows(a,b,n)
    assert info['projected_gap_m'][0]>0 and np.all(result['margins']>0) and classify(a[0],b[0],1e-8)['kind']=='disjoint'
    np.testing.assert_allclose(result['projected_gap_m'],info['projected_gap_m'],atol=1e-15)


def test_crossing_and_touching_do_not_gain_a_clearance_claim():
    a=np.array([[[0.,0,0],[1.,0,0],[0.,1,0]]]);b=np.array([[[.2,.2,-1],[.2,.2,1],[.8,.2,0]]]);n,info=choose_directions(a,b)
    assert info['projected_gap_m'][0]<=1e-14 and classify(a[0],b[0],1e-8)['kind']=='proper_crossing'
    assert not projection_rows(a,b,n)['report']['quality_approved']
    n,info=choose_directions(a,a);assert info['projected_gap_m'][0]==0 and not info['collision_certified']


def test_projection_rows_are_translation_rotation_and_side_reversal_consistent():
    a,b,n=fixture();q=np.array([[0.,-1,0],[1.,0,0],[0,0,1.]])
    base=projection_rows(a,b,n);shifted=projection_rows(a@q.T+[10000.,-20000.,3.],b@q.T+[10000.,-20000.,3.],n@q.T);reverse=projection_rows(b,a,-n)
    np.testing.assert_allclose(base['margins'],shifted['margins'],atol=1e-10,rtol=0);np.testing.assert_allclose(base['margins'].reshape(1,3,3).transpose(0,2,1),reverse['margins'].reshape(1,3,3),atol=1e-14)


def test_last_column_and_shared_motion_are_retained_without_spurious_gap_change():
    a,b,n=fixture();j=np.zeros(a.shape+(768,));j[...,767]=[.1,.2,.3];result=projection_rows(a,b,n,left_jacobian=j,right_jacobian=j)
    assert result['jacobian'].shape==(9,768) and not np.any(result['jacobian'])


@pytest.mark.parametrize('fault',['empty','shape','nan','bool','large','normal','one-jac','jac-shape','jac-columns','jac-nan','jac-bool','budget','working','gap','scale'])
def test_invalid_or_partial_inputs_reject(fault):
    a,b,n=fixture();kwargs={}
    if fault=='empty':a=a[:0];b=b[:0];n=n[:0]
    elif fault=='shape':b=b[:,:2]
    elif fault=='nan':a[0,0,0]=np.nan
    elif fault=='bool':a=a.astype(bool)
    elif fault=='large':a[0,0,0]=1e6+1
    elif fault=='normal':n*=2
    elif fault=='one-jac':kwargs['left_jacobian']=np.zeros(a.shape+(2,))
    elif fault.startswith('jac-'):
        ja=np.zeros(a.shape+(2,));jb=ja.copy()
        if fault=='jac-shape':jb=jb[:,:2]
        elif fault=='jac-columns':jb=np.zeros(a.shape+(3,))
        elif fault=='jac-nan':ja[0,0,0,0]=np.nan
        else:ja=ja.astype(bool)
        kwargs.update(left_jacobian=ja,right_jacobian=jb)
    elif fault=='budget':kwargs.update(left_jacobian=np.zeros(a.shape+(2,)),right_jacobian=np.zeros(a.shape+(2,)),maximum_jacobian_bytes=1)
    elif fault=='working':kwargs['maximum_working_bytes']=1
    elif fault=='gap':kwargs['minimum_gap_m']=-1.
    else:kwargs['length_scale_m']=0.
    with pytest.raises(ValueError):projection_rows(a,b,n,**kwargs)


@pytest.mark.parametrize('value',[0.,True,float('nan'),1e-5])
def test_invalid_axis_threshold_rejects(value):
    a,b,_=fixture()
    with pytest.raises(ValueError):choose_directions(a,b,minimum_axis_norm=value)
