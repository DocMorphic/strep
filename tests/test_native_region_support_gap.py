"""Complete extrema/gradient checks and the stronger-envelope limitation."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_region_support_gap import MAXIMUM_VERTICES, region_support_gap, pair_hinge_objective
from native_support_gap import triangle_support_gaps


def fixture():
    a=np.array([[0.,0.,0.],[.2,1.,0.],[-.1,0.,1.],[.3,-1.,0.]])
    return a,np.array([[1.,0,0],[1.2,1.,0],[.9,0.,1]]),np.array([1.,0,0])


def test_unequal_complete_point_sets_keep_last_extrema():
    a,b,n=fixture();result=region_support_gap(a,b,n)
    assert result['projected_gap_m']==pytest.approx(.6)
    a[-1,0]=.7;b[-1,0]=.8
    assert region_support_gap(a,b,n)['projected_gap_m']==pytest.approx(.1)
    assert result['left_gradient'].shape==a.shape and result['right_gradient'].shape==b.shape


@pytest.mark.parametrize('counts',[(1,1),(4,7),(17,31)])
def test_tied_supports_have_known_entropy_and_all_vertex_gradients(counts):
    na,nb=counts;a=np.zeros((na,3));b=np.zeros((nb,3));b[:,0]=2.;n=np.array([1.,0,0]);t=.01
    result=region_support_gap(a,b,n,temperature_m=t)
    assert result['projected_gap_m']==2.
    assert result['smooth_gap_m']==pytest.approx(2-t*(np.log(na)+np.log(nb)))
    np.testing.assert_array_equal(result['left_gradient'],np.tile(-n/na,(na,1)))
    np.testing.assert_array_equal(result['right_gradient'],np.tile(n/nb,(nb,1)))


@pytest.mark.parametrize('temperature',[1e-9,1e-5,.1])
def test_conservative_bound_uses_both_complete_populations(temperature):
    rng=np.random.default_rng(615);a=rng.normal(size=(17,3));b=rng.normal(size=(31,3));n=rng.normal(size=3);n/=np.linalg.norm(n)
    result=region_support_gap(a,b,n,temperature_m=temperature);error=result['projected_gap_m']-result['smooth_gap_m']
    assert 0<=error<=result['maximum_entropy_error_m']+2e-15
    assert result['maximum_entropy_error_m']==temperature*(np.log(17)+np.log(31))


def test_every_vertex_derivative_matches_finite_difference_near_ties():
    rng=np.random.default_rng(616);a=rng.normal(size=(4,3))*.003;b=rng.normal(size=(7,3))*.003;n=np.array([.6,0,.8]);t=.01;step=1e-7
    result=region_support_gap(a,b,n,temperature_m=t)
    for side,points in [('left',a),('right',b)]:
        for index in np.ndindex(points.shape):
            plus=points.copy();minus=points.copy();plus[index]+=step;minus[index]-=step
            first=(plus,b,n) if side=='left' else (a,plus,n);last=(minus,b,n) if side=='left' else (a,minus,n)
            finite=(region_support_gap(*first,temperature_m=t)['smooth_gap_m']-region_support_gap(*last,temperature_m=t)['smooth_gap_m'])/(2*step)
            assert finite==pytest.approx(result[side+'_gradient'][index],abs=7e-11,rel=2e-8)
    np.testing.assert_allclose(result['left_gradient'].sum(axis=0),-n,atol=2e-16)
    np.testing.assert_allclose(result['right_gradient'].sum(axis=0),n,atol=2e-16)


def test_rigid_transform_and_side_reversal_keep_gap_and_gradients():
    a,b,n=fixture();q=np.array([[0.,-1,0],[1,0,0],[0,0,1.]]);result=region_support_gap(a,b,n)
    moved=region_support_gap(a@q.T+[10000.,-20000.,30000.],b@q.T+[10000.,-20000.,30000.],n@q.T);reverse=region_support_gap(b,a,-n)
    for key in ['projected_gap_m','smooth_gap_m']:
        assert moved[key]==pytest.approx(result[key],abs=3e-12,rel=0)
        assert reverse[key]==pytest.approx(result[key],abs=1e-15,rel=0)
    np.testing.assert_allclose(moved['left_gradient'],result['left_gradient']@q.T,atol=3e-12)
    np.testing.assert_array_equal(reverse['left_gradient'],result['right_gradient'])


def test_complete_region_implies_every_covered_triangle_gap():
    rng=np.random.default_rng(617);a=rng.normal(size=(19,3))*.01;b=rng.normal(size=(23,3))*.01;b[:,0]+=1;n=np.array([1.,0,0])
    ai=rng.integers(0,len(a),size=(79,3));bi=rng.integers(0,len(b),size=(79,3))
    region=region_support_gap(a,b,n);pairs=triangle_support_gaps(a[ai],b[bi],np.tile(n,(len(ai),1)))
    assert np.all(pairs['projected_gap_m']>=region['projected_gap_m']-2e-15)
    assert region['projected_gap_m']>.9


def test_region_can_fail_when_each_original_triangle_pair_passes():
    a=np.array([[0.,0,0],[.1,1,0],[0.,0,1],[1.,3,0],[1.1,4,0],[1.,3,1]])
    b=a+np.array([.2,0,0]);n=np.array([1.,0,0]);pairs=triangle_support_gaps(a.reshape(2,3,3),b.reshape(2,3,3),np.tile(n,(2,1)))
    assert np.all(pairs['projected_gap_m']>0)
    assert region_support_gap(a,b,n)['projected_gap_m']<0


def test_input_arrays_are_unchanged_and_no_output_aliases_positions():
    a,b,n=fixture();copies=[x.copy() for x in (a,b,n)];result=region_support_gap(a,b,n)
    for original,copy in zip((a,b,n),copies):np.testing.assert_array_equal(original,copy)
    assert not np.shares_memory(result['left_gradient'],a) and not np.shares_memory(result['right_gradient'],b)


def test_full_vertex_budget_keeps_final_point_and_rejects_extra():
    a=np.zeros((MAXIMUM_VERTICES,3));a[-1,0]=.25;b=np.array([[1.,0,0]]);n=np.array([1.,0,0])
    result=region_support_gap(a,b,n);assert result['projected_gap_m']==.75 and result['left_gradient'].shape==a.shape
    with pytest.raises(ValueError):region_support_gap(np.r_[a,[[0.,0,0]]],b,n)


@pytest.mark.parametrize('kind',['empty-left','empty-right','left-shape','right-shape','normal-shape','nonunit','nan','inf','large','huge-normal','bool','complex','string'])
def test_invalid_geometry_rejects(kind):
    a,b,n=fixture()
    if kind=='empty-left':a=a[:0]
    elif kind=='empty-right':b=b[:0]
    elif kind=='left-shape':a=a[:,:2]
    elif kind=='right-shape':b=b.ravel()
    elif kind=='normal-shape':n=n[None,:]
    elif kind=='nonunit':n*=2
    elif kind=='nan':a[0,0]=np.nan
    elif kind=='inf':b[0,0]=np.inf
    elif kind=='large':a[0,0]=1e6+1
    elif kind=='huge-normal':n[0]=1e300
    elif kind=='bool':a=a.astype(bool)
    elif kind=='complex':a=a.astype(complex)
    else:b=b.astype(str)
    with pytest.raises(ValueError):region_support_gap(a,b,n)


@pytest.mark.parametrize('temperature',[0.,-1.,True,float('nan'),float('inf'),1e-10,.1001,'0.01'])
def test_invalid_temperature_rejects(temperature):
    with pytest.raises(ValueError):region_support_gap(*fixture(),temperature_m=temperature)


@pytest.mark.parametrize('block',[1,3,64,1024])
def test_blocked_pair_objective_matches_expanded_moving_region_chain(block):
    rng=np.random.default_rng(20261025)
    a=rng.normal(size=(7,3))*.02;b=rng.normal(size=(13,3))*.02;n=np.array([.6,0,.8])
    ja=rng.normal(size=(len(a),3,5));jb=rng.normal(size=(len(b),3,5))
    actual=pair_hinge_objective(a,b,n,clearance_m=.003,scale_m=.01,block_rows=block)
    gaps=np.array([n@(v-u) for u in a for v in b]);bad=np.minimum((gaps-.003)/.01,0.)
    full_jac=np.array([n@(dv-du) for du in ja for dv in jb])/.01
    expected_loss=bad@bad;expected_gradient=2*bad@full_jac
    chain=np.einsum('vi,vij->j',actual['left_gradient'],ja)+np.einsum('vi,vij->j',actual['right_gradient'],jb)
    assert actual['loss']==pytest.approx(expected_loss,rel=2e-14,abs=1e-12)
    np.testing.assert_allclose(chain,expected_gradient,rtol=2e-13,atol=2e-10)
    assert actual['report']['pair_rows']==91 and actual['report']['all_pairs_retained']
    assert not actual['report']['quality_approved']
    for column in range(5):
        h=1e-7
        plus=pair_hinge_objective(a+h*ja[:,:,column],b+h*jb[:,:,column],n,clearance_m=.003)['loss']
        minus=pair_hinge_objective(a-h*ja[:,:,column],b-h*jb[:,:,column],n,clearance_m=.003)['loss']
        assert (plus-minus)/(2*h)==pytest.approx(chain[column],rel=2e-8,abs=2e-6)


def test_pair_objective_keeps_last_pair_and_shared_point_deficit():
    a=np.zeros((129,3));b=np.ones((131,3));a[-1,0]=2.;n=np.array([1.,0,0])
    result=pair_hinge_objective(a,b,n,clearance_m=0.,scale_m=1.)
    assert result['loss']==131. and result['projected_gap_m']==-1.
    assert result['report']['pair_rows']==129*131
    np.testing.assert_array_equal(result['left_gradient'][:-1],0.)
    shared=pair_hinge_objective(a[:1],a[:1],n,clearance_m=.003)
    assert shared['loss']==pytest.approx(.09)
    assert np.any(shared['left_gradient']) and np.any(shared['right_gradient'])


def test_pair_objective_zero_loss_and_joint_translation_cancel():
    a,b,n=fixture();clean=pair_hinge_objective(a,b,n)
    assert clean['loss']==0. and not np.any(clean['left_gradient']) and not np.any(clean['right_gradient'])
    b-=1.;result=pair_hinge_objective(a,b,n);reverse=pair_hinge_objective(b,a,-n,block_rows=1)
    assert result['loss']==pytest.approx(reverse['loss'])
    np.testing.assert_allclose(result['left_gradient'],reverse['right_gradient'])
    np.testing.assert_allclose(result['left_gradient'].sum(axis=0)+result['right_gradient'].sum(axis=0),0.,atol=1e-10)
    copies=[x.copy() for x in (a,b,n)];pair_hinge_objective(a,b,n)
    for value,copy in zip((a,b,n),copies):np.testing.assert_array_equal(value,copy)


@pytest.mark.parametrize('kwargs',[
    {'clearance_m':True},{'clearance_m':-.1},{'clearance_m':float('nan')},
    {'scale_m':0.},{'scale_m':float('inf')},{'scale_m':1e-9},
    {'block_rows':0},{'block_rows':True},{'block_rows':1025},
    {'maximum_pairs':0},{'maximum_pairs':11},{'maximum_pairs':2_000_001},
    {'maximum_working_bytes':1},{'maximum_working_bytes':True},{'maximum_working_bytes':64*1024**2+1},
])
def test_pair_objective_rejects_incomplete_or_unbounded_requests(kwargs):
    with pytest.raises(ValueError):pair_hinge_objective(*fixture(),**kwargs)


@pytest.mark.parametrize('fault',['empty','shape','nan','normal','bool','huge'])
def test_pair_objective_rejects_invalid_point_populations(fault):
    a,b,n=fixture()
    if fault=='empty':a=a[:0]
    elif fault=='shape':b=b.ravel()
    elif fault=='nan':a[0,0]=np.nan
    elif fault=='normal':n*=2.
    elif fault=='bool':a=a.astype(bool)
    else:a[0,0]=1e6+1
    with pytest.raises(ValueError):pair_hinge_objective(a,b,n)
