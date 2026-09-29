import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_point_rate_objective import ExportPointRateObjective
from export_motion_sampling import joint_trajectory
from support_contact_v5 import rodrigues


def fixture():
    r=torch.eye(3,dtype=torch.float64).repeat(5,2,1,1)
    p=torch.zeros(5,2,3,dtype=torch.float64)
    p[:,0,0]=torch.tensor([0.,.01,.03,.04,.06]);p[:,1,0]=torch.tensor([0.,1.,3.,4.,6.])
    skin=dict(rig_joint_names=['LeftFoot','RightFoot'],lbs_indices=np.array([[0]*8,[1]*8]),
        lbs_weights=np.tile(np.arange(1,9)/36,(2,1)),bind_vertices=np.array([[0.,0.,.2],[0.,0.,-.2]]),
        bind_rig_transform=np.tile(np.eye(4),(2,1,1)))
    spec=dict(schema_version=1,fps=30,frame_count=5,regions={name:dict(mode='explicit',segments=[
        dict(start_frame=1,end_frame=3,space='world',position_m=[0.,0.,0.],vertex_id=i)])
        for i,name in enumerate(['LeftFoot','RightFoot'])})
    return r,p,skin,spec


def objective(r,p,skin,spec):
    with patch('export_point_rate_objective.regions',return_value={'LeftFoot':np.array([0]),'RightFoot':np.array([1])}):
        return ExportPointRateObjective(r,p,[-1,-1],skin,spec)


def test_per_point_limits_catch_slow_foot_regression_hidden_by_fast_foot():
    r,p,skin,spec=fixture();o=objective(r,p,skin,spec)
    assert o.loss(r,p)==0
    candidate=p.clone();candidate[:,0]*=1.5
    assert candidate[:,0,0].max()<p[:,1,0].max()
    assert o.loss(r,candidate)>0
    record=o.record()
    assert len(record['rows'])==6
    assert all(max(row['maximum_normalized_violations'])>0 for row in record['rows'] if row['region']=='LeftFoot')
    assert all(max(row['maximum_normalized_violations'])==0 for row in record['rows'] if row['region']=='RightFoot')
    o.advance_stage(4)
    assert o.record()['penalty']==40


def test_loss_has_finite_correct_translation_gradient():
    r,p,skin,spec=fixture();o=objective(r,p,skin,spec)
    candidate=(p*1.2).requires_grad_()
    assert torch.autograd.gradcheck(lambda x:o.loss(r,x),(candidate,),atol=1e-3,rtol=1e-3)


def test_rotation_return_matches_positions_and_skin_responds_to_rotation():
    r,p,skin,spec=fixture();o=objective(r,p,skin,spec)
    angle=torch.zeros(5,2,3,dtype=torch.float64);angle[:,0,1]=torch.arange(5)*.1;angle.requires_grad_()
    rotations=rodrigues(angle)
    sampled_r,sampled_p=joint_trajectory(rotations,p,[-1,-1],return_rotations=True)
    torch.testing.assert_close(sampled_p,joint_trajectory(rotations,p,[-1,-1]),rtol=0,atol=0)
    assert sampled_r.shape==(17,2,3,3)
    gradient=torch.autograd.grad(sum(x.square().sum() for x in o.rates(rotations,p)),angle)[0]
    assert torch.isfinite(gradient).all() and gradient.abs().max()>0


def test_static_point_has_finite_zero_loss_and_rejects_movement():
    r,p,skin,spec=fixture();p.zero_();o=objective(r,p,skin,spec);p.requires_grad_()
    loss=o.loss(r,p)
    assert loss==0 and torch.isfinite(torch.autograd.grad(loss,p)[0]).all()
    q=p.detach().clone();q[2,0,0]=.001
    assert o.loss(r,q)>0


def test_ambiguous_or_moving_material_point_rejected():
    r,p,skin,spec=fixture()
    spec['regions']['LeftFoot']['segments'][0].pop('vertex_id')
    with pytest.raises(ValueError,match='fixed material'):objective(r,p,skin,spec)
