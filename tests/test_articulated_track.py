from pathlib import Path
import sys
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from articulated_track import ArticulatedTrack


def setup(**overrides):
    local=torch.eye(3,dtype=torch.float64).repeat(5,3,1,1);root=torch.zeros((5,3),dtype=local.dtype)
    basis=torch.tensor([[0.],[.5],[1.],[.5],[0.]],dtype=local.dtype);fixed=torch.tensor([True,False,False,False,True])
    args=dict(local_rotations=local,root_positions=root,basis=basis,joints=[1],rotation_limits_radians=torch.tensor([.1],dtype=local.dtype),fixed_frames=fixed,maximum_root_translation_m=.02)
    args.update(overrides);return ArticulatedTrack(**args),args


def test_zero_identity_and_all_fixed_and_unselected_channels_exact():
    track,args=setup();zero=torch.zeros(track.size,dtype=torch.float64);local,root=track(zero)
    assert torch.equal(local,args['local_rotations']) and torch.equal(root,args['root_positions'])
    control=zero.clone();control[2]=.5;control[3]=.5;local,root=track(control)
    assert torch.equal(local[:,[0,2]],args['local_rotations'][:,[0,2]]) and torch.equal(local[[0,4]],args['local_rotations'][[0,4]])
    assert torch.equal(root[[0,4]],args['root_positions'][[0,4]]) and root[2,0]==.01


def test_full_local_root_control_jacobian_at_zero_and_nonzero():
    track,_=setup()
    function=lambda x:torch.cat([track(x)[0].flatten(),track(x)[1].flatten()])
    for v in [0.,.1]:assert torch.autograd.gradcheck(function,(torch.full((track.size,),v,dtype=torch.float64,requires_grad=True),),atol=1e-6,rtol=1e-5)


def test_true_angle_budget_and_so3_not_elementwise_rotation_edits():
    track,_=setup();control=torch.zeros(track.size,dtype=torch.float64);control[:3]=1/np.sqrt(3)
    local,_=track(control);r=local[2,1];angle=torch.acos(((torch.trace(r)-1)/2).clamp(-1,1))
    assert float(angle)==pytest.approx(.1,abs=1e-12)
    torch.testing.assert_close(r.T@r,torch.eye(3,dtype=r.dtype),atol=1e-14,rtol=0)


def test_out_of_vector_budget_rejects_without_clipping():
    track,_=setup();control=torch.zeros(track.size,dtype=torch.float64);control[:3]=.8
    assert not track.assess(control)['all_declared_bounds_pass']
    with pytest.raises(ValueError,match='budget'):track(control)


def test_complete_frame_assessment_and_convex_knot_implication():
    basis=torch.tensor([[0.,0.],[.5,0.],[.5,.5],[0.,.5],[0.,0.]],dtype=torch.float64)
    track,_=setup(basis=basis);control=torch.tensor([1.,0.,0.,0.,1.,0.]*2,dtype=torch.float64)
    result=track.assess(control);assert result['all_knot_balls_pass'] and result['all_declared_bounds_pass'] and result['complete_frame_group_vectors']==10


def test_owned_source_and_permissions_not_rebound_by_caller_mutation():
    track,args=setup();args['local_rotations'][:]=0;args['root_positions'][:]=99;args['basis'][:]=99;args['rotation_limits_radians'][:]=99;args['fixed_frames'][:]=False
    local,root=track(torch.zeros(track.size,dtype=torch.float64))
    assert torch.equal(local,torch.eye(3,dtype=torch.float64).repeat(5,3,1,1)) and not torch.any(root)


def test_disabled_root_has_no_hidden_root_control():
    track,_=setup(maximum_root_translation_m=0);assert track.size==3
    local,root=track(torch.tensor([.2,0.,0.],dtype=torch.float64));assert not torch.any(root) and not torch.equal(local[2,1],torch.eye(3,dtype=root.dtype))


@pytest.mark.parametrize('fault',['support','overshoot','unused','duplicates','joint','so3','dtype','root'])
def test_invalid_complete_source_or_control_policy_rejects(fault):
    _,args=setup()
    if fault=='support':args['basis'][0]=.1
    elif fault=='overshoot':args['basis'][2]=1.1
    elif fault=='unused':args['basis'][:]=0
    elif fault=='duplicates':args['joints']=[1,1]
    elif fault=='joint':args['joints']=[3]
    elif fault=='so3':args['local_rotations'][2,1]=0
    elif fault=='dtype':args['root_positions']=args['root_positions'].float()
    else:args['maximum_root_translation_m']=float('nan')
    with pytest.raises(ValueError):ArticulatedTrack(**args)


def test_nonfinite_or_partial_controls_reject():
    track,_=setup()
    for value in [torch.zeros(track.size-1,dtype=torch.float64),torch.full((track.size,),float('nan'),dtype=torch.float64)]:
        with pytest.raises(ValueError):track(value)


def test_root_support_can_span_full_clock_while_local_rotations_stay_protected():
    basis=torch.ones((5,1),dtype=torch.float64);fixed=torch.zeros(5,dtype=torch.bool)
    track,args=setup(root_basis=basis,root_fixed_frames=fixed);control=torch.zeros(track.size,dtype=torch.float64);control[4]=.5
    local,root=track(control)
    assert torch.equal(local,args['local_rotations']) and torch.all(root[:,1]==.01)
    assert track.assess(control)['protected_frames']==2 and track.assess(control)['root_protected_frames']==0


def test_root_support_does_not_implicitly_override_frozen_frames():
    with pytest.raises(ValueError,match='protected'):setup(root_basis=torch.ones((5,1),dtype=torch.float64))


def test_unused_root_permission_rejects_instead_of_silently_discarding_it():
    with pytest.raises(ValueError,match='Disabled'):setup(maximum_root_translation_m=0,root_basis=torch.ones((5,1),dtype=torch.float64))
