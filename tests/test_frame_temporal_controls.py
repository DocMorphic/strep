from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from frame_temporal_controls import FrameTemporalControls


def partition(knots=3):
    t=np.linspace(0,1,9)
    if knots==1:return np.ones((9,1))
    if knots==2:return np.c_[1-t,t]
    a=(1-t)**2;b=2*t*(1-t);return np.c_[a,b,1-(a+b)]


@pytest.mark.parametrize('knots',[1,2,3])
@pytest.mark.parametrize('chunk',[1,8,129])
def test_complete_lift_matches_explicit_column_map_and_embedding(knots,chunk):
    w=partition(knots);m=FrameTemporalControls(w,blocks=2,groups=3,constant_groups=[2]);rng=np.random.default_rng(291);j=rng.normal(size=(17,18));frames=np.arange(17)%9;actual=m.lift(j,frames,chunk_rows=chunk);expected=np.zeros_like(actual)
    for r,f in enumerate(frames):
        for b in range(2):
            for k in range(knots):
                for g in range(3):
                    factor=1/knots if g==2 else w[f,k]
                    for c in range(3):expected[r,((b*knots+k)*3+g)*3+c]=j[r,(b*3+g)*3+c]*factor
    np.testing.assert_array_equal(actual,expected);x=rng.normal(size=(6,3))*.1;embedded=m.embed(x.ravel());np.testing.assert_allclose(m.at_frames(embedded,frames),np.broadcast_to(x.ravel(),(len(frames),18)),rtol=0,atol=1e-16)


def test_lift_matches_finite_difference_of_independent_nonlinear_frame_function():
    w=partition();m=FrameTemporalControls(w,blocks=2,groups=2,constant_groups=[1]);rng=np.random.default_rng(721);x=rng.normal(size=36)*.1;unit=rng.normal(size=36);unit/=np.linalg.norm(unit);frames=np.array([1,4,7])
    def values(z):
        q=z.reshape(2,3,2,3);local=np.empty((3,12))
        for r,f in enumerate(frames):
            local[r]=np.stack([np.stack([sum(w[f,k]*q[b,k,0] for k in range(3)),sum(q[b,k,1] for k in range(3))/3]) for b in range(2)]).ravel()
        return local
    local=values(x);j=2*np.sin(local)*np.cos(local);analytic=m.lift(j,frames)@unit;eps=1e-6;numeric=(np.sin(values(x+eps*unit))**2-np.sin(values(x-eps*unit))**2).sum(1)/(2*eps);np.testing.assert_allclose(analytic,numeric,rtol=1e-7,atol=1e-10)


def test_constant_groups_stay_constant_and_input_ownership_is_explicit():
    w=partition();m=FrameTemporalControls(w,blocks=1,groups=2,constant_groups=[1]);saved=m.weights;w[:]=0;saved[:]=0;x=np.arange(18)*.01;y=m.at_frames(x,np.arange(9));np.testing.assert_array_equal(y[:,3:],np.broadcast_to(x.reshape(3,2,3)[:,1].mean(0),(9,3)));assert np.any(y[0,:3]!=y[-1,:3]);assert np.all(m.weights.sum(1)==1)


@pytest.mark.parametrize('change',[
    lambda w:np.zeros_like(w),lambda w:np.full_like(w,np.nan),lambda w:w.astype(bool),lambda w:w.astype(complex),
    lambda w:w[:2],lambda w:np.repeat(w,34,axis=0),lambda w:np.c_[w,np.zeros((9,6))],lambda w:w-.1,lambda w:w+.1,
])
def test_invalid_partitions_reject_without_repair(change):
    with pytest.raises(ValueError):FrameTemporalControls(change(partition()),blocks=1,groups=2)


@pytest.mark.parametrize('kwargs',[dict(blocks=True,groups=2),dict(blocks=0,groups=2),dict(blocks=9,groups=2),dict(blocks=2,groups=18),dict(blocks=8,groups=17),dict(blocks=1,groups=2,constant_groups=[2]),dict(blocks=1,groups=2,constant_groups=[1,1]),dict(blocks=1,groups=2,constant_groups=[True])])
def test_invalid_complete_control_layout_rejects(kwargs):
    with pytest.raises(ValueError):FrameTemporalControls(partition(),**kwargs)


