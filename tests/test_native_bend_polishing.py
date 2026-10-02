"""Early optimizer termination must not weaken the quadratic or box checks."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_leg_smoothing as smoothing


@pytest.mark.parametrize('fixed',[False,True])
def test_same_objective_active_set_finishes_stopped_optimizer_with_independent_kkt(tmp_path,monkeypatch,fixed):
    monkeypatch.setattr(smoothing,'minimize',lambda fn,x,**kw:SimpleNamespace(x=x.copy(),success=False,message='fixture stopped early',nit=1))
    t=np.array([0.,.031,.093,.217,.51,.9]);lo=np.array([.21,.27,.24,.4,.22,.19]);hi=np.full(6,1.8)
    if fixed:hi[[0,-1]]=lo[[0,-1]]
    tau=.15;mu=.5;x,r=smoothing.smooth(t,lo,hi,acceleration_time=tau,reference_weight=mu)
    dt=np.diff(t);mid=(dt[:-1]+dt[1:])/2
    d=np.diff(np.eye(len(t)),axis=0)/dt[:,None];dd=np.diff(d,axis=0)/mid[:,None]
    w=np.r_[dt[0]/2,mid,dt[-1]/2]
    h=d.T@np.diag(dt)@d+tau*tau*dd.T@np.diag(mid)@dd+mu*np.diag(w)
    g=h@x-mu*w*lo
    assert np.all(x>=lo) and np.all(x<=hi)
    free=(x>lo+1e-10)&(x<hi-1e-10)
    np.testing.assert_allclose(g[free],0.,atol=1e-10,rtol=0)
    assert np.all(g[(x==lo)&(lo!=hi)]>=-1e-10)
    assert np.all(g[(x==hi)&(lo!=hi)]<=1e-10)
    expected=np.sum(dt*(d@x)**2)+tau*tau*np.sum(mid*(dd@x)**2)+mu*np.sum(w*(x-lo)**2)
    assert r['objective']==pytest.approx(expected,rel=1e-13)
    p=r['polishing'];assert p['method']=='same_objective_bounded_least_squares' and r['projected_gradient_residual']<1e-7
    assert p['numerical_objective_after']<=p['numerical_objective_before']+1e-14


@pytest.mark.parametrize('fault',['box','stationarity','success'])
def test_bad_polishing_cannot_bypass_original_gate(monkeypatch,fault):
    monkeypatch.setattr(smoothing,'minimize',lambda fn,x,**kw:SimpleNamespace(x=x.copy(),success=False,message='fixture early',nit=1))
    def bad(matrix,target,**kw):
        lo,hi=kw['bounds'];x=lo.copy()
        if fault=='box':x[0]=hi[0]+.1
        return SimpleNamespace(x=x,success=fault!='success',nit=1)
    monkeypatch.setattr(smoothing,'lsq_linear',bad)
    with pytest.raises(ValueError,match='did not converge'):
        smoothing.smooth([0.,.1,.3,.8],[.2,.5,.2,.2],[1.]*4)
