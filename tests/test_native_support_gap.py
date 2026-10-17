"""Geometric, conservative-bound and derivative fixtures independent of FK."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_gap import MAXIMUM_PAIRS, triangle_support_gaps


def fixture():
    a=np.array([[[0.,0.,0.],[.2,1.,0.],[-.1,0.,1.]]])
    return a,a+np.array([1.,0.,0.]),np.array([[1.,0.,0.]])


def test_all_vertices_determine_the_separation_extrema():
    a,b,n=fixture();r=triangle_support_gaps(a,b,n)
    assert r['projected_gap_m'][0] == pytest.approx(.7)
    b[0,2,0]=-.3
    assert triangle_support_gaps(a,b,n)['projected_gap_m'][0] == pytest.approx(-.5)


def test_duplicate_vertices_have_known_entropy_correction_and_symmetric_gradient():
    a=np.zeros((2,3,3));b=a+np.array([2.,0,0]);n=np.array([[1.,0,0]]*2);t=.01
    r=triangle_support_gaps(a,b,n,temperature_m=t)
    np.testing.assert_allclose(r['smooth_gap_m'],2-2*t*np.log(3),atol=1e-15)
    np.testing.assert_allclose(r['left_gradient'],-n[:,None,:]/3+np.zeros_like(a))
    np.testing.assert_allclose(r['right_gradient'],n[:,None,:]/3+np.zeros_like(b))


@pytest.mark.parametrize('temperature',[1e-9,1e-5,.1])
def test_smooth_gap_is_conservative_and_error_is_bounded(temperature):
    rng=np.random.default_rng(721);a=rng.normal(size=(73,3,3));b=rng.normal(size=a.shape);n=rng.normal(size=(73,3));n/=np.linalg.norm(n,axis=1)[:,None]
    r=triangle_support_gaps(a,b,n,temperature_m=temperature);error=r['projected_gap_m']-r['smooth_gap_m']
    assert np.all(error>=0)
    assert np.all(error<=2*temperature*np.log(3)+2e-15)


def test_every_vertex_gradient_matches_central_differences_near_support_ties():
    rng=np.random.default_rng(734);a=rng.normal(size=(2,3,3))*.003;b=rng.normal(size=a.shape)*.003;n=np.array([[1.,0,0],[0,1.,0]])
    r=triangle_support_gaps(a,b,n,temperature_m=.01);step=1e-7
    for side,points in [('left',a),('right',b)]:
        for index in np.ndindex(points.shape):
            plus=points.copy();minus=points.copy();plus[index]+=step;minus[index]-=step
            args1=(plus,b,n) if side=='left' else (a,plus,n)
            args2=(minus,b,n) if side=='left' else (a,minus,n)
            fd=(triangle_support_gaps(*args1,temperature_m=.01)['smooth_gap_m']-triangle_support_gaps(*args2,temperature_m=.01)['smooth_gap_m'])/(2*step)
            expected=np.zeros(2);expected[index[0]]=r[side+'_gradient'][index]
            np.testing.assert_allclose(fd,expected,atol=6e-11,rtol=2e-8)


def test_common_translation_rotation_and_side_reversal_preserve_gaps():
    a,b,n=fixture();r=triangle_support_gaps(a,b,n);q=np.array([[0.,-1,0],[1,0,0],[0,0,1.]])
    moved=triangle_support_gaps(a@q.T+[10000.,-20000.,30000.],b@q.T+[10000.,-20000.,30000.],n@q.T)
    reverse=triangle_support_gaps(b,a,-n)
    for key in ['projected_gap_m','smooth_gap_m']:
        np.testing.assert_allclose(moved[key],r[key],atol=3e-12,rtol=0)
        np.testing.assert_allclose(reverse[key],r[key],atol=1e-15,rtol=0)
    np.testing.assert_allclose(moved['left_gradient'],r['left_gradient']@q.T,atol=3e-12)
    np.testing.assert_allclose(reverse['left_gradient'],r['right_gradient'],atol=1e-15)


@pytest.mark.parametrize('temperature',[0.,-1.,True,float('nan'),float('inf'),1e-10,.1001,'0.01'])
def test_invalid_temperature_rejects(temperature):
    with pytest.raises(ValueError):triangle_support_gaps(*fixture(),temperature_m=temperature)


@pytest.mark.parametrize('kind',['empty','too_many','shape','normal_shape','nonunit','nan','infinite','large','huge_normal','complex','bool','string'])
def test_invalid_geometry_rejects(kind):
    a,b,n=fixture()
    if kind=='empty':a=a[:0];b=b[:0];n=n[:0]
    elif kind=='too_many':a=np.zeros((MAXIMUM_PAIRS+1,3,3));b=a.copy();n=np.tile([1.,0,0],(len(a),1))
    elif kind=='shape':b=b[:,:2,:]
    elif kind=='normal_shape':n=n[0]
    elif kind=='nonunit':n*=2
    elif kind=='nan':a[0,0,0]=np.nan
    elif kind=='infinite':b[0,0,0]=np.inf
    elif kind=='large':a[0,0,0]=1e6+1
    elif kind=='huge_normal':n[0,0]=1e300
    elif kind=='complex':a=a.astype(complex)
    elif kind=='bool':a=a.astype(bool)
    else:a=a.astype(str)
    with pytest.raises(ValueError):triangle_support_gaps(a,b,n)
