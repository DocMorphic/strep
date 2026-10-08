import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inequality_restoration import restoration_residual


def test_only_violated_inequalities_enter_the_restoration_residual():
    x=np.array([.2,-.1]);seed=np.zeros(2);slack=np.array([-.02,0.,.03]);jac=np.array([[1.,2.],[3.,4.],[5.,6.]])
    residual,derivative=restoration_residual(x,seed,slack,jac)
    np.testing.assert_array_equal(residual[:3],[-.02,0.,0.])
    np.testing.assert_array_equal(derivative[:3],[jac[0],[0,0],[0,0]])
    np.testing.assert_allclose(residual[3:],1e-5*x)
    np.testing.assert_array_equal(derivative[3:],1e-5*np.eye(2))


def test_regularized_directional_jacobian_matches_finite_differences_away_from_boundary():
    x=np.array([.2,-.1]);seed=np.zeros(2);matrix=np.array([[1.,2.],[3.,4.],[5.,6.]])
    def pair(z):return restoration_residual(z,seed,matrix@z+[-.03,.3,.3],matrix)
    direction=np.array([.2,.4]);h=1e-7
    np.testing.assert_allclose(pair(x)[1]@direction,(pair(x+h*direction)[0]-pair(x-h*direction)[0])/(2*h),rtol=1e-8,atol=1e-9)


@pytest.mark.parametrize('change',[
    dict(parameters=[[1,2]]),dict(seed=[0]),dict(slacks=[float('nan')]),
    dict(jacobian=[[float('inf'),1]]),dict(regularization=0),dict(regularization=True)])
def test_invalid_residual_populations_are_rejected(change):
    args=dict(parameters=[1,2],seed=[0,0],slacks=[-.1],jacobian=[[1,1]])
    args.update(change)
    with pytest.raises(ValueError):restoration_residual(**args)


def test_small_residual_is_not_a_feasibility_certificate():
    residual,_=restoration_residual([0],[0],[-1e-9],[[1]])
    assert residual@residual<1e-15 and residual[0]<0
