import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inward_feasibility_step import inward_step


def test_all_failed_rows_get_inward_progress():
    x=np.zeros(2);g=np.array([1.,2.]);j=np.eye(2)
    step,info=inward_step(x,g,j,-np.ones(2),np.ones(2),np.full(2,.1))
    assert info['success'] and info['common_improvement']==pytest.approx(.1)
    assert np.all(g+j@step<g-.099)
    assert np.max(np.abs(step))<=.1


def test_conflicting_rows_do_not_return_a_tradeoff_as_progress():
    step,info=inward_step(np.zeros(1),np.ones(2),np.array([[1.],[-1.]]),[-1.],[1.],[.1])
    assert step is None and info['common_improvement']==0.


def test_passing_constraint_stays_protected():
    g=np.array([1.,-.02]);j=np.array([[1.],[-1.]])
    step,info=inward_step(np.zeros(1),g,j,[-1.],[1.],[.1])
    assert info['common_improvement']==pytest.approx(.02)
    assert (g+j@step)[1]<=1e-9 and step[0]<-.019


def test_inward_direction_has_room_for_nonlinear_curvature():
    # Each failed row has an independent first-order inward direction;
    # the quadratic cross term consumes some, but not all, of its reserve.
    step,info=inward_step(np.zeros(2),np.ones(2),np.eye(2),[-1.,-1.],[1.,1.],[.1,.1])
    actual=np.array([1+step[0]+step[1]**2,1+step[1]+step[0]**2])
    assert np.all(actual<1.)


@pytest.mark.parametrize('radius,lower,upper', [([0.],[-1.],[1.]),([float('nan')],[-1.],[1.]),([.1],[1.],[2.]),([.1],[1.],[-1.])])
def test_invalid_or_out_of_bounds_inputs_rejected(radius,lower,upper):
    with pytest.raises(ValueError):inward_step([0.],[1.],[[1.]],lower,upper,radius)
