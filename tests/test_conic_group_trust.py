from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from conic_group_trust import group_trust_step


def test_distinct_joint_and_root_step_radii_keep_required_floor_row():
    jac=np.zeros((2,6));jac[0,0]=1;jac[1,3]=1
    step,r=group_trust_step(np.array([-1.,-.7]),jac,np.zeros(6),[.1,1.],protected_rows=np.array([False,True]))
    assert step is not None and np.linalg.norm(step[:3])<=.1 and .7<=step[3]<=1
    assert r['original_author_control_balls']==2 and r['affine_norm_constraints']==2 and not r['source_budget_rebased']


def test_nonzero_source_controls_cannot_be_rebased_by_large_step_radius():
    x=np.array([.9,0,0]);step,r=group_trust_step(np.array([-2.]),np.ones((1,3)),x,[2.])
    assert step is not None and np.linalg.norm(x+step)<=1 and np.linalg.norm(step)<=2
    assert r['maximum_original_control_norm_excess']<=0 and r['maximum_group_step_norm_excess']<=0


def test_norm_trust_is_not_a_componentwise_box():
    step,r=group_trust_step(np.array([-2.]),np.ones((1,3)),np.zeros(3),[.2])
    assert step is not None and np.linalg.norm(step)<=.2
    assert r['predicted_maximum_model_violation']==pytest.approx(2-.2*np.sqrt(3),abs=1e-6)


def test_zero_radius_freezes_group_without_dropping_its_failed_row():
    step,r=group_trust_step(np.array([-2.,-.5]),np.eye(2,6),np.array([.2,0,0,0,0,0]),[0,.5])
    assert step is not None and np.array_equal(step[:3],np.zeros(3)) and r['model_rows']==2
    assert r['predicted_maximum_model_violation']==2


def test_required_uneditable_row_remains_infeasible():
    step,r=group_trust_step(np.array([-.1]),np.ones((1,3)),np.zeros(3),[0],protected_rows=np.array([True]))
    assert step is None and r['solver_status']=='PrimalInfeasible'


def test_existing_physical_affine_cones_are_transformed_not_replaced():
    t=np.zeros((1,3,6));t[0,0,0]=t[0,0,3]=1
    step,r=group_trust_step(np.array([-2.]),np.ones((1,6)),np.zeros(6),[.3,.8],affine_vectors=np.zeros((1,3)),affine_jacobian=t,affine_radii=np.array([.15]))
    assert step is not None and np.linalg.norm(np.einsum('bcj,j->bc',t,step),axis=1)[0]<=.15
    assert r['affine_norm_constraints']==3 and r['physical_affine_norm_constraints']==1


def test_inputs_are_owned_and_never_mutated():
    m=np.array([-1.]);j=np.ones((1,3));x=np.array([.1,0,0]);r=np.array([.2]);saved=[v.copy() for v in [m,j,x,r]]
    step,report=group_trust_step(m,j,x,r)
    assert step is not None and all(np.array_equal(a,b) for a,b in zip([m,j,x,r],saved))
    report['group_search_radii'][0]=1
    assert r[0]==.2


@pytest.mark.parametrize('fault',['shape','negative','too_large','nan','bool','complex','outside','jacobian','budget','partial_affine','affine_dtype','affine_radius'])
def test_invalid_or_incomplete_model_rejects(fault):
    m=np.array([-1.]);j=np.ones((1,3));x=np.zeros(3);r=np.array([.2]);options={}
    if fault=='shape':r=np.ones(2)
    elif fault=='negative':r[0]=-.1
    elif fault=='too_large':r[0]=2.1
    elif fault=='nan':r[0]=np.nan
    elif fault=='bool':r=np.array([True])
    elif fault=='complex':r=r.astype(complex)
    elif fault=='outside':x[0]=1.1
    elif fault=='jacobian':j=np.ones((1,6))
    elif fault=='budget':options['maximum_bytes']=1
    elif fault=='partial_affine':options['affine_vectors']=np.zeros((1,3))
    else:
        options.update(affine_vectors=np.zeros((1,3)),affine_jacobian=np.zeros((1,3,3)),affine_radii=np.ones(1))
        if fault=='affine_dtype':options['affine_vectors']=np.zeros((1,3),dtype=bool)
        else:options['affine_radii'][0]=0
    with pytest.raises(ValueError):group_trust_step(m,j,x,r,**options)
