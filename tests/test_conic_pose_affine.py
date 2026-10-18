from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from conic_pose_minimax import minimax_step


def test_vector_contact_blocks_sideways_drift_allowed_by_scalar_tangent():
    m=np.array([-.8,.01]);j=np.array([[0.,1.,0.],[-1.,0.,0.]])
    options=dict(trust=1.,protected_rows=np.array([False,True]))
    scalar,_=minimax_step(m,j,np.zeros(3),**options)
    offset=np.array([[.99,0.,0.]])
    assert scalar is not None and np.linalg.norm(offset[0]+scalar)>1.
    step,r=minimax_step(m,j,np.zeros(3),affine_vectors=offset,
        affine_jacobian=np.eye(3)[None],affine_radii=np.ones(1),**options)
    assert step is not None and np.linalg.norm(offset[0]+step)<=1.
    assert r['maximum_affine_norm_excess']<=0 and r['affine_norm_constraints']==1
    assert np.all(m[options['protected_rows']]+j[options['protected_rows']]@step>=0)
    assert r['predicted_maximum_model_violation']<.8


def test_fixed_impossible_contact_returns_no_proposal_without_dropping_it():
    step,r=minimax_step(np.array([-1.]),np.ones((1,3)),np.zeros(3),
        affine_vectors=np.array([[2.,0.,0.]]),affine_jacobian=np.zeros((1,3,3)),affine_radii=np.ones(1))
    assert step is None and not r['usable_direction'] and r['affine_norm_constraints']==1
    assert r['omitted_affine_norm_constraints']==0 and not r['quality_approved'] and not r['release_approved']


def test_both_actors_last_contact_and_original_control_balls_remain():
    # Third contact constrains relative A/B displacement, including all columns.
    t=np.zeros((3,3,6));t[0,:,:3]=np.eye(3);t[1,:,3:]=np.eye(3)
    t[2,:,:3]=np.eye(3);t[2,:,3:]=-np.eye(3)
    x=np.array([.8,0,0,-.8,0,0]);v=np.array([[.1,0,0],[-.1,0,0],[.2,0,0]])
    radii=np.array([.4,.4,.21])
    step,r=minimax_step(np.array([-4.]),np.array([[1.,1.,1.,-1.,-1.,-1.]]),x,trust=1.,
        affine_vectors=v,affine_jacobian=t,affine_radii=radii)
    assert step is not None and np.all(np.linalg.norm(v+np.einsum('bcj,j->bc',t,step),axis=1)<=radii)
    assert np.all(np.linalg.norm((x+step).reshape(-1,3),axis=1)<=1)
    assert r['affine_norm_constraints']==3 and r['control_vector_balls']==2 and r['model_rows']==1


def test_feasible_fixed_contact_is_retained_and_radius_is_not_control_budget():
    step,r=minimax_step(np.array([-1.]),np.array([[0.,1.,0.]]),np.zeros(3),
        affine_vectors=np.array([[.001,0,0]]),affine_jacobian=np.zeros((1,3,3)),affine_radii=np.array([.002]))
    assert step is not None and .24<step[1]<=.25 and r['affine_norm_constraints']==1
    assert r['maximum_affine_norm_excess']==pytest.approx(-.001)


def test_tiny_affine_bound_excess_is_not_accepted_as_solver_tolerance(monkeypatch):
    from types import SimpleNamespace
    import conic_pose_minimax as module
    real=module.solver_module()
    delta=.1+1e-13
    fit=SimpleNamespace(status='Solved',x=[delta,0,0,delta,0,0,1.])
    proxy=SimpleNamespace(NonnegativeConeT=real.NonnegativeConeT,
        SecondOrderConeT=real.SecondOrderConeT,DefaultSettings=real.DefaultSettings,
        DefaultSolver=lambda *args:SimpleNamespace(solve=lambda:fit),__version__=real.__version__)
    monkeypatch.setattr(module,'solver_module',lambda:proxy)
    step,r=module.minimax_step(np.array([-1.]),np.ones((1,3)),np.zeros(3),
        affine_vectors=np.zeros((1,3)),affine_jacobian=np.eye(3)[None],affine_radii=np.array([.1]))
    assert r['maximum_linear_model_residual']<=1e-8 and r['maximum_actual_control_norm_excess']<=0
    assert 0<r['maximum_affine_norm_excess']<1e-12 and step is None


@pytest.mark.parametrize('fault',['partial','empty','shape','columns','radii','zero','negative','nan','complex','bool','budget','too_many'])
def test_incomplete_or_invalid_affine_model_rejected(fault):
    options=dict(affine_vectors=np.zeros((1,3)),affine_jacobian=np.zeros((1,3,3)),affine_radii=np.ones(1))
    if fault=='partial':options.pop('affine_radii')
    elif fault=='empty':options.update(affine_vectors=np.empty((0,3)),affine_jacobian=np.empty((0,3,3)),affine_radii=np.empty(0))
    elif fault=='shape':options['affine_vectors']=np.zeros((1,4))
    elif fault=='columns':options['affine_jacobian']=np.zeros((1,3,6))
    elif fault=='radii':options['affine_radii']=np.ones(2)
    elif fault=='zero':options['affine_radii']=np.zeros(1)
    elif fault=='negative':options['affine_radii']=-np.ones(1)
    elif fault=='nan':options['affine_vectors'][0,0]=np.nan
    elif fault=='complex':options['affine_jacobian']=np.zeros((1,3,3),dtype=complex)
    elif fault=='bool':options['affine_radii']=np.ones(1,dtype=bool)
    elif fault=='budget':options['maximum_bytes']=1500
    else:options.update(affine_vectors=np.zeros((8193,3)),affine_jacobian=np.zeros((8193,3,3)),affine_radii=np.ones(8193))
    with pytest.raises(ValueError):minimax_step(np.array([-1.]),np.ones((1,3)),np.zeros(3),**options)
