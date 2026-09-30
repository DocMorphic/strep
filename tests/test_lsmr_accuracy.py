import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from lsmr_accuracy import measure


def test_larger_cap_measures_the_same_system_and_reports_remaining_error():
    a=np.diag(np.geomspace(.1,10,16));rhs=np.ones(16)
    _,short=measure(a,rhs,dict(maxiter=2,atol=1e-12,btol=1e-12))
    fit,long=measure(a,rhs,dict(maxiter=100,atol=1e-12,btol=1e-12))
    assert short['stop_code']==7 and short['iterations']==2
    assert long['normal_norm']<short['normal_norm']*1e-6
    np.testing.assert_allclose(a@fit[0],rhs,atol=1e-8)
    assert long['normal_norm']==pytest.approx(np.linalg.norm(a.T@(a@fit[0]-rhs)))


def test_damping_is_included_in_independent_stationarity_measure():
    a=np.array([[1.,2.],[3.,4.],[2.,-1.]]);rhs=np.array([1.,-1.,.3]);damp=.5
    fit,record=measure(a,rhs,dict(maxiter=50,damp=damp,atol=1e-12,btol=1e-12))
    expected=np.linalg.solve(a.T@a+damp*damp*np.eye(2),a.T@rhs)
    np.testing.assert_allclose(fit[0],expected,atol=1e-12)
    assert record['normal_norm']<1e-10
    assert record['regularized_residual_norm']>record['residual_norm']


def test_invalid_rhs_is_rejected():
    with pytest.raises(ValueError):measure(np.eye(2),[float('nan'),0],dict(maxiter=2))
