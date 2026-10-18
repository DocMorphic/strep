from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from conic_pose_minimax import minimax_step


def test_balances_worst_constraint_not_average_error():
    margin=np.array([-1.,-.6,-.6]);jac=np.array([[-.1,0,0],[1.,0,0],[1.,0,0]])
    step,r=minimax_step(margin,jac,np.zeros(3),trust=1.)
    assert step is not None and step[0]<0 and r['predicted_maximum_model_violation']<1
    assert r['model_rows']==3 and r['omitted_rows']==r['omitted_control_balls']==0


def test_conflicting_contact_rows_remain_visible():
    step,r=minimax_step(np.array([-1.,.5]),np.array([[1.,0,0],[-1.,0,0]]),np.zeros(3),trust=1.)
    assert step is not None and step[0]==pytest.approx(.75,abs=1e-6)
    assert r['predicted_maximum_model_violation']==pytest.approx(.25,abs=1e-6)
    assert not r['quality_approved'] and not r['release_approved']


def test_exact_vector_ball_prevents_componentwise_box_overshoot():
    step,r=minimax_step(np.array([-5.]),np.ones((1,3)),np.zeros(3),trust=1.)
    assert step is not None and np.linalg.norm(step)<=1
    assert r['predicted_maximum_model_violation']==pytest.approx(5-np.sqrt(3),abs=1e-6)


def test_nonzero_initial_controls_keep_original_relative_ball():
    point=np.array([.8,0,0]);step,r=minimax_step(np.array([-2.]),np.ones((1,3)),point,trust=1.)
    assert step is not None and np.linalg.norm(point+step)<=1 and r['maximum_actual_control_norm_excess']<=0


def test_two_actor_control_balls_and_last_row_not_dropped():
    margin=np.r_[np.ones(3),-2.];jac=np.zeros((4,6));jac[-1]=1
    step,r=minimax_step(margin,jac,np.zeros(6),trust=1.)
    assert step is not None and np.all(np.linalg.norm(step.reshape(-1,3),axis=1)<=1)
    assert r['control_vector_balls']==2 and r['model_rows']==4 and r['predicted_maximum_model_violation']<1e-6


def test_uneditable_failed_row_is_not_an_infeasibility_claim():
    step,r=minimax_step(np.array([-2.,-.5]),np.array([[0.,0,0],[1.,0,0]]),np.zeros(3))
    assert step is not None and r['predicted_maximum_model_violation']==2 and r['model_rows']==2


@pytest.mark.parametrize('fault',['shape','groups','outside','nan','budget','trust'])
def test_invalid_complete_model_rejects(fault):
    m=np.array([-1.]);j=np.ones((1,3));x=np.zeros(3);options={}
    if fault=='shape':m=np.ones(2)
    elif fault=='groups':j=np.ones((1,4));x=np.zeros(4)
    elif fault=='outside':x[:]=1.
    elif fault=='nan':j[0,0]=float('nan')
    elif fault=='budget':options['maximum_bytes']=1
    else:options['trust']=0
    with pytest.raises(ValueError):minimax_step(m,j,x,**options)
