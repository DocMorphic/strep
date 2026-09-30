import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.optimize import least_squares
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from torch_jacobian_operator import TorchJacobianOperator


def residual(x):return torch.stack([x[0]**2+3*x[1],torch.sin(x[0])-x[1]**2,x[0]*0+7])


def test_both_products_match_dense_jacobian_and_adjoint():
    x=np.array([.3,-.4]);op=TorchJacobianOperator(residual,x)
    dense=np.array([[.6,3.],[np.cos(.3),.8],[0.,0.]])
    v=np.array([.7,.2]);w=np.array([-.4,.3,.8])
    np.testing.assert_allclose(op@v,dense@v,atol=1e-13)
    np.testing.assert_allclose(op.T@w,dense.T@w,atol=1e-13)
    assert w@(op@v)==pytest.approx(v@(op.T@w),abs=1e-13)
    np.testing.assert_allclose(op@np.eye(2),dense,atol=1e-13)
    np.testing.assert_allclose(op.values,residual(torch.tensor(x)).numpy())
    np.testing.assert_allclose(op@v,dense@v,atol=1e-13)  # graph remains reusable


def test_constant_function_has_zero_products():
    op=TorchJacobianOperator(lambda x:torch.ones(3,dtype=torch.float64),[1.,2.])
    np.testing.assert_array_equal(op@np.ones(2),np.zeros(3))
    np.testing.assert_array_equal(op.T@np.ones(3),np.zeros(2))


def test_least_squares_uses_operator_without_dense_jacobian():
    a=torch.tensor([[1.,2.],[3.,-1.],[2.,1.]],dtype=torch.float64)
    target=a@torch.tensor([.2,.4],dtype=torch.float64)
    f=lambda x:a@x-target
    fit=least_squares(lambda x:f(torch.tensor(x,dtype=torch.float64)).numpy(),[0.,0.],
        jac=lambda x:TorchJacobianOperator(f,x),method='trf',tr_solver='lsmr',bounds=([-1.,-1.],[1.,1.]),
        ftol=1e-12,xtol=1e-12,gtol=1e-12)
    assert fit.success
    np.testing.assert_allclose(fit.x,[.2,.4],atol=1e-10)


def test_guard_interrupts_products():
    calls=[]
    def guard():
        calls.append(1)
        if len(calls)>2:raise TimeoutError('budget')
    op=TorchJacobianOperator(residual,[.3,-.4],guard)
    with pytest.raises(TimeoutError):op@np.ones(2)


@pytest.mark.parametrize('point', [[],[float('nan')],[[1.,2.]]])
def test_invalid_point_rejected(point):
    with pytest.raises(ValueError):TorchJacobianOperator(residual,point)
