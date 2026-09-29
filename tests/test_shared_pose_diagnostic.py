import copy
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from shared_pose_diagnostic import require_repeated_motion, require_static_scene, shared_basis
from box_root_optimizer import BoxRootOptimizer


def motion():
    return dict(root_positions=np.zeros((5, 3)), posed_joints=np.zeros((5, 2, 3)),
                local_rot_mats=np.tile(np.eye(3), (5, 2, 1, 1)),
                global_rot_mats=np.tile(np.eye(3), (5, 2, 1, 1)))


def scene():
    return dict(actors={'A': {}}, frame_count=5,
                objects={'box': {'shape': 'box', 'size_m': [1,1,1], 'keyframes': [dict(frame=0, translation_m=[0, 1, 0], rotation_xyzw=[0, 0, 0, 1])] }},
                contacts=[dict(id='grip', actor='A', start_frame=0, end_frame=4,
                               target=dict(space='object', object='box', point_m=[0, 0, 0]))])


@pytest.mark.parametrize('field', ['root_positions', 'posed_joints', 'local_rot_mats', 'global_rot_mats'])
def test_dynamic_motion_cannot_be_silently_collapsed(field):
    data=motion(); assert require_repeated_motion(data)==5
    data[field][2].flat[0]+=1e-8
    with pytest.raises(ValueError, match='exactly repeated'): require_repeated_motion(data)


def test_nonfinite_and_mismatched_motion_rejected():
    data=motion();data['posed_joints'][0, 0, 0]=np.nan
    with pytest.raises(ValueError):require_repeated_motion(data)
    with pytest.raises(ValueError):require_repeated_motion(motion(), 4)


@pytest.mark.parametrize('change', ['object', 'window', 'partner', 'cuts', 'target'])
def test_nonstatic_scene_rejected(change):
    data=scene(); require_static_scene(data,'A',['grip'])
    if change=='object':
        last=copy.deepcopy(data['objects']['box']['keyframes'][0]);last.update(frame=4,translation_m=[0,2,0])
        data['objects']['box']['keyframes'].append(last)
    if change=='window':data['contacts'][0]['start_frame']=1
    if change=='partner':data['actors']['B']={}
    if change=='cuts':data['partner_cut_file']='cuts.json'
    if change=='target':data['contacts'][0]['target']['space']='actor'
    with pytest.raises(ValueError):require_static_scene(data,'A',['grip'])


def test_shared_controls_solve_all_samples_as_one_pose():
    basis,knots=shared_basis(5)
    assert knots.tolist()==[0]
    rotation=torch.zeros((1,1,3),dtype=torch.float64,requires_grad=True)
    lift=torch.tensor([.01],dtype=torch.float64,requires_grad=True)
    solver=BoxRootOptimizer(rotation,lift,.22,50)
    target=torch.tensor([.1,-.05,.08],dtype=torch.float64)
    def closure():
        solver.zero_grad()
        poses=torch.einsum('fk,kjd->fjd',torch.tensor(basis),rotation)
        heights=lift.expand(5)
        loss=(poses-target).square().sum()+((heights-.06)**2).sum()
        loss.backward()
        return loss
    solver.step(closure)
    np.testing.assert_allclose(rotation.detach().numpy()[0,0],target.numpy(),atol=1e-7)
    assert abs(float(lift.detach()[0])-.06)<1e-7
    assert np.array_equal(lift.detach().expand(5).numpy(), np.full(5,float(lift.detach()[0])))