@pytest.mark.parametrize('case',['frames','boolean_frames','negative_frame','out_of_clock','missing_column','complex_j','nan_j','large_j','zero_chunk','bool_chunk','over_budget','invalid_budget','bad_controls','control_ball'])
def test_incomplete_or_unbounded_queries_reject(case):
    m=FrameTemporalControls(partition(),blocks=1,groups=2);j=np.ones((3,6));frames=[0,4,8];kwargs={}
    if case=='frames':frames=[]
    elif case=='boolean_frames':frames=[True,False,True]
    elif case=='negative_frame':frames=[0,-1,8]
    elif case=='out_of_clock':frames=[0,4,9]
    elif case=='missing_column':j=j[:,:5]
    elif case=='complex_j':j=j.astype(complex)
    elif case=='nan_j':j[0,0]=np.nan
    elif case=='large_j':j[0,0]=1e7
    elif case=='zero_chunk':kwargs['chunk_rows']=0
    elif case=='bool_chunk':kwargs['chunk_rows']=True
    elif case=='over_budget':kwargs['maximum_bytes']=1
    elif case=='invalid_budget':kwargs['maximum_bytes']=64*1024**2+1
    elif case=='bad_controls':
        with pytest.raises(ValueError):m.embed(np.zeros(5))
        return
    elif case=='control_ball':
        with pytest.raises(ValueError):m.at_frames(np.ones(18),frames)
        return
    with pytest.raises(ValueError):m.lift(j,frames,**kwargs)


def test_float32_partition_must_still_be_unity_in_owned_coordinates():
    weights=np.tile(np.array([.1,.2,.7],dtype=np.float32),(3,1));assert np.all(weights.sum(1)==1) and np.any(weights.astype(float).sum(1)!=1)
    with pytest.raises(ValueError):FrameTemporalControls(weights,blocks=1,groups=1)


@pytest.mark.parametrize('operation',['embed','at_frames'])
def test_float32_boundary_must_still_fit_owned_control_ball(operation):
    x=np.array([.8,.6,0],dtype=np.float32);assert np.linalg.norm(x)==1 and np.linalg.norm(x.astype(float))>1;m=FrameTemporalControls(np.ones((3,1)),blocks=1,groups=1)
    with pytest.raises(ValueError):m.embed(x) if operation=='embed' else m.at_frames(x,[0,1,2])


def test_exact_float32_coordinates_remain_supported():
    m=FrameTemporalControls(np.tile(np.array([.25,.5,.25],dtype=np.float32),(3,1)),blocks=1,groups=1);x=np.array([.5,.5,0],dtype=np.float32);np.testing.assert_array_equal(m.at_frames(m.embed(x),[0,1,2]),np.tile(x.astype(float),(3,1)))


@pytest.mark.parametrize('dtype',[np.float64,np.longdouble],ids=['double','platform-long-double'])
def test_complete_input_storage_is_counted_before_output_allocation(dtype,monkeypatch):
    m=FrameTemporalControls(np.ones((3,1)),blocks=1,groups=1);rows=1024;j=np.zeros((rows,3),dtype=dtype);frames=np.zeros(rows,dtype=int);minimum_live_bytes=j.nbytes+rows*3*8+m.weights.nbytes+frames.nbytes
    def forbidden(*args,**kwargs):raise AssertionError('Output allocated before rejecting an undersized complete budget')
    monkeypatch.setattr('frame_temporal_controls.np.empty',forbidden)
    with pytest.raises(ValueError):m.lift(j,frames,chunk_rows=1,maximum_bytes=minimum_live_bytes-1)


@pytest.mark.parametrize('bad',[np.nan,np.inf,1e7])
def test_chunk_validation_reaches_last_row_before_output_allocation(bad,monkeypatch):
    m=FrameTemporalControls(np.ones((3,1)),blocks=1,groups=1);j=np.zeros((17,3));j[-1,-1]=bad
    def forbidden(*args,**kwargs):raise AssertionError('Invalid tail omitted before output allocation')
    monkeypatch.setattr('frame_temporal_controls.np.empty',forbidden)
    with pytest.raises(ValueError):m.lift(j,np.arange(17)%3,chunk_rows=2)
